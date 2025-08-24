"""
知识图谱搜索工具模块。
"""

from typing import Dict, List, Any
from langchain.tools import Tool
from langchain_core.tools import BaseTool
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from tavily import TavilyClient

    import os
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    # 获取API密钥
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    
    tavily_available = bool(TAVILY_API_KEY)
    if tavily_available:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
    else:
        logger.warning("未设置TAVILY_API_KEY环境变量，Tavily搜索功能将不可用")
        
except ImportError:
    logger.warning("未安装Tavily客户端库，Tavily搜索功能将不可用")
    tavily_available = False

# 思考工具 - 用于支持ReAct思考过程
def think_tool(query: str) -> str:
    """一个用于分析信息和规划后续行动的思考工具。不执行外部搜索，仅帮助模型组织思路。"""
    return f"思考过程记录: {query}"

# Web搜索工具 - 使用Tavily API
def search_web(query: str) -> str:
    """使用Tavily搜索API在网络上查询信息。"""
    if not tavily_available:
        return "搜索功能不可用 - 未配置Tavily API密钥"
    
    try:
        # 执行搜索
        search_result = tavily_client.search(
            query=query,
            search_depth="advanced",
            include_domains=["wikipedia.org", "britannica.com", "scholar.google.com", 
                            "sciencedirect.com", "nature.com", "nih.gov"],
            include_answer=True,
            include_raw_content=False,
            max_results=5
        )
        
        # 格式化结果
        formatted_result = "搜索结果:\n\n"
        
        # 添加Tavily生成的答案（如果有）
        if search_result.get("answer"):
            formatted_result += f"Tavily答案: {search_result['answer']}\n\n"
            
        # 添加搜索结果
        for i, result in enumerate(search_result.get("results", []), 1):
            formatted_result += f"{i}. {result.get('title', '无标题')}\n"
            formatted_result += f"   链接: {result.get('url', '#')}\n"
            formatted_result += f"   内容: {result.get('content', '无内容')[:500]}...\n\n"
            
        return formatted_result
    except Exception as e:
        logger.error(f"搜索时出现意外错误: {e}")
        return f"搜索时出现意外错误: {str(e)}"

# 节点详情查询工具 - 在知识图谱中查询特定节点
def search_node_details(node_title: str) -> str:
    """在相关知识库中查询特定节点的详细信息。"""
    # 这是一个示例，实际应该连接到某种知识库
    return f"节点 '{node_title}' 的详细信息尚未实现，这是一个占位符功能。"

# 定义LangChain工具
search_tools = [
    Tool(
        name="think_tool",
        func=think_tool,
        description="用于思考和分析已有信息、规划下一步研究的工具。使用这个工具来整理你的思路，而不是获取新信息。"
    ),
    Tool(
        name="search_web",
        func=search_web,
        description="在互联网上搜索最新、权威的信息。提供清晰具体的搜索查询以获得最佳结果。"
    ),
    Tool(
        name="search_node_details",
        func=search_node_details,
        description="查询知识图谱中特定节点的详细背景信息。输入节点标题作为参数。"
    )
]
