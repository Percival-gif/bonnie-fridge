import json
import os
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional
from pydantic import BaseModel
from services.kimi_service import generate_recommendation_reason

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

# 加载菜谱数据
RECIPES_PATH = os.path.join(os.path.dirname(__file__), "../../data/recipes.json")
with open(RECIPES_PATH, "r", encoding="utf-8") as f:
    RECIPES_DATA = json.load(f)["recipes"]

# 用户画像（内存存储）
_user_profile: Dict[str, any] = {
    "taste": "不限制",       # 清淡 / 微辣 / 重辣 / 酸甜
    "goal": "无特殊",        # 减脂 / 增肌 / 控糖 / 素食
    "max_time": "不限制",    # 15分钟 / 30分钟 / 不限制
    "staples": ["盐", "糖", "油", "生抽", "酱油", "醋", "大米"]  # 常备食材
}

class RecommendRequest(BaseModel):
    ingredients: List[str]

class CheckDishRequest(BaseModel):
    dish_name: str
    ingredients: List[str]

class ShoppingListRequest(BaseModel):
    recipe_ids: List[str]
    ingredients: List[str]

# 用户画像设置
@router.get("/profile")
async def get_profile():
    return JSONResponse({
        "success": True,
        "data": _user_profile
    })

@router.post("/profile")
async def update_profile(profile: Dict):
    """
    更新用户画像
    {
        "taste": "清淡",
        "goal": "减脂",
        "max_time": "30分钟",
        "staples": ["盐", "油", "大米"]
    }
    """
    allowed_tastes = ["清淡", "微辣", "重辣", "酸甜", "不限制"]
    allowed_goals = ["减脂", "增肌", "控糖", "素食", "无特殊"]
    allowed_times = ["15分钟", "30分钟", "不限制"]

    if profile.get("taste") in allowed_tastes:
        _user_profile["taste"] = profile["taste"]
    if profile.get("goal") in allowed_goals:
        _user_profile["goal"] = profile["goal"]
    if profile.get("max_time") in allowed_times:
        _user_profile["max_time"] = profile["max_time"]
    if "staples" in profile and isinstance(profile["staples"], list):
        _user_profile["staples"] = profile["staples"]

    return JSONResponse({
        "success": True,
        "data": _user_profile
    })

# 菜谱推荐
@router.post("/recommend")
async def recommend(request: RecommendRequest):
    """
    基于食材推荐菜谱
    ingredients: ["鸡蛋", "西红柿", "黄瓜"]
    """
    if not request.ingredients:
        return JSONResponse({
            "success": False,
            "error": "请先识别或添加食材"
        })

    # 合并用户常备食材
    all_available = set(request.ingredients + _user_profile.get("staples", []))

    results = []
    for recipe in RECIPES_DATA:
        # 检查是否匹配饮食目标
        tags = recipe.get("tags", [])
        goal = _user_profile.get("goal", "无特殊")
        if goal == "素食" and "素菜" not in tags and "素食" not in tags:
            continue
        if goal == "减脂" and ("油炸" in tags or "红烧" in tags):
            continue

        # 计算匹配度
        required = [ing["name"] for ing in recipe.get("ingredients", [])]
        matched = [r for r in required if any(r in avail or avail in r for avail in all_available)]
        match_score = len(matched) / len(required) if required else 0

        # 只推荐匹配度 > 50% 的
        if match_score < 0.5:
            continue

        # 标记已有/缺料
        ingredient_status = []
        for req in recipe.get("ingredients", []):
            req_name = req["name"]
            has_it = any(req_name in avail or avail in req_name for avail in all_available)
            ingredient_status.append({
                "name": req_name,
                "amount": req["amount"],
                "has": has_it
            })

        # 生成推荐理由（简化版，不每次都调用 AI，降低 Token 消耗）
        reason = f"匹配度 {int(match_score * 100)}%，你有 {len(matched)}/{len(required)} 种食材"

        results.append({
            "id": recipe["id"],
            "name": recipe["name"],
            "tags": tags,
            "time": recipe.get("time", "未知"),
            "difficulty": recipe.get("difficulty", "未知"),
            "match_score": round(match_score, 2),
            "ingredients": ingredient_status,
            "steps": recipe.get("steps", []),
            "reason": reason
        })

    # 按匹配度排序
    results.sort(key=lambda x: x["match_score"], reverse=True)

    return JSONResponse({
        "success": True,
        "data": results[:5]  # 最多返回 5 道
    })

# 反向查询
@router.post("/check")
async def check_dish(request: CheckDishRequest):
    """
    想做某道菜，检查缺什么
    {
        "dish_name": "红烧肉",
        "ingredients": ["鸡蛋", "西红柿"]
    }
    """
    dish_name = request.dish_name.strip()
    user_ingredients = request.ingredients

    if not dish_name:
        return JSONResponse({
            "success": False,
            "error": "请输入菜名"
        })

    all_available = set(user_ingredients + _user_profile.get("staples", []))

    # 在菜谱库中查找
    recipe = next((r for r in RECIPES_DATA if dish_name in r["name"] or r["name"] in dish_name), None)

    if not recipe:
        return JSONResponse({
            "success": True,
            "data": {
                "found": False,
                "message": f"菜谱库中暂未找到'{dish_name}'，你可以尝试搜索其他家常菜"
            }
        })

    required = [ing["name"] for ing in recipe.get("ingredients", [])]
    matched = [r for r in required if any(r in avail or avail in r for avail in all_available)]
    missing = [r for r in required if r not in matched]

    return JSONResponse({
        "success": True,
        "data": {
            "found": True,
            "dish": recipe["name"],
            "have": matched,
            "missing": missing,
            "match_score": round(len(matched) / len(required), 2) if required else 0,
            "steps": recipe.get("steps", [])
        }
    })

# 购物清单
@router.post("/shopping-list")
async def generate_shopping_list(request: ShoppingListRequest):
    """
    生成购物清单
    {
        "recipe_ids": ["tomato-egg", "egg-fried-rice"],
        "ingredients": ["鸡蛋", "西红柿"]
    }
    """
    recipe_ids = request.recipe_ids
    user_ingredients = request.ingredients
    all_available = set(user_ingredients + _user_profile.get("staples", []))

    shopping_map = {}

    for rid in recipe_ids:
        recipe = next((r for r in RECIPES_DATA if r["id"] == rid), None)
        if not recipe:
            continue
        for ing in recipe.get("ingredients", []):
            name = ing["name"]
            amount = ing["amount"]
            # 检查是否已有
            has_it = any(name in avail or avail in name for avail in all_available)
            if not has_it:
                if name not in shopping_map:
                    shopping_map[name] = {"amounts": [amount], "for": [recipe["name"]]}
                else:
                    shopping_map[name]["amounts"].append(amount)
                    if recipe["name"] not in shopping_map[name]["for"]:
                        shopping_map[name]["for"].append(recipe["name"])

    # 格式化输出
    shopping_list = []
    for name, info in shopping_map.items():
        amounts = list(set(info["amounts"]))
        shopping_list.append({
            "name": name,
            "amount": "、".join(amounts) if len(amounts) <= 2 else f"{amounts[0]} 等",
            "for_dishes": info["for"]
        })

    return JSONResponse({
        "success": True,
        "data": shopping_list,
        "count": len(shopping_list)
    })
