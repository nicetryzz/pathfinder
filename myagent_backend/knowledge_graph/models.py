"""
Data models for the Knowledge Graph Generator using NetworkX.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import networkx as nx
import json

# --- NetworkX Graph Model ---
class NetworkXGraph(BaseModel):
    """包装NetworkX图的Pydantic模型，用于知识图谱表示"""
    
    graph: Dict = Field(default_factory=dict)  # 图的元数据
    
    def __init__(self, **data):
        super().__init__(**data)
        self._nx_graph = nx.DiGraph()  # 使用有向图表示知识图谱
    

    def add_node(self, node_id: str, **attrs):
        """添加一个节点到图中"""
        self._nx_graph.add_node(node_id, **attrs)

    def add_edge(self, source: str, target: str, **attrs):
        """添加一条边到图中"""
        self._nx_graph.add_edge(source, target, **attrs)

    def delete_node(self, node_id: str):
        """彻底删除节点及其所有相关边"""
        if node_id in self._nx_graph:
            self._nx_graph.remove_node(node_id)
    
    def get_node(self, node_id: str) -> Dict:
        """获取节点属性"""
        if node_id in self._nx_graph.nodes:
            return dict(self._nx_graph.nodes[node_id])
        return {}
    
    def get_nodes(self) -> List[Dict]:
        """获取所有节点及其属性"""
        return [{"id": n, **dict(attr)} for n, attr in self._nx_graph.nodes(data=True)]
    
    def get_edges(self) -> List[Dict]:
        """获取所有边及其属性"""
        return [{"source": u, "target": v, **dict(attr)} for u, v, attr in self._nx_graph.edges(data=True)]
    
    def to_dict(self) -> Dict:
        """将图转换为字典表示"""
        return {
            "nodes": self.get_nodes(),
            "edges": self.get_edges(),
            "metadata": self.graph
        }
    
    def to_json(self) -> str:
        """将图转换为JSON字符串"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict) -> "NetworkXGraph":
        """从字典创建图"""
        graph = cls()
        # 添加元数据
        graph.graph = data.get("metadata", {})
        
        # 添加节点
        for node in data.get("nodes", []):
            node_id = node.pop("id")
            graph.add_node(node_id, **node)
        
        # 添加边
        for edge in data.get("edges", []):
            source = edge.pop("source")
            target = edge.pop("target")
            graph.add_edge(source, target, **edge)
        
        return graph
    
    # NetworkX分析方法
    def get_central_nodes(self, top_n: int = 3) -> List[str]:
        """获取中心度最高的节点"""
        centrality = nx.betweenness_centrality(self._nx_graph)
        return sorted(centrality, key=centrality.get, reverse=True)[:top_n]
    
    def get_leaf_nodes(self) -> List[str]:
        """获取叶子节点（出度为0的节点）"""
        return [n for n, d in self._nx_graph.out_degree() if d == 0]
    
    def get_root_nodes(self) -> List[str]:
        """获取根节点（入度为0的节点）"""
        return [n for n, d in self._nx_graph.in_degree() if d == 0]



# --- State for LangGraph workflow ---
class PipelineState(BaseModel):
    """知识图谱生成流程的状态对象"""
    topic: str
    graph: Optional[NetworkXGraph] = None  # 整个流程使用一个统一的图

    # 处理状态
    current_stage: str = "planning"
    processed_nodes: Dict[str, List[str]] = Field(default_factory=lambda: {
        "researched": [],  # 已完成研究的节点
        "written": [],     # 已完成撰写的节点
        "edited": []       # 已完成编辑的节点
    })
    
    # Inspector报告
    inspection_report: Optional[Dict[str, Any]] = None

    inspection_iter: int = 0
    
    class Config:
        arbitrary_types_allowed = True
    
    def save_state(self, filepath: str):
        """保存当前状态到文件
        
        参数:
            filepath: 保存状态的JSON文件路径
        """
        state_data = {
            "topic": self.topic,
            "current_stage": self.current_stage,
            "processed_nodes": self.processed_nodes,
            "inspection_report": self.inspection_report
        }
        
        # 序列化图数据（如果存在）
        if self.graph:
            state_data["graph"] = self.graph.to_dict()
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_state(cls,
     filepath: str) -> "PipelineState":
        """从文件加载状态
        
        参数:
            filepath: 状态JSON文件路径
            
        返回:
            加载的PipelineState对象
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
        
        # 创建状态对象
        state = cls(
            topic=state_data["topic"],
            current_stage=state_data.get("current_stage", "planning"),
            processed_nodes=state_data.get("processed_nodes", {"researched": [], "written": [], "edited": []}),
            inspection_report=state_data.get("inspection_report")
        )
        
        # 如果有图数据，则加载
        if "graph" in state_data:
            state.graph = NetworkXGraph.from_dict(state_data["graph"])
        
        return state
    
    def initialize_graph(self, graph: Optional[NetworkXGraph] = None):
        """初始化图结构"""
        if graph:
            self.graph = graph
        elif not self.graph:
            self.graph = NetworkXGraph()
    
    def update_node_content(self, node_id: str, content: Dict, stage: Optional[str] = None):
        """更新节点内容
        
        参数:
            node_id: 要更新的节点ID
            content: 要添加的内容属性
            stage: 当前处理阶段，如果提供则会更新节点状态和处理列表
        """
        if not self.graph:
            self.initialize_graph()
        
        # 获取现有属性并更新
        attrs = self.graph.get_node(node_id)
        attrs.update(content)
        
        # 如果提供了处理阶段，更新节点状态和处理列表
        if stage:
            attrs["status"] = stage
            if stage == "researched" and node_id not in self.processed_nodes["researched"]:
                self.processed_nodes["researched"].append(node_id)
            elif stage == "written" and node_id not in self.processed_nodes["written"]:
                self.processed_nodes["written"].append(node_id)
            elif stage == "edited" and node_id not in self.processed_nodes["edited"]:
                self.processed_nodes["edited"].append(node_id)
        
        # 更新节点
        self.graph.add_node(node_id, **attrs)
    
    def add_node(self, node_id: str, **attrs):
        """添加新节点到图中"""
        if not self.graph:
            self.initialize_graph()
        
        self.graph.add_node(node_id, **attrs)
    
    def add_edge(self, source: str, target: str, **attrs):
        """添加新边到图中"""
        if not self.graph:
            self.initialize_graph()
        
        self.graph.add_edge(source, target, **attrs)
    
    def get_next_nodes_to_process(self, stage: str, limit: int = -1) -> List[str]:
        """获取下一批要处理的节点
        
        参数:
            stage: 处理阶段 (researching, writing, editing)
            limit: 返回的最大节点数量
            
        返回:
            待处理节点ID列表
        """
        if not self.graph:
            return []
        
        nodes = self.graph.get_nodes()
        
        if stage == "researching":
            # 找出尚未研究的节点
            candidates = [n["id"] for n in nodes 
                         if "status" not in n or n["status"] == "created"]
            
        elif stage == "writing":
            # 找出已研究但尚未撰写的节点
            candidates = [n["id"] for n in nodes 
                         if n["id"] in self.processed_nodes["researched"] 
                         and n["id"] not in self.processed_nodes["written"]]
            
        elif stage == "editing":
            # 找出已撰写但尚未编辑的节点
            candidates = [n["id"] for n in nodes 
                         if n["id"] in self.processed_nodes["written"] 
                         and n["id"] not in self.processed_nodes["edited"]]
            
        else:
            return []
        
        # 返回限制数量的节点
        if limit == -1:
            return candidates
        return candidates[:limit]
    
    def get_graph_data(self) -> "GraphData":
        """获取简化的图数据输出"""
        if not self.graph:
            self.initialize_graph()
        
        data = self.graph.to_dict()
        return GraphData(**data)
    
    def is_complete(self) -> bool:
        """检查知识图谱是否已完成全部处理
        
        返回:
            如果所有节点都已完成编辑，则返回True
        """
        if not self.graph:
            return False
        
        nodes = self.graph.get_nodes()
        node_ids = [n["id"] for n in nodes]
        
        # 检查是否所有节点都已完成编辑
        return all(node_id in self.processed_nodes["edited"] for node_id in node_ids)
