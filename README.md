# Pathfinder - AI知识图谱学习导航系统

## 项目简介
Pathfinder 是一个面向 AI 领域的知识图谱学习与导航系统，支持主题检索、知识结构可视化、节点详情展示与资源推荐。系统采用前后端分离架构，支持离线批量生成知识图谱与在线极速 API 响应。

- 前端：Vue3 + Element Plus + ECharts，响应式双栏布局，支持主题输入、知识图谱可视化、节点详情区独立滚动。
- 后端：FastAPI，支持 /api/v1/maps/{topic_name} 路径获取知识图谱 JSON，离线批量生成脚本 offline_generate.py。
- 离线Agent：支持批量生成高质量知识图谱 JSON，自动调用 LLM/多代理/密钥池，严格约束节点类型和相关性。
- 特色：多代理/密钥池轮询，节点类型/相关性严格约束，Markdown 详情渲染，资源推荐美观。

## 快速启动
1. 安装依赖
   ```bash
   # 后端（推荐使用 conda 环境）
   cd myagent_backend
   conda env create -f environment.yml
   conda activate pathfinder
   # 前端
   cd frontend
   npm install
   ```
2. 启动服务
   ```bash
   # 后端
   uvicorn myagent_backend.main:app --reload
   # 前端
   npm run dev
   ```
3. 访问页面
   浏览器打开 http://localhost:5173

## 离线Agent批量生成
- 离线批量生成脚本位于 `myagent_backend/scripts/offline_generate.py`
- 支持批量主题输入，自动生成知识图谱 JSON 文件，适合大规模预生成和数据集扩充。
- 支持多代理/密钥池自动轮询，LLM模型动态实例化，节点类型/相关性严格约束。

### 运行方法
```bash
cd myagent_backend/scripts
python offline_generate.py --input topics.txt --output ./output_json/
```
- `--input topics.txt`：包含待生成主题的文本文件，每行一个主题
- `--output ./output_json/`：生成的知识图谱 JSON 文件保存目录
- 可通过环境变量或 config.py 配置代理和密钥池

## 主要功能
- 主题检索与知识图谱加载
- 节点点击展示详情（Markdown渲染、资源推荐）
- 图谱结构自适应布局，节点关系清晰
- 支持离线批量生成知识图谱 JSON
- API 极速响应，前后端分离

## 目录结构
```
myproject/
├── myagent_backend/      # 后端 FastAPI 服务与批量生成脚本
│   ├── scripts/          # 离线批量生成 offline_generate.py
│   ├── knowledge_graph/  # 主要业务逻辑、agents、prompts
├── frontend/            # 前端 Vue3 可视化界面
├── README.md            # 项目说明文档
```

## 代理与密钥池说明
- 本项目知识图谱生成支持多代理/密钥池轮询，参考实现：[gpt-load](https://github.com/tbphp/gpt-load)
- 如需自定义 Google Key 代理，需使用 [langchain-google@feature/upgrade-to-google-genai-sdk](https://github.com/Instawork/langchain-google/tree/feature/upgrade-to-google-genai-sdk) 分支

## 贡献与交流
如有建议、问题或需求，欢迎 issue 或 PR。

---

> Pathfinder - Your AI Learning Navigator
