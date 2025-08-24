
# Pathfinder MVP - 技术设计文档 (TDD) V3.0
**文档版本**: 3.0（与PRD v4.0及代码实现同步）

**更新日期**: 2025年8月22日

**负责人**: 您

**战略副驾**: AI技术战略副驾

---

## 摘要
本文档在V2.9的基础上进行迭代，使其与产品需求文档（PRD）v4.0及最新代码实现完全对齐。此TDD详细阐述了**“面向知识图谱构建的多智能体协作框架”的技术实现细节**。
该框架旨在技术上落地PRD v4.0中定义的“AI向导”与“对话共创”产品愿景，通过一条基于LangGraph构建、包含多个专业智能体的协作流水线，动态地规划、研究、撰写、审查并自我迭代，最终生成结构严谨、内容一致的高质量知识图谱。

---

## 1. 系统架构 (System Architecture)
为支持多智能体协作的复杂流程，我们的系统架构设计如下，其核心在于后端强大的AI智能体引擎。

```mermaid
graph TD
    subgraph "用户端 (Browser)"
        A[前端应用 (Vue.js / Streamlit)]
    end

    subgraph "云服务 (Cloud Platform)"
        B[API网关]
        C[后端服务 (Python/FastAPI)]
        D[AI智能体引擎 (LangGraph)]
        E[LLM模型 (Gemini Pro API)]
        F[专业搜索引擎 (Tavily API)]
    end

    A -- 1. 初始请求 --> B;
    B -- 2. --> C;
    C -- 3. 调用多智能体研究流水线 --> D;
    D -- 4. 流水线开始执行 --> E & F;
    E & F -- 5. --> D;
    D -- 6. 组装图谱JSON --> C;
    C -- 7. 返回图谱JSON --> B;
    B -- 8. 响应 --> A;
```

---

## 2. 技术选型 (Technology Stack)
为了实现我们先进的多智能体协作框架，并兼顾MVP阶段对开发速度的要求，我们选择了以下经过验证的技术栈组合。

| 类别   | 技术                | 理由 |
|--------|---------------------|------|
| 前端   | Vue.js 3 / Streamlit | Vue.js以其平缓的学习曲线和强大的生态，适合构建功能完善的Web应用。对于求职Demo，Streamlit是更优选，它能用纯Python在数小时内搭建出优雅的数据应用界面，让我们能100%聚焦于后端AI逻辑。 |
| 后端   | Python + FastAPI     | Python是AI领域的“母语”。FastAPI以其卓越的性能、对异步操作的原生支持（对处理长时运行的AI任务至关重要）以及自动生成API文档的便捷性，成为构建高性能AI后端的最佳选择。 |
| AI/LLM集成 | Gemini Pro + LangGraph | Gemini Pro在多语言理解、复杂推理和遵循指令方面表现出色，是驱动我们多个专业Agent的核心大脑。LangGraph则为我们提供了构建有状态、可循环的复杂智能体流程的强大框架，是实现我们“多智能体协作流水线”这一核心逻辑的基石。 |
| 搜索引擎 | Tavily API           | Tavily是专为AI Agent设计的搜索引擎。它返回的结果更简洁、更聚焦于事实，极大地降低了LLM从搜索结果中提取关键信息的难度和Token消耗，是实现高效、精准研究的关键工具。 |

---

## 3. 核心逻辑实现: 多智能体研究流水线

### 3.1 核心原则：基于状态机的流水线作业
我们将整个知识生成过程，抽象为一个基于LangGraph的状态机。工作流围绕一个中心化的状态对象 (PipelineState) 进行，每个Agent作为一个节点，接收当前状态，执行其专业任务，然后更新状态。一个中央Router函数根据更新后的状态决定下一个激活哪个Agent节点。

### 3.2 LangGraph图谱生成流程
**State (状态对象)**: PipelineState是整个流水线的“中央数据库”，它以一个NetworkXGraph对象为核心，追踪着知识图谱从无到有的全过程，并记录每个节点的处理进度（processed_nodes）。

**Node 1: Architect_Agent (知识架构师)**
触发条件: 工作流启动。

职责: 接收用户主题，调用LLM，根据ARCHITECT_SYSTEM_PROMPT的严格约束，生成一个包含core, prerequisite, component三种类型节点的初步知识图谱结构。

输出: 更新PipelineState中的graph对象，包含初始的节点和边。current_stage更新为 architect_finished。

**Node 2: Researcher_Agent (研究员)**
触发条件: current_stage为 researching。

职责: 并行地为所有status为created的节点进行深度研究。

内部实现: 每个研究任务本身就是一个迷你的ReAct Agent。它使用一个独立的LangGraph状态机，通过“思考(Thinking) -> 行动(Action - 调用搜索工具) -> 观察(Observation)”的循环，迭代式地收集信息，直到产出满足质量要求的结构化“研究数据包”（包含定义、关键点、示例、来源）。

输出: 将“研究数据包”的内容更新到PipelineState中对应节点的属性上，并将节点status更新为researched。当所有待研究节点处理完毕，current_stage更新为 research_finished。

**Node 3: Writer_Agent (撰稿人)**
触发条件: current_stage为 writing。

职责: 并行地为所有status为researched的节点撰写初稿。

工作模式: 接收节点的“研究数据包”，调用LLM生成draft_text（详细文稿）和node_summary（摘要）。

输出: 将文稿和摘要更新到PipelineState的对应节点中，并将节点status更新为written。当所有待撰写节点处理完毕，current_stage更新为 write_finished。

**Node 4: Editor_Agent (总编辑)**
触发条件: current_stage为 editing。

职责: 逐一审阅status为written的节点，确保全局内容的一致性和逻辑自洽。

工作模式: 在处理一个节点时，会动态收集其所有相邻节点的摘要作为上下文，然后调用LLM对当前节点内容进行优化，确保内容能与其他节点良好衔接。

输出: 将优化后的final_text更新到PipelineState的对应节点中，并将节点status更新为edited。当所有待编辑节点处理完毕，current_stage更新为 editor_finished。

**Node 5: Inspector_Agent (审查员)**
触发条件: current_stage为 inspecting。

职责: 从全局视角审视整个知识图谱的结构完整性，提出结构性修改建议（增加或删除节点）。

工作模式: 接收完整的图谱结构和所有节点的摘要，调用LLM生成一份包含ADD_NODE或DELETE_NODE建议的审查报告。系统会自动应用这些建议，直接修改图谱结构。

输出 (路由关键):

如果有新节点被添加，current_stage将被重置为 researching，触发工作流的自我迭代。

如果没有结构性修改，current_stage更新为 inspection_finished，流水线正常结束。

---

---

## 4. 后端设计与 API

### 4.1 架构决策与未来演进
- **MVP架构决策：单一数据包API (Single Data Packet API)**
  - 决策：MVP阶段战略性选择通过单一API端点，一次性返回前端渲染所需的全部数据。
  - 理由：极致的用户体验（点击节点瞬间响应）、最高的开发效率（简化前后端逻辑）、清晰的故事线（智能封装）。

- **未来架构演进：列表-详情模式 (List-Detail Pattern)**
  - 规划：产品走向生产环境、图谱规模变大时，架构将平滑演进。/maps接口只返回轻量级图谱结构，新增/nodes/{node_id}接口按需获取节点详情，以优化性能。

### 4.2 API接口设计
| 端点 | 方法 | 路径 | 描述 |
|------|------|------|------|
| 获取知识图谱 | GET | /api/v1/maps/{topic_name} | 获取指定主题的、预先生成好的完整知识图谱。前端获取核心数据的唯一入口。 |
| 节点AI助教对话 | POST | /api/v1/nodes/chat | 预留端点，用于实现PRD中的“对话共创”愿景。 |

---

## 5. 前后端数据契约 (Agent to Frontend Data Contract)
由 Assembler Agent 生成，由后端 API 返回给前端的最终 JSON 结构。

### 5.1 顶层结构
| 字段名   | 类型             | 描述           |
|----------|------------------|----------------|
| metadata | Metadata Object  | 关于图谱的元数据 |
| graph    | GraphData Object | 核心图谱数据   |

### 5.2 详细模型定义
```json
// KnowledgeGraphResponse (顶层对象)
{
  "metadata": {
    "topic": "string",
    "generated_at": "string (ISO 8601)",
    "total_nodes": "integer",
    "total_edges": "integer"
  },
  "graph": {
    "nodes": [
      {
        "id": "string",
        "title": "string",
        "type": "string ('core'|'prerequisite'|'component')",
        "description": "string",
        "content": {
          "definition": "string",
          "key_points": ["string"],
          "final_text": "string (Markdown格式)",
          "examples": ["string"],
          "sources": [
            {
              "title": "string",
              "url": "string"
            }
          ]
        }
      }
    ],
    "edges": [
      {
        "source": "string (node_id)",
        "target": "string (node_id)",
        "label": "string"
      }
    ]
  }
}
```

---

## 6. 前端设计与规划

### 6.1 页面布局
采用经典的双栏布局：左侧为图谱画布 (Graph Canvas)，右侧为节点详情窗格 (Node Detail Pane)。

### 6.2 核心交互流程
1. 页面加载：前端调用 GET /api/v1/maps/{topic_name} 获取完整的图谱 JSON。
2. 图谱渲染：
   - 使用 Vis.js 将 graph.nodes 和 graph.edges 渲染到左侧画布。
   - 关键：根据每个节点的 type 字段，在渲染时赋予不同的颜色、大小或形状，直观展示知识结构。
3. 节点交互：
   - 监听 Vis.js 的 click 事件，获取被点击节点的 id。
   - 根据 id 在本地完整 JSON 数据中查找对应节点对象。
4. 详情展示（Markdown 渲染）：
   - 获取节点对象中的 content.final_text（Markdown 字符串）。
   - 使用 marked.js 库的 marked.parse() 函数将其转换为 HTML。
   - 将生成的 HTML 动态渲染到右侧详情窗格。

---

## 7. 部署方案

- **前端（静态文件）**：部署于 Vercel 或 GitHub Pages，实现 CI/CD，提交代码自动部署。
- **后端（FastAPI）**：部署于 Google Cloud Run，完全托管，按需付费，成本效益高。