"""
配置文件，用于设置知识图谱生成器的各种参数和工具。
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Literal, Union
from dotenv import load_dotenv
from google.generativeai import GenerativeModel
from google.generativeai import configure as gconfigure
from langchain_core.language_models.base import BaseLanguageModel
from langchain_google_genai import ChatGoogleGenerativeAI

import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 获取环境变量
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")

# GPT-Load配置
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL")
USE_GEMINI_POOL = os.getenv("USE_GEMINI_POOL", "false").lower() == "true"
GEMINI_CUSTOM_HEADERS = os.getenv("GEMINI_CUSTOM_HEADERS", "{}")

# 解析自定义请求头
try:
    CUSTOM_HEADERS = json.loads(GEMINI_CUSTOM_HEADERS)
except json.JSONDecodeError:
    logger.warning("自定义请求头JSON解析错误，使用空字典")
    CUSTOM_HEADERS = {}

# LLM模型配置
def get_llm(model: Optional[str] = None) -> BaseLanguageModel:
    """
    获取LLM实例
    
    参数:
        model: 模型名称，如果为None则使用默认模型
        
    返回:
        LLM实例
    """
    model_name = model or DEFAULT_MODEL
    
    # 创建LLM实例
    if model_name.startswith("gemini"):
        # 检查是否使用GPT-Load密钥池
        if  GEMINI_BASE_URL:
            logger.info(f"使用GPT-Load密钥池: {GEMINI_BASE_URL}")
            
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key="dummy_key",
                base_url=GEMINI_BASE_URL,
                additional_headers={"Authorization" : "Bearer sk-123456"}
                # additional_headers=CUSTOM_HEADERS
            )
        else:
            # 使用常规API密钥
            if not GOOGLE_API_KEY:
                raise ValueError("未设置GEMINI_API_KEY环境变量")
                
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=GOOGLE_API_KEY,
            )
    else:
        raise ValueError(f"不支持的模型: {model_name}")
    
    return llm

# 可配置参数
DEFAULT_CONFIG = {
    "max_nodes": 10,              # 知识图谱中的最大节点数量
    "max_edges_per_node": 5,      # 每个节点的最大边数
    "log_level": "INFO",          # 日志级别
    "visualization": {
        "enabled": True,          # 是否启用可视化
        "format": "png",         # 可视化格式，支持"html"和"png"
    }
}

# 获取配置
def get_config() -> Dict[str, Any]:
    """
    获取配置
    
    返回:
        配置字典
    """
    return DEFAULT_CONFIG
