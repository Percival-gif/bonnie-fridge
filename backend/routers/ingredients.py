from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict
from services.kimi_service import recognize_ingredients
import traceback

router = APIRouter(prefix="/api/ingredients", tags=["ingredients"])

# 内存存储用户库存（生产环境建议用数据库）
_user_inventory: Dict[str, List[Dict]] = {}

@router.post("/recognize")
async def recognize(file: UploadFile = File(...)):
    """
    上传冰箱照片，AI 识别食材
    """
    try:
        image_bytes = await file.read()
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="图片过大，请上传小于 10MB 的图片")

        ingredients = await recognize_ingredients(image_bytes)

        # 存入内存（用 session_id 区分用户，简单起见用 "default"）
        _user_inventory["default"] = ingredients

        return JSONResponse({
            "success": True,
            "data": ingredients,
            "count": len(ingredients)
        })
    except RuntimeError as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=429)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({
            "success": False,
            "error": f"识别失败: {str(e)}"
        }, status_code=500)

@router.get("/inventory")
async def get_inventory():
    """
    获取当前库存
    """
    inventory = _user_inventory.get("default", [])
    return JSONResponse({
        "success": True,
        "data": inventory
    })

@router.post("/inventory/update")
async def update_inventory(updates: List[Dict]):
    """
    手动更新库存（纠偏、补充、删除）
    请求体示例：
    [
        {"action": "add", "name": "牛肉", "quantity": "200克"},
        {"action": "remove", "name": "鸡蛋"},
        {"action": "update", "name": "西红柿", "quantity": "5个"}
    ]
    """
    inventory = _user_inventory.get("default", [])

    for update in updates:
        action = update.get("action")
        name = update.get("name", "").strip()
        quantity = update.get("quantity", "")

        if not name:
            continue

        if action == "add":
            # 检查是否已存在
            existing = next((item for item in inventory if item["name"] == name), None)
            if existing:
                existing["quantity"] = quantity
            else:
                inventory.append({
                    "name": name,
                    "quantity": quantity or "若干",
                    "confidence": "user"
                })
        elif action == "remove":
            inventory = [item for item in inventory if item["name"] != name]
        elif action == "update":
            existing = next((item for item in inventory if item["name"] == name), None)
            if existing:
                existing["quantity"] = quantity

    _user_inventory["default"] = inventory

    return JSONResponse({
        "success": True,
        "data": inventory
    })

@router.post("/supplement")
async def supplement_ingredients(supplements: List[Dict]):
    """
    语音/文字补充食材
    请求体示例：
    [
        {"name": "冷冻牛排", "quantity": "2块"},
        {"name": "昨天买的豆腐", "quantity": "1盒"}
    ]
    """
    inventory = _user_inventory.get("default", [])

    for sup in supplements:
        name = sup.get("name", "").strip()
        quantity = sup.get("quantity", "若干")
        if name:
            existing = next((item for item in inventory if item["name"] == name), None)
            if existing:
                existing["quantity"] = quantity
            else:
                inventory.append({
                    "name": name,
                    "quantity": quantity,
                    "confidence": "user"
                })

    _user_inventory["default"] = inventory

    return JSONResponse({
        "success": True,
        "data": inventory
    })

@router.post("/consume")
async def consume_ingredients(used: List[Dict]):
    """
    做菜后扣减库存
    请求体示例：
    [
        {"name": "鸡蛋", "quantity": "2个"}
    ]
    """
    inventory = _user_inventory.get("default", [])

    for u in used:
        name = u.get("name", "").strip()
        # 简化处理：直接标记为"已用完"或从列表移除
        # MVP 版本直接移除
        inventory = [item for item in inventory if item["name"] != name]

    _user_inventory["default"] = inventory

    return JSONResponse({
        "success": True,
        "data": inventory
    })
