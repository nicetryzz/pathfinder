"""
知识图谱生成器的主入口点。
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, Any

# 添加项目根目录到路径，确保可以导入modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_graph.api import generate_knowledge_graph
from knowledge_graph.utils.visualization import visualize_graph
from knowledge_graph.models import NetworkXGraph

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=os.path.join('logs', 'knowledge_graph.log'),
    filemode='a'
)
logger = logging.getLogger(__name__)

# 添加控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def main():
    """主函数（同步版本）"""
    parser = argparse.ArgumentParser(description='知识图谱生成器')
    parser.add_argument('--topic', '-t', type=str, required=True, help='知识图谱的主题')
    parser.add_argument('--output', '-o', type=str, default=None, help='输出文件路径')
    parser.add_argument('--max-steps', '-m', type=int, default=20, help='最大执行步骤数')
    parser.add_argument('--visualize', '-v', action='store_true', help='生成可视化文件')

    args = parser.parse_args()

    try:
        logger.info(f"开始为主题 '{args.topic}' 生成知识图谱")
        result = generate_knowledge_graph(args.topic, max_steps=args.max_steps)

        output_file = args.output or f"knowledge_graph_{args.topic.replace(' ', '_')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"知识图谱数据已保存到 {output_file}")

        if args.visualize and "graph" in result:
            graph = NetworkXGraph.from_dict(result["graph"])
            vis_file = f"知识图谱_{args.topic.replace(' ', '_')}"
            visualize_graph(graph, args.topic, vis_file)
            logger.info(f"知识图谱可视化已保存")

    except Exception as e:
        logger.error(f"生成知识图谱时出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    os.makedirs('logs', exist_ok=True)
    main()
