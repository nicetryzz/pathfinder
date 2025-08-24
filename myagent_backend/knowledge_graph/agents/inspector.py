"""
Inspector agent for the Knowledge Graph Generator.
"""

import json
import logging
import uuid
from typing import Dict, Any, List

from langchain_core.messages import HumanMessage, SystemMessage

from ..models import PipelineState
from ..prompts import INSPECTOR_SYSTEM_PROMPT, INSPECTOR_HUMAN_PROMPT
from ..config import get_llm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def apply_suggestions(state: PipelineState, report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply the suggested changes from the inspector's report to the knowledge graph.
    Returns a summary of changes made.
    """
    results = {
        "added_nodes": [],
        "removed_nodes": [],
        "added_edges": [],
        "removed_edges": [],
        "errors": []
    }
    
    for suggestion in report.get("structural_suggestions",[]):
        if suggestion['suggestion_type'] == 'ADD_NODE':
            try:
                # Generate a unique node ID based on the title
                suggested_node = suggestion['details']['suggested_node']
                title = suggested_node.get("title")
                node_id = suggested_node.get("node_id")
                if not title:
                    continue
                
                # Add the new node to the graph
                state.add_node(
                    node_id=suggested_node.get("node_id", ""),
                    title=suggested_node.get("title", ""),
                    type=suggested_node.get("type", ""),
                    description=suggested_node.get("description", ""),
                    status="created"  # Mark as created but not yet researched
                )
                
                results["added_nodes"].append(suggested_node)

                logger.info(f"Added new node: {title} (ID: {node_id}")
                
                connection = suggestion['details']['connect_to']

                if connection:
                    source_id = connection.get("source_id")
                    target_id = connection.get("target_id")
                    relationship = connection.get("relationship", "relates_to")
                
                    if not source_id or not target_id:
                        continue
                    
                    # Check if both nodes exist
                    source_node = state.graph.get_node(source_id)
                    target_node = state.graph.get_node(target_id)
                
                    if not source_node or not target_node:
                        logger.warning(f"Cannot add edge: one or both nodes don't exist ({source_id} → {target_id})")
                        results["errors"].append(f"Cannot add edge: missing nodes {source_id} or {target_id}")
                        continue
                    
                    # Add the new edge
                    state.add_edge(source_id, target_id, relationship=relationship)
                    
                    results["added_edges"].append({
                        "source_id": source_id,
                        "source_title": source_node.get("title", source_id),
                        "target_id": target_id,
                        "target_title": target_node.get("title", target_id),
                        "relationship": relationship
                    })
                    
                    logger.info(f"Added new edge: {source_node.get('title', source_id)} → {relationship} → {target_node.get('title', target_id)}")
            except Exception as e:
                logger.error(f"Error adding suggested node {suggestion.get('title')}: {e}")
                results["errors"].append(f"Failed to add node {suggestion.get('title')}: {e}")
        elif suggestion['suggestion_type'] == 'DEEPEN_NODE':
            # 这是一个更复杂的操作，因为它涉及批量添加节点和边
            try:
                details = suggestion['details']
                parent_node_id = details.get("target_node_id")
                parent_node = state.graph.get_node(parent_node_id)

                if not parent_node:
                    error_msg = f"Cannot deepen node: Parent node with ID '{parent_node_id}' not found."
                    logger.warning(error_msg)
                    results["errors"].append(error_msg)
                    continue

                # 遍历建议添加的每一个子节点
                for sub_node_data in details.get("suggested_sub_components", []):
                    sub_node_id = sub_node_data.get("node_id")
                    sub_node_title = sub_node_data.get("title")

                    if not sub_node_id or not sub_node_title:
                        results["errors"].append(f"Skipping sub-node for {parent_node_id} due to missing title or node_id.")
                        continue

                    # 1. 添加子节点
                    state.add_node(
                        node_id=sub_node_id,
                        title=sub_node_title,
                        type="sub_component",  # 类型是固定的
                        description=sub_node_data.get("description", ""),
                        status="created"
                    )
                    results["added_nodes"].append(sub_node_data)
                    logger.info(f"Added new sub-node '{sub_node_title}' (ID: {sub_node_id}) under '{parent_node.get('title')}'")

                    # 2. 添加从父节点到子节点的边
                    state.add_edge(parent_node_id, sub_node_id, relationship="is_component_of")
                    results["added_edges"].append({
                        "source_id": parent_node_id, "source_title": parent_node.get("title", parent_node_id),
                        "target_id": sub_node_id, "target_title": sub_node_title,
                        "relationship": "is_component_of"
                    })
                    logger.info(f"Added new edge: {parent_node.get('title')} → is_component_of → {sub_node_title}")

            except Exception as e:
                error_msg = f"Error deepening node {details.get('target_node_id')}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        elif suggestion['suggestion_type'] == 'DELETE_NODE':
            suggested_node = suggestion['details']
            node_id = suggested_node.get("node_id")
            if not node_id:
                continue
            node = state.graph.get_node(node_id)
            if node:
                # 彻底删除节点及其所有相关边
                state.graph.delete_node(node_id)
                results["removed_nodes"].append({
                    "id": node_id,
                    "title": node.get("title", node_id),
                    "reason": suggestion.get("reason", "No reason provided")
                })
                logger.info(f"Deleted node and its edges: {node.get('title', node_id)} (ID: {node_id})")

    return results

def inspector_agent(state: PipelineState) -> Dict[str, Any]:
    """
    Inspector agent that performs a global review of the knowledge graph.
    It analyzes the overall structure, coherence, and consistency,
    and makes suggestions for improvement.
    """
    logger.info("--- Global Inspector Agent: Starting Review ---")
    if not state.graph:
        logger.error("Inspector Agent: Missing graph data.")
        return {}

    state.current_stage = "inspecting"

    topic = state.topic
    nodes = state.graph.get_nodes()
    edges = state.graph.get_edges()

    # Prepare nodes information (ID, title, summary) for the prompt
    nodes_info = []
    for node in nodes:
        node_id = node["id"]
        title = node.get("title", "No Title")
        summary = node.get("node_summary", "No summary available.")
        node_type = node.get("type", "concept")
        nodes_info.append(f"- Node ID: {node_id}\n  Title: {title}\n  Type: {node_type}\n  Summary: {summary}")
    nodes_str = "\n\n".join(nodes_info)

    # Prepare edges information for the prompt
    edges_info = []
    for edge in edges:
        source_id = edge["source"]
        target_id = edge["target"]
        relationship = edge.get("relationship", "related_to")
        source_node = state.graph.get_node(source_id)
        target_node = state.graph.get_node(target_id)
        source_title = source_node.get("title", source_id) if source_node else source_id
        target_title = target_node.get("title", target_id) if target_node else target_id
        edges_info.append(f"- '{source_title}' ({source_id}) → {relationship} → '{target_title}' ({target_id})")
    edges_str = "\n".join(edges_info)

    # Prepare applied changes for the prompt
    applied_changes = []
    inspection_report = getattr(state, "inspection_report", None)
    if inspection_report and "changes_applied" in inspection_report:
        changes = inspection_report["changes_applied"]
        for node in changes.get("added_nodes", []):
            applied_changes.append(f"已添加节点: {node.get('title', node.get('node_id'))}")
        for node in changes.get("removed_nodes", []):
            applied_changes.append(f"已删除节点: {node.get('title', node.get('id'))}")
    applied_changes_str = "\n".join(applied_changes) if applied_changes else "无"

    # Create prompt for the LLM
    messages = [
        SystemMessage(content=INSPECTOR_SYSTEM_PROMPT),
        HumanMessage(content=INSPECTOR_HUMAN_PROMPT.format(
            topic=topic,
            iter=state.inspection_iter,
            edges=edges_str,
            nodes=nodes_str,
            applied_changes=applied_changes_str
        ))
    ]

    try:
        llm = get_llm(model='gemini-1.5-pro')
        response = llm.invoke(messages)
        response_text = response.content
        
        logger.debug(f"Inspector LLM raw response: {response_text}")

        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        else:
            json_str = response_text.strip()
            
        report = json.loads(json_str)
        
        # Count suggestions
        structural_suggestions = len(report.get("structural_suggestions", []))
        
        logger.info(f"Inspector generated: {structural_suggestions} structural suggestions")
        
        # Apply the suggested changes to the graph
        changes = apply_suggestions(state, report)
        
        # Add changes to the report
        report["changes_applied"] = changes
        
        # 多轮 inspection，inspection_report 变为列表，追加本轮 report
        if not hasattr(state, "inspection_report") or state.inspection_report is None:
            state.inspection_report = []
        if not isinstance(state.inspection_report, list):
            # 兼容旧格式，转为列表
            state.inspection_report = [state.inspection_report]
        state.inspection_report.append(report)
        
        # Determine next stage based on whether new nodes were added
        if changes["added_nodes"]:
            # If new nodes were added, they need to be researched
            logger.info(f"Added {len(changes['added_nodes'])} new nodes, returning to research stage")
            state.current_stage = "researching"
        else:
            # If no new nodes, inspection is complete
            logger.info("Inspection completed with no new nodes added")
            state.current_stage = "inspection_finished"

    except Exception as e:
        logger.error(f"Inspector Agent: Error during review - {e}")
        state.current_stage = "inspector_error"
        state.inspection_report = {"error": str(e)}

    result = {
        "inspection_report": state.inspection_report,
        "current_stage": state.current_stage
    }
    
    # 如果需要继续研究，添加完整的图谱数据和处理节点列表到返回值
    if state.current_stage == "researching":
        result["graph"] = state.graph
        result["processed_nodes"] = state.processed_nodes
        
    return result
