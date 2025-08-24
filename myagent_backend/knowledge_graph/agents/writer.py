"""
Writer agent for the Knowledge Graph Generator.
"""

import json
import logging
import os
from typing import Dict, List, Any, Tuple, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from ..models import PipelineState
from ..prompts import WRITER_SYSTEM_PROMPT, WRITER_HUMAN_PROMPT
from .models import ResearchedData, WrittenContent
from ..config import get_llm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def write_node_content(
    node_id: str,
    node_title: str,
    topic: str,
    research_data: ResearchedData
) -> Tuple[str, WrittenContent]:
    """Write content for a single node and return it."""
    logger.info(f"Writing content for node: {node_title}")
    
    # Format the research data as a string
    research_data_str = (
        f"Definition: {research_data.definition}\n\n"
        f"Key Points:\n" + "\n".join([f"- {point}" for point in research_data.key_points]) + "\n\n"
        f"Examples:\n" + "\n".join([f"- {example}" for example in research_data.examples]) + "\n\n"
        f"Sources:\n" + "\n".join([f"- {source.title}: {source.url}" for source in research_data.sources])
    )
    
    # Create prompt
    messages = [
        SystemMessage(content=WRITER_SYSTEM_PROMPT),
        HumanMessage(content=WRITER_HUMAN_PROMPT.format(
            topic=topic,
            node_title=node_title,
            research_data=research_data_str
        ))
    ]
    
    try:
        # Execute with LLM
        llm = get_llm()
        response = llm.invoke(messages)
        response_text = response.content
        
        # Extract JSON from the response
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].strip()
        else:
            json_str = response_text.strip()
            
        data = json.loads(json_str)
        
        # Create WrittenContent object
        written_content = WrittenContent(
            draft_text=data.get("draft_text", ""),
            node_summary=data.get("node_summary", ""),
        )
        
        return node_id, written_content
        
    except Exception as e:
        logger.error(f"Error writing content for node {node_title}: {e}")
        # Return minimal content
        return node_id, WrittenContent(
            draft_text=f"Content for {node_title} could not be generated.",
            node_summary=f"Summary for {node_title} could not be generated.",
        )

def writer_agent(state: PipelineState) -> Dict:
    """Writer agent that creates content drafts for all nodes."""
    if not state.graph:
        logger.error("Missing required data for writer agent")
        return {}
    
    topic = state.topic
    
    # 使用get_next_nodes_to_process获取需要撰写的节点ID
    nodes_to_process_ids = state.get_next_nodes_to_process("writing")
    
    # 如果没有节点需要撰写，标记为完成状态并返回
    if not nodes_to_process_ids:
        logger.info("No new nodes to write content for. Writing phase complete.")
        state.current_stage = "write_finished"
        return {
            "graph": state.graph,
            "processed_nodes": state.processed_nodes,
            "current_stage": state.current_stage
        }
    
    logger.info(f"This round will write content for {len(nodes_to_process_ids)} nodes")
    
    # Get researched node data
    researched_nodes = {}
    for node_id in nodes_to_process_ids:
        node_data = state.graph.get_node(node_id)
        if node_data:
            researched_nodes[node_id] = ResearchedData(
                definition=node_data.get("definition", ""),
                key_points=node_data.get("key_points", []),
                examples=node_data.get("examples", []),
                sources=node_data.get("sources", [])
            )
    
    # Create writing tasks for each node
    results = []
    for node_id in nodes_to_process_ids:
        # Skip if we don't have research data for this node
        if node_id not in researched_nodes:
            logger.warning(f"Skipping node {node_id} as it has no research data")
            continue
            
        # Get node info for title
        node = state.graph.get_node(node_id)
        node_title = node.get("title", node_id)
        
        # Write content for this node
        result = write_node_content(
            node_id=node_id,
            node_title=node_title,
            topic=topic,
            research_data=researched_nodes[node_id]
        )
        results.append(result)
    
    # Get all nodes from the graph for later check
    nodes = state.graph.get_nodes()
    
    # Update the state with written content
    for node_id, written_content in results:
        # Update the node with the written content
        state.update_node_content(
            node_id=node_id,
            content={
                "draft_text": written_content.draft_text,
                "node_summary": written_content.node_summary,
                "status": "written"
            },
            stage="written"
        )
    
    # Check if there are any more nodes to write
    remaining_nodes = state.get_next_nodes_to_process("writing")
    if not remaining_nodes:
        # If no remaining nodes, mark as writing finished
        state.current_stage = "write_finished"
        logger.info("All nodes have been written")
    else:
        # If there are still unwritten nodes, maintain current state
        state.current_stage = "writing"
        logger.info(f"There are still {len(remaining_nodes)} nodes waiting to be written")
    
    return {
        "graph": state.graph,
        "processed_nodes": state.processed_nodes,
        "current_stage": state.current_stage
    }
