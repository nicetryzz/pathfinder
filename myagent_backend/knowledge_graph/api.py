"""
知识图谱服务的API模块，提供生成和检索知识图谱的接口。
"""

import logging
import os
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from .models import PipelineState, NetworkXGraph
from .agents.models import GraphData
from .core.router import route_to_next_agent
from .agents.architect import architect_agent
from .agents.researcher import researcher_agent
from .agents.writer import writer_agent
from .agents.editor import editor_agent
from .agents.inspector import inspector_agent
from .utils.visualization import visualize_graph

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=os.path.join('logs', 'knowledge_graph.log'),
    filemode='a'
)
logger = logging.getLogger(__name__)

# 添加控制台处理器，同时输出到控制台
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 代理映射表
AGENT_MAP = {
    "architect": architect_agent,
    "researcher": researcher_agent,
    "writer": writer_agent,
    "editor": editor_agent,
    "inspector": inspector_agent,
    "done": lambda state: {"message": "知识图谱生成完成", "current_stage": state.current_stage}
}

def generate_knowledge_graph(topic: str, max_steps: int = 3) -> Dict[str, Any]:

    """
    生成知识图谱
    
    参数:
        topic: 知识图谱主题
        max_steps: 最大步骤数，防止无限循环
        
    返回:
        包含生成的知识图谱数据的字典
    """
    logger.info(f"开始为主题 '{topic}' 生成知识图谱")
    
    # 初始化流程状态
    state = PipelineState(
        topic=topic,
        current_stage="planning"
    )
    
    # 初始化图结构
    state.initialize_graph()
    
    # 执行代理流程
    last_stage = ""
    
    while state.inspection_iter <= max_steps:
        step = state.inspection_iter
        # 检查是否完成
        if state.current_stage == "completed":
            logger.info(f"知识图谱生成完成，总共用了 {step} 步")
            break
        
        # 记录阶段变化
        logger.info(f"阶段变化: {last_stage} -> {state.current_stage}")
        last_stage = state.current_stage
        
        # 获取下一个要执行的代理
        next_agent = route_to_next_agent(state)
        logger.info(f"步骤 {step}: 执行代理 {next_agent}")
        
        try:
            # 执行代理
            agent_func = AGENT_MAP.get(next_agent)
            if not agent_func:
                logger.error(f"未知代理: {next_agent}")
                break
                
            # 执行代理并获取结果
            result = agent_func(state)
                
            if "current_stage" in result:
                # 更新当前阶段
                state.current_stage = result["current_stage"]
            
            if state.current_stage == "editor_finished":
                state.inspection_iter += 1
            
        except Exception as e:
            logger.error(f"执行代理 {next_agent} 时出错: {e}")
            break
    
    # 检查是否达到最大步骤数
    if step > max_steps:
        logger.warning(f"达到最大步骤数 {max_steps}，强制结束流程")
    
    # 获取最终图数据
    if state.graph:
        try:
            # 尝试生成可视化
            visualize_graph(
                graph=state.graph,
                topic=topic,
                output_file=f"知识图谱_{topic.replace(' ', '_')}.png"
            )
            logger.info(f"知识图谱可视化已保存")
        except Exception as e:
            logger.error(f"生成可视化时出错: {e}")
    
    # 返回结果
    return {
        "topic": topic,
        "graph": state.graph.to_dict() if state.graph else {},
        "current_stage": state.current_stage,
        "steps": step,
        "inspection_report": state.inspection_report,
    }

def get_knowledge_graph(graph_id: str) -> Optional[Dict[str, Any]]:
    """
    获取指定ID的知识图谱
    
    参数:
        graph_id: 知识图谱ID
        
    返回:
        知识图谱数据，如果不存在则返回None
    """
    # 此处应实现从数据库或文件系统获取已生成的知识图谱
    # 目前是一个简单的占位函数
    return None
