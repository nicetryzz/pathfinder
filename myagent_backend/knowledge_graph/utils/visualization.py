

"""
知识图谱可视化工具
"""

import logging
from typing import Optional
import matplotlib.pyplot as plt
import networkx as nx
from pyvis.network import Network
import matplotlib
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入当前包的模型
from ..models import NetworkXGraph

def setup_chinese_font():
    """
    设置matplotlib以支持中文显示
    """
    try:
        # 检查操作系统
        if os.name == 'nt':  # Windows系统
            # 微软雅黑是Windows常见的中文字体
            font_path = 'C:/Windows/Fonts/msyh.ttc'  # 微软雅黑
            if not os.path.exists(font_path):
                font_path = 'C:/Windows/Fonts/simhei.ttf'  # 尝试使用黑体
                
            if os.path.exists(font_path):
                font_properties = matplotlib.font_manager.FontProperties(fname=font_path)
                plt.rcParams['font.family'] = font_properties.get_name()
            else:
                logger.warning("找不到中文字体文件，可能无法正确显示中文")
                
        elif os.name == 'posix':  # Linux/Mac系统
            # 尝试常见的中文字体
            try:
                plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'Noto Sans CJK SC', 
                                                 'WenQuanYi Micro Hei', 'SimHei', 
                                                 'Microsoft YaHei', 'PingFang SC']
                plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
            except:
                logger.warning("配置中文字体失败，可能无法正确显示中文")
        
        # 通用配置，适用于所有系统
        matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS'] + \
                                               matplotlib.rcParams['font.sans-serif']
        matplotlib.rcParams['axes.unicode_minus'] = False
    except Exception as e:
        logger.warning(f"设置中文字体时出错: {e}")
        logger.warning("可能无法正确显示中文字符")

def visualize_graph(graph: NetworkXGraph, topic: str, output_file: str = None):
    """
    可视化NetworkX图并保存为文件或显示
    
    参数:
        graph: 要可视化的NetworkXGraph对象
        topic: 图的主题（用于标题）
        output_file: 保存图像的文件路径，如果为None则显示图像
    """
    try:
        # 设置中文字体支持
        setup_chinese_font()
        
        # 创建一个NetworkX DiGraph用于可视化
        G = nx.DiGraph()
        
        # 添加节点
        for node in graph.get_nodes():
            G.add_node(node["id"], title=node.get("title", node["id"]), 
                      type=node.get("type", "concept"))
        
        # 添加边
        for edge in graph.get_edges():
            G.add_edge(
                edge["source"], 
                edge["target"], 
                title=edge.get("relationship", "relates_to")
            )
        
        # 方法1: 使用matplotlib绘制
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G)  # 定位布局
        
        # 设置节点颜色基于类型
        node_colors = []
        for node, attrs in G.nodes(data=True):
            if attrs.get("type") == "core":
                node_colors.append("red")
            elif attrs.get("type") == "prerequisite":
                node_colors.append("green")
            elif attrs.get("type") == "component":
                node_colors.append("blue")
            else:
                node_colors.append("skyblue")
        
        # 绘制节点
        nx.draw_networkx_nodes(G, pos, node_size=700, node_color=node_colors)
        
        # 绘制边
        nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.7, arrows=True)
        
        # 绘制节点标签
        nx.draw_networkx_labels(G, pos, font_size=10, 
                                labels={n: G.nodes[n].get('title', n) for n in G.nodes()})
        
        # 绘制边标签
        edge_labels = {(u, v): d.get('title', '') for u, v, d in G.edges(data=True)}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
        
        plt.title(f"知识图谱: {topic}")
        plt.axis('off')  # 关闭坐标轴
        
        # 保存或显示
        if output_file:
            plt.savefig(output_file)
            logger.info(f"图形已保存为 {output_file}")
        else:
            plt.show()
            
        # 方法2: 使用Pyvis创建交互式可视化（HTML）
        # try:
        #     # 创建Pyvis网络
        #     net = Network(height="750px", width="100%", directed=True, notebook=False)
            
        #     # 从NetworkX图中加载数据
        #     net.from_nx(G)
            
        #     # 确保HTML文件支持中文显示
        #     net.set_template("""
        #     <!DOCTYPE html>
        #     <html>
        #     <head>
        #         <meta charset="utf-8">
        #         <title>知识图谱可视化</title>
        #         <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/vis-network@9.1.0/dist/vis-network.min.js"></script>
        #         <link href="https://cdn.jsdelivr.net/npm/vis-network@9.1.0/dist/dist/vis-network.min.css" rel="stylesheet" type="text/css" />
        #         <style type="text/css">
        #             #mynetwork {
        #                 width: 100%;
        #                 height: 750px;
        #                 background-color: #ffffff;
        #                 border: 1px solid lightgray;
        #                 position: relative;
        #             }
        #         </style>
        #     </head>
        #     <body>
        #         <div id="mynetwork"></div>
        #         <script type="text/javascript">
        #             function draw() {
        #                 var nodes = new vis.DataSet({{ nodes | safe }});
        #                 var edges = new vis.DataSet({{ edges | safe }});
        #                 var container = document.getElementById("mynetwork");
        #                 var data = {
        #                     nodes: nodes,
        #                     edges: edges
        #                 };
        #                 var options = {{ options | safe }};
        #                 var network = new vis.Network(container, data, options);
        #             }
        #             window.addEventListener("load", () => {
        #                 draw();
        #             });
        #         </script>
        #     </body>
        #     </html>
        #     """)
            
        #     # 设置物理布局选项
        #     net.set_options('''
        #     {
        #       "physics": {
        #         "forceAtlas2Based": {
        #           "gravitationalConstant": -50,
        #           "centralGravity": 0.01,
        #           "springLength": 100,
        #           "springConstant": 0.08
        #         },
        #         "solver": "forceAtlas2Based",
        #         "stabilization": {
        #           "iterations": 100
        #         }
        #       }
        #     }
        #     ''')
            
        #     # 保存为HTML文件
        #     html_file = output_file.replace('.png', '.html') if output_file else f"知识图谱_{topic.replace(' ', '_')}.html"
        #     net.save_graph(html_file)
        #     logger.info(f"交互式图形已保存为 {html_file}")
        # except ImportError:
        #     logger.info("要使用交互式可视化，请安装pyvis: pip install pyvis")
            
    except Exception as e:
        logger.error(f"可视化图形时出错: {e}")
