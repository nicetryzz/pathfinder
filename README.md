# Pathfinder - 您的AI知识学习导航员
Pathfinder 是一个创新的AI知识图谱学习与导航系统，旨在解决AI初学者及进阶者在面对复杂领域时“不知从何学起”的核心痛点。用户只需输入一个主题，Pathfinder即可通过强大的多代理（Multi-Agent）系统，自动生成一张结构清晰、包含权威学习资源的交互式知识地图。

![](screenshot\demo.png)

## 📖 项目文档
为了更深入地了解Pathfinder的设计理念与技术实现，请查阅我们的核心文档：

* 产品需求文档 ([PRD.md](PRD.md)): 详细阐述了产品的愿景、目标用户、功能需求和交互设计。

* 技术设计文档 ([TDD.md(TDD.md)]): 深入解析了系统的技术架构、多代理协作流程和API设计。

## ✨ 核心特性
* 🧠 智能图谱生成: 基于强大的多代理系统（Architect, Inspector, etc.），自动将复杂主题解构为分层的知识树。

* 🌐 动态关联网络: 不仅是树状结构，更能智能挖掘并建议知识间的横向关联，揭示深层联系。

* 📊 交互式可视化: 基于Vue3 + ECharts，提供流畅、清晰、可交互的知识图谱可视化体验。

* 🚀 前后端分离: 采用FastAPI + Vue3架构，API响应迅速，易于维护和独立部署。

* ⚙️ 离线批量处理: 内置强大的离线脚本，支持批量生成和预缓存知识图谱，便于大规模应用。

* 🔐 灵活的密钥管理: 支持多代理/密钥池轮询，有效管理API配额与成本。

## 🛠️ 技术栈
* 前端: Vue 3, Vite, ECharts, Element Plus

* 后端: Python 3.10+, FastAPI, Uvicorn

* AI/LLM: LangChain, Google Gemini Pro

## 🚀 快速启动

### 环境配置
本项目需要通过环境变量配置您的LLM API密钥。

a. 复制环境变量模板文件：
```
cp myagent_backend/.env.example myagent_backend/.env
```
b. 编辑新创建的.env文件，填入您的API密钥和代理信息：
```
# myagent_backend/.env
GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"
# 如果您使用代理，请取消注释并设置
# GOOGLE_API_BASE="YOUR_PROXY_URL_HERE"
```
### 安装依赖
```
# 后端 (推荐使用 Conda)
cd myagent_backend
conda env create -f environment.yml
conda activate pathfinder

# 前端
cd frontend
npm install
```
### 启动服务
```
# 启动后端API服务器
cd myagent_backend
uvicorn myagent_backend.api_server.main:app --reload

# 启动前端开发服务器
cd frontend
npm run dev
```
现在，您可以在浏览器中打开 http://localhost:5173 来访问Pathfinder。

## ⚙️ 离线Agent批量生成
对于需要预先生成大量知识图谱的场景，我们提供了强大的离线批量生成脚本。
```
cd myagent_backend/scripts

# 示例：根据 topics.txt 文件中的主题列表，生成JSON文件到 ../../maps/ 目录
python offline_generate.py --input topics.txt --output ../../maps/
```
* --input: 包含待生成主题的文本文件，每行一个主题。

* --output: 生成的知识图谱JSON文件保存目录。
  
## ⚠️ 代理与密钥池说明
* 本项目支持多代理/密钥池轮询，以管理高并发请求和API成本。具体实现可参考第三方库 [gpt-load](https://github.com/tbphp/gpt-load)。

* **注意**: 当前版本与Google GenAI SDK的集成，可能需要依赖一个特定的langchain-google功能分支。这是一个临时性措施，我们正密切关注上游库的更新，以便尽快切换回稳定主分支。如果您遇到相关问题，请参考：https://github.com/Instawork/langchain-google/tree/feature/upgrade-to-google-genai-sdk

## 🗺️ 未来路线图 (Roadmap)
我们对Pathfinder有很多激动人心的计划！

[ ] 交互式布局: 支持用户拖拽节点，并提供多种布局算法（分层、径向）切换。

[ ] 多语言支持: 支持生成非英文主题的知识图谱。

[ ] 知识节点编辑: 允许用户在前端对图谱结构和内容进行微调。

## 🤝 贡献与交流
我们欢迎任何形式的贡献！如果您有好的建议、发现了Bug，或是想实现新的功能，请随时提交 Issue 或 Pull Request。

Pathfinder - Your AI Learning Navigator