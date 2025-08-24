"""
知识图谱生成流程的路由器，负责决定下一步执行哪个代理。
"""

import logging
from typing import Dict, Any, Literal, List, Optional, Union

from ..models import PipelineState

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定义代理阶段类型
AgentStage = Literal[
    "planning", 
    "architect_finished", 
    "researching", 
    "research_finished", 
    "writing", 
    "write_finished", 
    "editing",
    "editor_finished",
    "inspecting",
    "inspection_finished",
    "completed"
]

def route_to_next_agent(state: PipelineState) -> str:
    """
    路由器函数，决定下一个要执行的代理。
    
    参数:
        state: 当前管道状态
        
    返回:
        下一个要执行的代理的名称
    """
    current_stage: AgentStage = state.current_stage
    
    # 记录当前阶段
    logger.info(f"当前阶段: {current_stage}")
    
    # 根据当前阶段决定下一个要执行的代理
    if current_stage == "planning":
        # 规划阶段后执行架构师代理
        return "architect"
        
    elif current_stage == "architect_finished":
        # 架构师完成后开始研究阶段
        state.current_stage = "researching"
        return "researcher"
        
    elif current_stage == "researching":
        # 如果还在研究阶段，继续执行研究员代理
        return "researcher"
        
    elif current_stage == "research_finished":
        # 研究完成后开始撰写阶段
        state.current_stage = "writing"
        return "writer"
        
    elif current_stage == "writing":
        # 如果还在撰写阶段，继续执行撰稿人代理
        return "writer"
        
    elif current_stage == "write_finished":
        # 撰写完成后开始编辑阶段
        state.current_stage = "editing"
        return "editor"
        
    elif current_stage == "editing":
        # 如果还在编辑阶段，继续执行编辑代理
        return "editor"
        
    elif current_stage == "editor_finished":
        # 编辑完成后开始检查阶段
        state.current_stage = "inspecting"
        return "inspector"
        
    elif current_stage == "inspecting":
        # 如果还在检查阶段，继续执行检查代理
        return "inspector"
        
    elif current_stage == "inspection_finished":
        # 检查完成后，流程结束
        state.current_stage = "completed"
        return "done"
    
    # 默认情况，如果无法确定下一步，返回完成状态
    logger.warning(f"无法为阶段 '{current_stage}' 确定下一个代理，流程结束")
    state.current_stage = "completed"
    return "done"
