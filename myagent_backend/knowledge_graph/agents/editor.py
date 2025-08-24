"""
Editor agent for the Knowledge Graph Generator.
"""

import json
import logging
from typing import Dict, List, Any
from collections import deque

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from ..models import PipelineState
from ..prompts import EDITOR_SYSTEM_PROMPT, EDITOR_HUMAN_PROMPT
from ..config import get_llm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def editor_agent(state: PipelineState) -> Dict:
    """
    Editor agent that reviews and refines node content.
    It processes nodes in the order determined by get_next_nodes_to_process.
    """
    if not state.graph:
        logger.error("Missing graph data for editor agent")
        return {}

    topic = state.topic
    edges = state.graph.get_edges()
    
    # 使用get_next_nodes_to_process获取需要编辑的节点ID
    nodes_to_process_ids = state.get_next_nodes_to_process("editing")
    
    # 如果没有节点需要编辑，标记为完成状态并返回
    if not nodes_to_process_ids:
        logger.info("No new nodes to edit. Editor phase complete.")
        state.current_stage = "editor_finished"
        return {
            "graph": state.graph,
            "processed_nodes": state.processed_nodes,
            "current_stage": state.current_stage
        }
    
    logger.info(f"This round will edit {len(nodes_to_process_ids)} nodes")
    
    # Process each node in the list
    for node_id in nodes_to_process_ids:
        current_node = state.graph.get_node(node_id)
        if not current_node or current_node.get("status") != "written":
            logger.info(f"Skipping node {node_id} as it's not ready for editing.")
            continue

        logger.info(f"Editing node: {node_id} - {current_node.get('title', '')}")

        # 1. Gather context for the current node
        node_content = current_node.get("draft_text", "")
        node_relationships = []
        adjacent_nodes_summary = []
        
        # Find neighbors and build context
        neighbors = []
        neighbor_ids = set()

        for edge in edges:
            if edge["source"] == node_id and edge["target"] not in neighbor_ids:
                neighbor_id = edge["target"]
                relationship = edge.get("relationship", "relates_to")
                target_node = state.graph.get_node(neighbor_id)
                if target_node:
                    target_title = target_node.get("title", neighbor_id)
                    node_relationships.append(f"'{current_node.get('title', node_id)}' → {relationship} → '{target_title}'")
                    neighbors.append(target_node)
                    neighbor_ids.add(neighbor_id)

            elif edge["target"] == node_id and edge["source"] not in neighbor_ids:
                neighbor_id = edge["source"]
                relationship = edge.get("relationship", "relates_to")
                source_node = state.graph.get_node(neighbor_id)
                if source_node:
                    source_title = source_node.get("title", neighbor_id)
                    node_relationships.append(f"'{source_title}' → {relationship} → '{current_node.get('title', node_id)}'")
                    neighbors.append(source_node)
                    neighbor_ids.add(neighbor_id)

        for neighbor in neighbors:
            summary = neighbor.get("node_summary")
            if summary:
                adjacent_nodes_summary.append(f"- {neighbor.get('title', neighbor['title'])}: {summary}")

        # 2. Create prompt and invoke LLM
        messages = [
            SystemMessage(content=EDITOR_SYSTEM_PROMPT),
            HumanMessage(content=EDITOR_HUMAN_PROMPT.format(
                topic=topic,
                node_id=node_id,
                node_title=current_node.get('title', node_id),
                node_content=node_content,
                node_relationships="\n".join(node_relationships),
                adjacent_nodes_summary="\n".join(adjacent_nodes_summary)
            ))
        ]

        try:
            llm = get_llm()
            response = llm.invoke(messages)
            response_text = response.content
            
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            
            data = json.loads(json_str)
            final_text = data.get("optimized_content", node_content)

            # 3. Update state with edited content
            state.update_node_content(
                node_id=node_id,
                content={"final_text": final_text, "status": "edited"},
                stage="edited"
            )
            logger.info(f"Successfully edited and updated node {node_id}.")

        except Exception as e:
            logger.error(f"Error processing node {node_id} in editor agent: {e}")
            # Fallback: mark as edited but use original draft text
            state.update_node_content(
                node_id=node_id,
                content={"final_text": node_content, "status": "edited"},
                stage="edited"
            )

    # Check if there are any more nodes to edit
    remaining_nodes = state.get_next_nodes_to_process("editing")
    if not remaining_nodes:
        # If no remaining nodes, mark as editing finished
        state.current_stage = "editor_finished"
        logger.info("All nodes have been edited")
    else:
        # If there are still unedited nodes, maintain current state
        state.current_stage = "editing"
        logger.info(f"There are still {len(remaining_nodes)} nodes waiting to be edited")

    return {
        "graph": state.graph,
        "processed_nodes": state.processed_nodes,
        "current_stage": state.current_stage
    }
