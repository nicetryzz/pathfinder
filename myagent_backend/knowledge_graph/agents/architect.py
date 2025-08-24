"""
Architect agent for the Knowledge Graph Generator.
"""

import json
import logging
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from ..models import PipelineState, NetworkXGraph
from ..utils.visualization import visualize_graph
from ..prompts import ARCHITECT_SYSTEM_PROMPT
from ..config import get_llm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def architect_agent(state: PipelineState) -> Dict:
    """架构师代理，创建初始知识图谱结构"""
    topic = state.topic
    logger.info(f"架构师代理正在处理主题: {topic}")
    
    # 初始化图（如果尚未初始化）
    if not state.graph:
        state.initialize_graph()
    
    # 创建提示
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
        HumanMessage(content=f"为主题 '{topic}' 创建知识图谱结构")
    ])
    
    # 使用LLM执行 - 先格式化提示模板生成消息
    messages = prompt.format_messages()
    llm = get_llm()
    response = llm.invoke(messages)
    response_text = response.content
    print("response_text:" + response_text)
    
    try:
        # 从响应中提取JSON
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].strip()
        else:
            json_str = response_text.strip()
            
        graph_data = json.loads(json_str)
        
        # 创建或更新NetworkX图
        nx_graph = NetworkXGraph()
        
        # 添加节点
        for node in graph_data.get("nodes", []):
            nx_graph.add_node(
                node_id=node["node_id"],
                title=node["title"],
                type=node.get("type", "concept"),
                description=node.get("description", ""),
                status="created"
            )
        
        # 添加边
        for edge in graph_data.get("edges", []):
            nx_graph.add_edge(
                source=edge["source_id"],
                target=edge["target_id"],
                relationship=edge.get("relationship", edge.get("label", "relates_to"))
            )
        
        # 更新状态
        state.graph = nx_graph
        state.current_stage = "architect_finished"
        
        # 使用可视化函数生成图表
        visualize_graph(nx_graph, topic, f"知识图谱_{topic.replace(' ', '_')}.png")
        
        return {"graph": nx_graph, "current_stage": "architect_finished"}
    
    except Exception as e:
        logger.error(f"解析架构师代理响应时出错: {e}")
        # 创建简单的备用图
        if not state.graph or len(state.graph.get_nodes()) == 0:
            nx_graph = NetworkXGraph()
            node_id = f"{topic.lower().replace(' ', '-')}"
            nx_graph.add_node(
                node_id=node_id,
                title=topic,
                type="core",
                status="created"
            )
            state.graph = nx_graph
            
        state.current_stage = "researching"
        return {"graph": state.graph, "current_stage": "researching"}
