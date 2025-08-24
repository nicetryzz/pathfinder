"""
Data models for agents in the Knowledge Graph generation workflow.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class Source(BaseModel):
    """A source of information."""
    title: str
    url: str

class ResearchedData(BaseModel):
    """Data structure for research results."""
    definition: str
    key_points: List[str]
    examples: List[str]
    sources: List[Source] = Field(default_factory=list)

class WrittenContent(BaseModel):
    """Data structure for written content."""
    draft_text: str
    node_summary: str = ""  # 节点内容的简明概要
    linked_concepts: List[str] = Field(default_factory=list)

class GraphData(BaseModel):
    """Complete knowledge graph data structure."""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None

class GenerateMapRequest(BaseModel):
    """Request format for generating a knowledge map."""
    topic: str
