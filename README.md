# 🧊 Fridge2Fork · 冰箱侦探

> 拍一张冰箱照片，AI 识别食材并推荐"现在就能做的菜"

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-teal.svg)

## 📸 演示

1. 打开网页 → 拍一张冰箱内部照片
2. AI 自动识别食材（西兰花、西红柿、鸡蛋...）
3. 推荐"你能做的菜"，标注已有食材 ✓ 和缺料食材 ✗
4. 自动生成购物清单，一键复制

> 💡 **在线体验**：https://your-app.onrender.com （部署后替换）

---

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 📸 **AI 食材识别** | 调用 Kimi K2.7 多模态模型，识别冰箱照片中的食材 |
| 🎤 **语音补充** | 识别完成后，可用语音补充"冷冻层还有牛排" |
| 🍳 **智能推荐** | 基于库存 + 用户画像，推荐 3-5 道匹配度最高的菜 |
| 🔍 **反向查询** | 输入"想做红烧肉"，AI 检查现有食材并告知缺料 |
| 🛒 **购物清单** | 自动汇总缺料食材，支持一键复制 |
| 👤 **用户画像** | 记住口味偏好、饮食目标、常备食材 |
| 📊 **消耗跟踪** | 确认"做了这道菜"后，自动扣减库存 |

---

## 🏗️ 架构图

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   用户手机   │ ───▶ │  FastAPI 后端 │ ───▶ │  Kimi API   │
│  (拍照上传)  │ ◀─── │  (Python)    │ ◀─── │ (多模态AI)  │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  JSON 菜谱库  │
                     │  (25道家常菜) │
                     └──────────────┘
```

**技术栈**
- **前端**：HTML5 + Tailwind CSS + Vanilla JS
- **后端**：Python + FastAPI
- **AI 模型**：Kimi K2.7 Code（多模态图像识别）
- **部署**：Render（免费）
- **数据**：JSON 文件（轻量，适合 MVP）

---

## 🚀 快速部署（Render）

### 1. Fork 本仓库到 GitHub

### 2. 注册 Render
访问 https://render.com，用 GitHub 账号登录。

### 3. 创建 Web Service
1. Dashboard → **New +** → **Web Service**
2. 选择你的 `fridge2fork` 仓库
3. Render 会自动识别 `render.yaml` 配置

### 4. 设置环境变量
在 Render Dashboard → Environment 中添加：
```
KIMI_API_KEY=sk-your-kimi-api-key-here
DAILY_LIMIT=10
```

### 5. 点击 Deploy
等待 2-3 分钟，获得线上地址：`https://fridge2fork-xxxxx.onrender.com`

> ⚠️ **注意**：Render Free 服务 15 分钟无访问会休眠，首次访问可能需要 30 秒唤醒。

---

## 💻 本地开发

### 后端启动
```bash
cd backend
pip install -r requirements.txt
# 创建 .env 文件，填入 KIMI_API_KEY
cp .env.example .env
# 编辑 .env，填入你的 Key
uvicorn main:app --reload
```

### 前端访问
```bash
# 方式一：直接打开（仅限本地调试，可能有跨域限制）
# 双击 frontend/index.html

# 方式二：启动本地 HTTP 服务器（推荐）
cd frontend
python -m http.server 5500
# 浏览器访问 http://localhost:5500
```

### API 文档
本地启动后访问：http://localhost:8000/docs

---

## 📁 项目结构

```
fridge2fork/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── routers/
│   │   ├── ingredients.py   # 食材识别/库存管理
│   │   └── recipes.py       # 菜谱推荐/画像/购物清单
│   ├── services/
│   │   └── kimi_service.py  # Kimi API 调用
│   └── requirements.txt
├── frontend/
│   ├── index.html           # 主页面
│   ├── css/style.css
│   └── js/app.js
├── data/
│   └── recipes.json         # 25道家常菜数据库
├── docs/                    # 开发文档
│   ├── 01-产品需求文档.md
│   ├── 02-技术架构.md
│   ├── 03-API接口规范.md
│   ├── 04-代码规范.md
│   ├── 05-部署手册.md
│   └── 06-开发执行步骤.md
├── CLAUDE.md                # 项目协作指引
├── render.yaml              # Render 部署配置
└── README.md
```

---

## 🎯 面试亮点

1. **多模态 AI 应用**：真实调用视觉大模型解决日常痛点，不是玩具项目
2. **完整产品闭环**：识别 → 推荐 → 清单 → 消耗跟踪，用户体验完整
3. **双入口设计**：被动推荐（拍冰箱）+ 主动搜索（想做某菜），体现产品思维
4. **成本意识**：限流 + BYOK 混合架构，展示对 API 成本的工程思考
5. **全栈能力**：从前端 UI 到后端 API 到 AI Prompt 工程，独立完成

---

## 🛡️ 成本与安全

- **后端代理模式**：API Key 仅存于服务器环境变量，前端不接触
- **每日限流**：默认 10 次/天，防止意外超支
- **开源友好**：Fork 后填写自己的 Key 即可部署，零成本使用

---

## 📄 开源协议

MIT License © 2026 Fridge2Fork

---

## 🙏 致谢

- [Moonshot AI](https://moonshot.cn) 提供 Kimi 多模态 API
- [FastAPI](https://fastapi.tiangolo.com) 提供高效后端框架
- [Tailwind CSS](https://tailwindcss.com) 提供原子化 CSS 方案
