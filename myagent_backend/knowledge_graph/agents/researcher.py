"""
Researcher agent for the Knowledge Graph Generator.
"""

import json
import logging
from typing import Dict, List, Any, Tuple, Annotated, Sequence, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END

from ..models import PipelineState, NetworkXGraph
from ..prompts import RESEARCHER_SYSTEM_PROMPT, RESEARCHER_HUMAN_PROMPT
from ..search_tools import search_tools
from .models import ResearchedData
from ..config import get_llm
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建工具字典，方便通过名称查找
tools_by_name = {tool.name: tool for tool in search_tools}

# 定义研究代理状态
class ResearchAgentState(TypedDict):
    """研究代理的状态"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    node_id: str
    node_title: str
    node_type: str
    topic: str
    context: str
    research_data: Dict
    completed: bool

# LangGraph节点函数

def call_llm(state: ResearchAgentState, config: RunnableConfig = None):
    """调用LLM处理研究请求"""
    # 如果这是第一条消息，创建系统提示
    llm = get_llm(model='gemini-1.5-pro')
    model = llm.bind_tools(search_tools)
    if len(state["messages"]) == 0:
        # 获取节点类型特定的搜索策略
        search_strategy = {
            "core": "详尽研究核心概念的定义、历史和重要性",
            "prerequisite": "研究这个前置知识对于理解主题的必要性",
            "component": "探索这个组成部分如何融入主要主题",
        }.get(state["node_type"], "详细研究此概念的关键方面")
        
        # 使用导入的提示模板并进行格式化
        context_info = f"以下是结点的简要介绍:\n\n{state['context']}\n\n这个节点是'{state['node_type']}'类型。{search_strategy}。"
        
        # 创建系统消息
        system_message = SystemMessage(content=RESEARCHER_SYSTEM_PROMPT)
        
        # 创建人类消息，使用现有的RESEARCHER_HUMAN_PROMPT格式化
        formatted_prompt = RESEARCHER_HUMAN_PROMPT.format(
            topic=state['topic'],
            node_title=state['node_title'],
            context=context_info
        )
        human_message = HumanMessage(content=formatted_prompt)
        
        response = model.invoke([system_message, human_message], config)        
        # 返回系统消息和人类消息
        return {"messages": [system_message, human_message, response]}
    
    response = model.invoke(state["messages"], config)
    return {"messages": [response]}

def call_tools(state: ResearchAgentState):
    """执行工具调用"""
    outputs = []
    # 遍历最后一条消息中的工具调用
    for tool_call in state["messages"][-1].tool_calls:
        # 通过名称获取工具
        tool_result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
        outputs.append(
            ToolMessage(
                content=tool_result,
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )
    return {"messages": outputs}

def should_continue(state: ResearchAgentState):
    """决定是否继续执行或结束"""
    messages = state["messages"]
    last_message = messages[-1]
    
    # 跟踪连续的思考次数，避免陷入思考循环
    consecutive_thinking = 0
    for i in range(len(messages)-1, -1, -1):
        if (hasattr(messages[i], "name") and messages[i].name == "think_tool"):
            consecutive_thinking += 1
        else:
            break
    
    # 如果连续思考超过3次，强制进行搜索或返回结果
    if consecutive_thinking >= 3:
        logger.warning("检测到连续思考超过3次，强制进行搜索或提供结果")
        return "force_action"
    
    # 如果最后一条消息不是工具调用，尝试提取研究数据
    if not getattr(last_message, "tool_calls", None):
        try:
            # 尝试从最后一条消息中提取JSON
            content = last_message.content
            
            # 从响应中提取JSON，更强大的JSON提取
            json_str = None
            if "```json" in content:
                parts = content.split("```json")
                if len(parts) > 1:
                    json_parts = parts[1].split("```")
                    if len(json_parts) > 0:
                        json_str = json_parts[0].strip()
            elif "```" in content:
                parts = content.split("```")
                if len(parts) > 1:
                    json_str = parts[1].strip()
            else:
                # 尝试寻找{ }包围的内容
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = content.strip()
            
            if not json_str:
                logger.error("无法从响应中提取JSON内容")
                return "retry"
                
            # 记录提取的JSON以便调试
            logger.debug(f"提取的JSON字符串: {json_str[:100]}...")
                
            # 尝试清理和修复常见JSON错误
            json_str = json_str.replace('\n', ' ').replace('\r', ' ')
            json_str = re.sub(r',\s*}', '}', json_str)  # 移除JSON对象末尾的逗号
            json_str = re.sub(r',\s*]', ']', json_str)  # 移除JSON数组末尾的逗号
                
            data = json.loads(json_str)
            
            # 验证数据
            if data.get("definition") and len(data.get("key_points", [])) >= 2:
                return "end"
            else:
                # 数据不完整，继续对话
                logger.warning(f"研究数据不完整: definition={bool(data.get('definition'))}, key_points={len(data.get('key_points', []))}")
                return "retry"
        except json.JSONDecodeError as e:
            logger.error(f"解析研究结果时出错: {e}")
            return "retry"
        except Exception as e:
            logger.error(f"处理结果时出现意外错误: {str(e)}")
            return "retry"
    
    # 检测think_tool调用，支持ReAct模式
    is_think_tool_call = False
    if getattr(last_message, "tool_calls", None):
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == "think_tool":
                is_think_tool_call = True
                break
    
    # 如果是think_tool调用，继续执行
    if is_think_tool_call:
        logger.info("检测到思考工具调用，继续ReAct循环")
        return "continue"
    
    # 如果是其他工具调用，继续执行
    return "continue"

def retry_research(state: ResearchAgentState):
    """当数据不完整时，要求模型重试"""
    retry_message = HumanMessage(content="""
您的回答缺少完整的研究数据。请确保您的回复包含:
1. definition: 简洁明确的定义
2. key_points: 至少3个关键点
3. examples: 示例或应用
4. sources: 信息来源

请使用工具进行更多研究，并以有效的JSON格式返回。
""")
    return {"messages": [retry_message]}

def force_action(state: ResearchAgentState):
    """强制模型采取行动，防止陷入思考循环"""
    action_message = HumanMessage(content="""
我注意到你进行了多次连续的思考而没有采取实际行动。现在，请执行以下操作之一：

1. 如果你已收集了足够信息，请直接以JSON格式提供完整的研究结果，包含：
   - definition: 简洁明确的定义
   - key_points: 至少3个关键点
   - examples: 示例或应用
   - sources: 信息来源

2. 如果你还需要更多信息，请立即使用search_web或search_node_details工具进行具体搜索，
   而不是继续使用think_tool。

请立即采取具体行动而非继续分析。
""")
    return {"messages": [action_message]}

def process_data(state: ResearchAgentState):
    """处理并保存最后消息中的数据"""
    try:
        # 如果没有找到临时存储的JSON字符串，尝试从最后消息中提取
        content = state["messages"][-1].content
        
        # 尝试提取JSON
        if "```json" in content:
            parts = content.split("```json")
            if len(parts) > 1:
                json_parts = parts[1].split("```")
                if json_parts:
                    json_str = json_parts[0].strip()
        elif "```" in content:
            parts = content.split("```")
            if len(parts) > 1:
                json_str = parts[1].strip()
        else:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = content.strip()
        
        # 解析JSON数据
        if json_str:
            data = json.loads(json_str)
            
            # 在节点函数中更新状态（这会被正确保存）
            state["research_data"] = data
            state["completed"] = True
            
            # 添加带有特殊标记的系统消息
            research_completed_message = SystemMessage(
                content=f"RESEARCH_COMPLETED|{json_str}"
            )
            state["messages"].append(research_completed_message)
            
            logger.info(f"研究数据成功保存，completed=True, 数据键: {list(data.keys())}")
        
    except Exception as e:
        logger.error(f"处理数据时出错: {e}")
        
    return state

def extract_research_data(state: ResearchAgentState):
    """从最终状态提取研究数据并创建ResearchedData对象"""
    # 首先尝试从特殊标记消息中提取JSON
    for message in state["messages"]:
        if isinstance(message, SystemMessage) and message.content.startswith("RESEARCH_COMPLETED|"):
            try:
                # 从特殊标记消息中提取JSON字符串
                json_str = message.content.split("RESEARCH_COMPLETED|", 1)[1]
                data = json.loads(json_str)
                
                # 创建并返回ResearchedData对象
                return ResearchedData(
                    definition=data.get("definition", ""),
                    key_points=data.get("key_points", []),
                    examples=data.get("examples", []),
                    sources=[{"title": s.get("title", "未知来源"), 
                             "url": s.get("url", "#")} 
                            for s in data.get("sources", [])]
                )
            except Exception as e:
                logger.error(f"从标记消息提取研究数据时出错: {e}")
    
    # 如果没有找到特殊标记消息，尝试使用state中的research_data
    if state["research_data"]:
        data = state["research_data"]
        return ResearchedData(
            definition=data.get("definition", ""),
            key_points=data.get("key_points", []),
            examples=data.get("examples", []),
            sources=[{"title": s.get("title", "未知来源"), 
                    "url": s.get("url", "#")} 
                    for s in data.get("sources", [])]
        )
    
    # 如果没有找到研究数据，返回空对象
    logger.warning("未找到有效的研究数据")
    return ResearchedData(
        definition="",
        key_points=[],
        examples=[],
        sources=[]
    )

def research_node(
    node_id: str,
    node_title: str,
    node_type: str,
    topic: str,
    context: str,
    max_retries: int = 5
) -> Tuple[str, ResearchedData]:
    """
    研究一个节点并返回研究数据
    
    参数:
        node_id: 节点ID
        node_title: 节点标题
        node_type: 节点类型 (core, prerequisite, component)
        topic: 主题
        context: 图谱上下文
        max_retries: 最大重试次数
        
    返回:
        节点ID和研究数据
    """
    logger.info(f"正在研究节点: {node_title} (类型: {node_type})")
    
    # 定义研究工作流
    workflow = StateGraph(ResearchAgentState)
    
    # 添加节点
    workflow.add_node("llm", call_llm)
    workflow.add_node("tools", call_tools)
    workflow.add_node("retry", retry_research)    
    workflow.add_node("force_action", force_action)
    workflow.add_node("process_data", process_data)
    
    # 设置入口点
    workflow.set_entry_point("llm")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "llm",
        should_continue,
        {
            "continue": "tools",
            "retry": "retry",
            "force_action": "force_action",
            "end": "process_data",
        }
    )
    
    # 从process_data到结束
    workflow.add_edge("process_data", END)
    
    # 添加正常边
    workflow.add_edge("tools", "llm")
    workflow.add_edge("retry", "llm")
    workflow.add_edge("force_action", "llm")
    
    # 编译图
    graph = workflow.compile()
    
    # 初始化状态
    initial_state = ResearchAgentState(
        messages=[],
        node_id=node_id,
        node_title=node_title,
        node_type=node_type,
        topic=topic,
        context=context,
        research_data={},
        completed=False
    )
    
    # 执行工作流
    retries = 0
    while retries <= max_retries:
        try:
            # 运行工作流
            final_state = graph.invoke(initial_state)
            
            # 尝试从消息中提取研究数据
            research_data = extract_research_data(final_state)
            
            # 检查是否有有效的研究数据
            if research_data.definition and len(research_data.key_points) >= 2:
                logger.info(f"成功研究节点: {node_title}")
                return node_id, research_data
                
        except Exception as e:
            logger.error(f"研究节点 {node_title} 时出错: {e}")
        
        retries += 1
        if retries <= max_retries:
            logger.info(f"重试研究节点 ({retries}/{max_retries}): {node_title}")
    
    # 所有重试失败后返回最小研究数据
    logger.warning(f"无法完成节点 {node_title} 的研究，返回最小数据")
    return node_id, ResearchedData(
        definition=f"{node_title} 是与 {topic} 相关的概念。",
        key_points=[
            f"{node_title} 是 {topic} 的重要组成部分。", 
            f"由于技术原因，无法获取关于 {node_title} 的完整信息。"
        ],
        examples=[],
        sources=[]
    )

def researcher_agent(state: PipelineState) -> Dict:
    """研究员代理，研究图中的所有节点"""
    if not state.graph:
        logger.error("没有图结构可供研究")
        return {}
    
    topic = state.topic
    
    # 使用get_next_nodes_to_process获取需要研究的节点ID
    nodes_to_process_ids = state.get_next_nodes_to_process("researching")
    
    # 如果没有节点需要研究，标记为完成状态并返回
    if not nodes_to_process_ids:
        logger.info("没有新节点需要研究，研究阶段完成")
        state.current_stage = "research_finished"
        return {
            "graph": state.graph,
            "processed_nodes": state.processed_nodes,
            "current_stage": state.current_stage
        }
    
    logger.info(f"本轮将研究 {len(nodes_to_process_ids)} 个节点")
    
    # 创建描述图的上下文字符串
    context = ''
    
    # 创建研究任务
    results = []
    for node_id in nodes_to_process_ids:
        # 获取节点详细信息
        node = state.graph.get_node(node_id)
        if not node:
            logger.warning(f"无法找到节点 {node_id} 的信息")
            continue
        
        result = research_node(
            node_id=node_id,
            node_title=node.get("title", node_id),
            node_type=node.get("type", "concept"),
            topic=topic,
            context=node.get("description", "concept")
        )
        results.append(result)
    
    # 更新状态
    for node_id, research_data in results:
        # 将研究结果添加到图节点
        sources = [s.dict() for s in research_data.sources]
        state.update_node_content(
            node_id=node_id,
            content={
                "definition": research_data.definition,
                "key_points": research_data.key_points,
                "examples": research_data.examples,
                "sources": sources,
                "status": "researched"
            },
            stage="researched"
        )
    
    # 检查是否还有未研究的节点
    remaining_nodes = state.get_next_nodes_to_process("researching")
    if not remaining_nodes:
        # 如果没有剩余节点，标记为研究完成
        state.current_stage = "research_finished"
        logger.info("所有节点研究完成")
    else:
        # 如果还有未研究的节点，保持当前状态
        state.current_stage = "researching"
        logger.info(f"还有 {len(remaining_nodes)} 个节点等待研究")
        
    return {
        "graph": state.graph,
        "processed_nodes": state.processed_nodes,
        "current_stage": state.current_stage
    }
