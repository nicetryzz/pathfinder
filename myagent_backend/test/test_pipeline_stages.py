"""
分阶段测试工具 - 逐步测试知识图谱生成流程

用法:
1. 运行从头到尾的流程：python -m myagent_backend.test.test_pipeline_stages --topic "LLM AI agent" --stage all
2. 运行单个阶段：python -m myagent_backend.test.test_pipline_stages --agent architect --topic "LLM AI agent" --save states/LLM_AI_agent_architect.json
3. 从保存的状态继续：python -m myagent_backend.test.test_pipeline_stages --load states/ai_researcher.json --stage writer
4. 仅可视化：python -m myagent_backend.test.test_pipeline_stages --load states/ai_final.json --visualize
"""

import os
import sys
import json
import argparse
import logging
from typing import Optional, List, Dict, Any

# 添加项目根目录到路径，以便正确导入模块
# 获取当前脚本的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录 (myagent_backend)
project_root = os.path.abspath(os.path.join(current_dir, ".."))
# 将项目根目录添加到系统路径
if project_root not in sys.path:
    sys.path.append(project_root)

# 现在可以导入项目模块
from myagent_backend.knowledge_graph.models import PipelineState, NetworkXGraph
from myagent_backend.knowledge_graph.utils.visualization import visualize_graph
from myagent_backend.knowledge_graph.agents.architect import architect_agent
from myagent_backend.knowledge_graph.agents.researcher import researcher_agent
from myagent_backend.knowledge_graph.agents.writer import writer_agent
from myagent_backend.knowledge_graph.agents.editor import editor_agent
from myagent_backend.knowledge_graph.agents.inspector import inspector_agent

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定义阶段和对应的代理
STAGES = {
    "architect": architect_agent,
    "researcher": researcher_agent,
    "writer": writer_agent,
    "editor": editor_agent,
    "inspector": inspector_agent
}

# 定义阶段顺序
STAGE_ORDER = ["architect", "researcher", "writer", "editor", "inspector"]

def ensure_dir(filepath):
    """确保文件的目录存在"""
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

def run_pipeline_stages(
    topic: Optional[str] = None,
    stage: str = "all",
    load_path: Optional[str] = None,
    save_dir: Optional[str] = None,
    visualize: bool = False,
    visualize_all: bool = False
):
    """运行知识图谱生成的指定阶段
    
    参数:
        topic: 主题 (仅在创建新状态时需要)
        stage: 要运行的阶段 (单个阶段名称或 "all")
        load_path: 加载状态的文件路径
        save_dir: 保存状态的目录
        visualize: 是否在结束时可视化图谱
        visualize_all: 是否在每个阶段后可视化图谱
    """
    # 加载或创建状态
    if load_path:
        logger.info(f"从 {load_path} 加载状态")
        state = PipelineState.load_state(load_path)
        # 如果提供了新主题，更新主题
        if topic:
            state.topic = topic
    elif topic:
        logger.info(f"为主题 '{topic}' 创建新状态")
        state = PipelineState(topic=topic)
        state.initialize_graph()
    else:
        logger.error("必须提供 --topic 或 --load 参数")
        return
        
    # 如果只是可视化，不运行代理
    if visualize and stage == "none":
        if state.graph:
            visualize_file = f"知识图谱_{state.topic.replace(' ', '_')}.png"
            logger.info(f"可视化图谱到 {visualize_file}")
            visualize_graph(state.graph, state.topic, visualize_file)
        else:
            logger.error("没有可视化的图谱数据")
        return
    
    # 确定要运行的阶段
    stages_to_run = []
    if stage == "all":
        stages_to_run = STAGE_ORDER
    elif stage in STAGES:
        stages_to_run = [stage]
    else:
        logger.error(f"未知阶段: {stage}")
        return
    
    # 执行指定阶段
    last_stage = None
    for current_stage in stages_to_run:
        agent_func = STAGES[current_stage]
        logger.info(f"执行 {current_stage} 阶段")
        
        try:
            # 运行当前阶段的代理
            result = agent_func(state)
            logger.info(f"{current_stage} 阶段执行完成")
            logger.info(f"当前状态: {state.current_stage}")
            
            # 在我们的新设计中，代理直接操作state对象，不需要从结果中获取图谱
            # 但我们仍检查结果以保持兼容性
            # if result and isinstance(result, dict) and "graph" in result:
            #     pass  # 在新设计中不需要这个步骤
            
            # 如果当前阶段是 inspector 且状态为 researching，则循环回研究阶段
            if current_stage == "inspector" and state.current_stage == "researching":
                logger.info("检测到Inspector添加了新节点，需要重新研究")
                
                if save_dir:
                    save_path = os.path.join(save_dir, f"{state.topic.replace(' ', '_')}_{current_stage}_loop.json")
                    ensure_dir(save_path)
                    logger.info(f"保存循环状态到 {save_path}")
                    state.save_state(save_path)
                    
                # 重新运行研究阶段
                logger.info("重新运行研究阶段")
                result = researcher_agent(state)
                # 不需要额外设置state.graph，因为researcher_agent会直接更新state对象
                    
                logger.info(f"研究阶段重新执行完成，当前状态: {state.current_stage}")
            
            # 保存阶段状态
            if save_dir:
                save_path = os.path.join(save_dir, f"{state.topic.replace(' ', '_')}_{current_stage}.json")
                ensure_dir(save_path)
                logger.info(f"保存阶段状态到 {save_path}")
                state.save_state(save_path)
            
            # 可视化阶段结果
            if visualize_all and state.graph:
                visualize_file = f"知识图谱_{state.topic.replace(' ', '_')}_{current_stage}.png"
                logger.info(f"可视化阶段图谱到 {visualize_file}")
                visualize_graph(state.graph, state.topic, visualize_file)
                
            last_stage = current_stage
                
        except Exception as e:
            logger.error(f"执行 {current_stage} 阶段时出错: {e}")
            break
    
    # 最终可视化
    if visualize and state.graph:
        stage_suffix = f"_{last_stage}" if last_stage else ""
        visualize_file = f"知识图谱_{state.topic.replace(' ', '_')}{stage_suffix}.png"
        logger.info(f"可视化最终图谱到 {visualize_file}")
        visualize_graph(state.graph, state.topic, visualize_file)

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="知识图谱阶段测试工具")
    
    parser.add_argument("--topic", help="知识图谱主题")
    parser.add_argument("--stage", default="all", 
                        choices=list(STAGES.keys()) + ["all", "none"], 
                        help="要执行的阶段")
    parser.add_argument("--load", help="加载状态的JSON文件路径")
    parser.add_argument("--save-dir", help="保存状态的目录")
    parser.add_argument("--visualize", action="store_true", help="可视化最终图谱")
    parser.add_argument("--visualize-all", action="store_true", help="可视化每个阶段的图谱")
    
    args = parser.parse_args()
    
    run_pipeline_stages(
        topic=args.topic,
        stage=args.stage,
        load_path=args.load,
        save_dir=args.save_dir,
        visualize=args.visualize,
        visualize_all=args.visualize_all
    )

if __name__ == "__main__":
    main()
