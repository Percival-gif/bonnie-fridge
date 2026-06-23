import os
import base64
import json
import httpx
from typing import List, Dict
from dotenv import load_dotenv
from io import BytesIO

# 从 backend 目录加载 .env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
KIMI_BASE_URL = "https://api.moonshot.cn/v1"
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "10"))

# 简单的内存限流器（生产环境建议用 Redis）
_call_count = {"date": "", "count": 0}

def _check_limit() -> bool:
    """检查当日调用次数是否超限"""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    global _call_count
    if _call_count["date"] != today:
        _call_count = {"date": today, "count": 0}
    if _call_count["count"] >= DAILY_LIMIT:
        return False
    _call_count["count"] += 1
    return True

def _encode_image(image_bytes: bytes) -> str:
    """将图片转为 base64"""
    return base64.b64encode(image_bytes).decode("utf-8")

def _preprocess_image(image_bytes: bytes, max_size: int = 512, quality: int = 70) -> bytes:
    """
    用 Pillow 预处理图片：
    1. 支持 HEIC/PNG/JPG 等各种格式（HEIC 需 pillow-heif）
    2. 等比例缩放到最大边不超过 max_size
    3. 统一转换为 RGB JPEG
    4. 控制文件大小
    """
    import traceback
    try:
        from PIL import Image
    except ImportError:
        print("[WARN] Pillow 未安装，跳过图片预处理")
        return image_bytes

    try:
        img = Image.open(BytesIO(image_bytes))
        original_size = len(image_bytes)
        print(f"[INFO] 原始图片: {img.size}, 模式={img.mode}, 大小={original_size/1024:.1f}KB")

        # 转换为 RGB（去除透明通道等）
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # 等比例缩放
        width, height = img.size
        if max(width, height) > max_size:
            ratio = max_size / max(width, height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # 保存为 JPEG
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        result = buffer.getvalue()
        print(f"[INFO] 预处理后: {img.size}, 大小={len(result)/1024:.1f}KB")
        return result
    except Exception as e:
        print(f"[ERROR] 图片预处理失败: {e}")
        traceback.print_exc()
        return image_bytes

async def recognize_ingredients(image_bytes: bytes) -> List[Dict]:
    """
    调用 Kimi K2.7 多模态 API 识别冰箱中的食材
    返回结构化食材列表
    """
    if not KIMI_API_KEY:
        raise ValueError("KIMI_API_KEY 未设置，请在 .env 文件中配置")

    if not _check_limit():
        raise RuntimeError(f"今日免费调用额度已用完（{DAILY_LIMIT}次），请明天再来或部署自己的后端")

    base64_image = _encode_image(_preprocess_image(image_bytes))
    mime_type = "image/jpeg"  # 预处理后统一为 JPEG

    system_prompt = """你是一位专业的"冰箱食材识别助手"。
用户会上传一张冰箱内部的照片，请你仔细识别照片中所有可见的食材。

输出要求（严格遵循）：
1. 只输出 JSON 数组，不要任何其他文字说明
2. 每个食材包含：name（食材名称，如"鸡蛋"、"西红柿"，不识别品牌）、quantity（数量/份量，如"3个"、"1盒"）、confidence（置信度：high/medium/low）
3. 如果某食材看不清，confidence 标为 low
4. 忽略调味品瓶子的品牌，只识别种类（如"酱油"而非"海天酱油"）
5. 不要识别容器、货架、冰箱部件

示例输出格式：
[
  {"name": "鸡蛋", "quantity": "5个", "confidence": "high"},
  {"name": "西红柿", "quantity": "3个", "confidence": "high"},
  {"name": "牛奶", "quantity": "1盒", "confidence": "medium"}
]
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}},
                {"type": "text", "text": "请识别这张冰箱照片中的所有食材，只返回JSON数组。"}
            ]
        }
    ]

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{KIMI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {KIMI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "kimi-k2.7-code",
                "messages": messages,
                "max_tokens": 1000
            }
        )
        if response.status_code != 200:
            print(f"[ERROR] Kimi API 返回 {response.status_code}: {response.text}")
        response.raise_for_status()
        data = response.json()
        msg = data["choices"][0]["message"]

        # kimi-k2.7-code 是推理模型，回答可能在 reasoning_content 中
        content = msg.get("content", "") or msg.get("reasoning_content", "")

        if not content:
            raise ValueError("AI 返回内容为空")

        # 清理可能的 markdown 代码块
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        # 尝试从文本中提取 JSON 数组（推理模型可能在数组前后有解释文字）
        import re
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        ingredients = json.loads(content)
        # 确保返回的是列表
        if not isinstance(ingredients, list):
            raise ValueError("AI 返回格式错误，期望 JSON 数组")
        return ingredients

async def generate_recommendation_reason(ingredients: List[str], recipe_name: str) -> str:
    """
    生成一句话推荐理由
    """
    if not KIMI_API_KEY:
        return f"使用你现有的 {', '.join(ingredients[:3])} 等食材"

    prompt = f"用户冰箱里有：{', '.join(ingredients)}。推荐菜谱：{recipe_name}。请用一句话（30字以内）说明推荐理由，要亲切自然。"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{KIMI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {KIMI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "kimi-k2.7-code",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 100
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

async def check_missing_ingredients(user_ingredients: List[str], target_dish: str) -> Dict:
    """
    反向查询：想做某道菜，检查缺什么料
    """
    if not KIMI_API_KEY:
        return {"error": "API Key 未配置"}

    prompt = f"""用户冰箱里有：{', '.join(user_ingredients)}。
用户想做菜：{target_dish}。
请分析：
1. 用户已有的食材（可直接用）
2. 用户缺少的食材
3. 给出简单建议

输出JSON格式：
{{"have": ["鸡蛋", "西红柿"], "missing": ["葱花", "糖"], "suggestion": "建议"}}"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{KIMI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {KIMI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "kimi-k2.7-code",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500
            }
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # 清理 markdown
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        return json.loads(content)
