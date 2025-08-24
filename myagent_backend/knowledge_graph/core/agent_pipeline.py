"""
Implementation of the Knowledge Graph Generator using LangGraph.
"""

import json
import logging
from typing import Dict, List, Any, Optional

from langgraph.graph import StateGraph, END

from .models import PipelineState, NetworkXGraph
from .agents import architect_agent, researcher_agent, writer_agent, editor_agent, inspector_agent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== 路由函数 =====
def router(state: PipelineState) -> str:
    """根据当前状态确定工作流程的下一个步骤。"""
    logger.info(f"--- Routing: Current stage is '{state.current_stage}' ---")
    
    if state.current_stage == "planning":
        return "architect"
    
    if state.current_stage == "architect_finished":
        logger.info("Architect finished, moving to researcher.")
        state.current_stage = "researching"
        return "researcher"
        
    if state.current_stage == "researching":
        # researcher_agent 内部处理循环，完成后会更新状态
        return "researcher"
        
    if state.current_stage == "research_finished":
        logger.info("Research finished, moving to writer.")
        state.current_stage = "writing"
        return "writer"
        
    if state.current_stage == "writing":
        # writer_agent 内部处理循环，完成后会更新状态
        return "writer"
        
    if state.current_stage == "write_finished":
        logger.info("Writer finished, moving to editor.")
        state.current_stage = "editing"
        return "editor"
        
    if state.current_stage == "editor_finished":
        logger.info("Editor finished, moving to inspector.")
        state.current_stage = "inspecting"
        return "inspector"
    
    if state.current_stage == "inspecting":
        # inspector_agent 内部处理循环
        return "inspector"
        
    if state.current_stage == "inspection_finished":
        logger.info("--- Workflow Complete ---")
        return END
    
    # 处理Inspector添加新节点后回到研究阶段的情况
    # 这里Inspector已经将current_stage设置为"researching"
    if state.current_stage == "researching" and hasattr(state, 'inspection_report'):
        logger.info("Inspector added new nodes, returning to research phase.")
        return "researcher"
        
    # Fallback for any other state
    logger.warning(f"Unknown state '{state.current_stage}', ending workflow.")
    return END

# ===== Main Workflow =====

def create_knowledge_graph_workflow() -> StateGraph:
    """创建知识图谱生成的LangGraph工作流"""
    # 定义工作流图
    workflow = StateGraph(PipelineState)
    
    # 添加节点到图中
    workflow.add_node("architect", architect_agent)
    workflow.add_node("researcher", researcher_agent)
    workflow.add_node("writer", writer_agent)
    workflow.add_node("editor", editor_agent)
    workflow.add_node("inspector", inspector_agent)
    
    # 设置入口点
    workflow.set_entry_point("architect")
    
    # 使用统一的路由函数来管理所有转换
    workflow.add_conditional_edges(
        "architect",
        router,
    )
    workflow.add_conditional_edges(
        "researcher",
        router,
    )
    workflow.add_conditional_edges(
        "writer",
        router,
    )
    workflow.add_conditional_edges(
        "editor",
        router,
    )
    workflow.add_conditional_edges(
        "inspector",
        router,
    )
    
    # 编译工作流
    return workflow.compile()

# ===== API Function =====

def generate_knowledge_graph(topic: str) -> NetworkXGraph:
    """
    生成知识图谱的主API函数
    
    参数:
        topic: 要生成知识图谱的主题
        
    返回:
        生成的知识图谱数据
    """
    logger.info(f"正在为主题生成知识图谱: {topic}")
    
    # 创建初始状态
    state = PipelineState(topic=topic)
    
    # 创建并初始化图结构
    state.initialize_graph()
    
    # 创建工作流
    workflow = create_knowledge_graph_workflow()
    
    # 执行工作流
    try:
        final_state = workflow.invoke(state)
        
        # 获取最终图数据
        if final_state.graph:
            # 直接返回NetworkX图
            return final_state.graph
        else:
            # 如果图为空，返回空图谱
            nx_graph = NetworkXGraph()
            nx_graph.graph = {"topic": topic, "status": "incomplete"}
            return nx_graph
        
    except Exception as e:
        logger.error(f"生成知识图谱时出错: {e}")
        nx_graph = NetworkXGraph()
        nx_graph.graph = {"error": str(e), "topic": topic}
        return nx_graph