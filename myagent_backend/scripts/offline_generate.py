import os
import json
import argparse
from myagent_backend.knowledge_graph.api import generate_knowledge_graph

def parse_args():
    parser = argparse.ArgumentParser(description="批量生成知识图谱 JSON 文件")
    parser.add_argument('--input', type=str, default=None, help='主题列表文件，每行一个主题')
    parser.add_argument('--output', type=str, default=None, help='输出目录')
    return parser.parse_args()

def load_topics(input_path):
    if input_path and os.path.exists(input_path):
        with open(input_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    # 默认主题列表
    return [
        # "Transformer模型全解析",
        # "RAG vs. Fine-tuning：技术选型与实现",
        "AI Agent的系统设计",
        "大型语言模型的分布式训练"
    ]

def main():
    args = parse_args()
    topics = load_topics(args.input)
    output_dir = args.output or os.path.join(os.path.dirname(__file__), "..", "precomputed_maps")
    os.makedirs(output_dir, exist_ok=True)
    for topic in topics:
        print(f"正在生成主题: {topic}")
        result = generate_knowledge_graph(topic)
        out_path = os.path.join(output_dir, f"{topic}_map.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"已保存: {out_path}")

if __name__ == "__main__":
    main()
