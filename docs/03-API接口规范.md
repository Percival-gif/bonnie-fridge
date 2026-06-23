# 03-API 接口规范

> 基础地址：`http://localhost:8000`（本地）或 `https://your-app.onrender.com`（线上）
> 所有 JSON 响应格式：`{ "success": true/false, "data": ..., "error": "..." }`

## 1. 食材识别

### POST `/api/ingredients/recognize`
上传冰箱照片，AI 识别食材。

**请求**：`multipart/form-data`
- `file`: 图片文件（JPG/PNG，< 10MB）

**响应示例**：
```json
{
  "success": true,
  "data": [
    {"name": "鸡蛋", "quantity": "5个", "confidence": "high"},
    {"name": "西红柿", "quantity": "3个", "confidence": "high"},
    {"name": "牛奶", "quantity": "1盒", "confidence": "medium"}
  ],
  "count": 3
}
```

**错误码**：
- `429`: 今日免费额度已用完
- `500`: AI 识别失败或返回格式错误

---

## 2. 库存管理

### GET `/api/ingredients/inventory`
获取当前库存列表。

### POST `/api/ingredients/inventory/update`
手动更新库存（纠偏）。

**请求体**：
```json
[
  {"action": "add", "name": "牛肉", "quantity": "200克"},
  {"action": "remove", "name": "鸡蛋"},
  {"action": "update", "name": "西红柿", "quantity": "5个"}
]
```

### POST `/api/ingredients/supplement`
语音/文字补充食材。

**请求体**：
```json
[
  {"name": "冷冻牛排", "quantity": "2块"}
]
```

### POST `/api/ingredients/consume`
做菜后扣减库存。

**请求体**：
```json
[
  {"name": "鸡蛋", "quantity": "2个"}
]
```

---

## 3. 用户画像

### GET `/api/recipes/profile`
获取当前画像。

### POST `/api/recipes/profile`
更新画像。

**请求体**：
```json
{
  "taste": "清淡",
  "goal": "减脂",
  "max_time": "30分钟",
  "staples": ["盐", "油", "大米"]
}
```

---

## 4. 菜谱推荐

### POST `/api/recipes/recommend`
基于食材推荐菜谱。

**请求体**：食材名称数组
```json
["鸡蛋", "西红柿", "黄瓜"]
```

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "id": "tomato-egg",
      "name": "西红柿炒鸡蛋",
      "match_score": 0.85,
      "ingredients": [
        {"name": "鸡蛋", "amount": "3个", "has": true},
        {"name": "西红柿", "amount": "2个", "has": true},
        {"name": "葱花", "amount": "少许", "has": false}
      ],
      "steps": ["..."],
      "reason": "匹配度 85%，你有 4/5 种食材"
    }
  ]
}
```

---

## 5. 反向查询

### POST `/api/recipes/check`
想做某道菜，查缺料。

**请求体**：
```json
{
  "dish_name": "红烧肉",
  "ingredients": ["鸡蛋", "西红柿"]
}
```

**响应示例**：
```json
{
  "success": true,
  "data": {
    "found": true,
    "dish": "红烧肉",
    "have": ["生抽", "糖"],
    "missing": ["五花肉", "八角", "冰糖"],
    "match_score": 0.4,
    "steps": ["..."]
  }
}
```

---

## 6. 购物清单

### POST `/api/recipes/shopping-list`
生成缺料购物清单。

**请求体**：
```json
{
  "recipe_ids": ["tomato-egg", "egg-fried-rice"],
  "ingredients": ["鸡蛋", "西红柿"]
}
```

**响应示例**：
```json
{
  "success": true,
  "data": [
    {"name": "葱花", "amount": "少许", "for_dishes": ["西红柿炒鸡蛋"]}
  ],
  "count": 1
}
```
