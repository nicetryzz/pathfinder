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

        elif suggestion['suggestion_type'] == 'MERGE_NODES':
            details = suggestion['details']
            nodes_to_merge_ids = details.get("nodes_to_merge", [])
            new_node_data = details.get("new_node")

            if not nodes_to_merge_ids or not new_node_data:
                results["errors"].append("MERGE_NODES suggestion is missing nodes_to_merge or new_node details.")
                continue
            
            # 1. 创建合并后的新节点
            new_node_id = new_node_data['node_id']
            state.add_node(
                node_id=new_node_id,
                title=new_node_data['title'],
                type=new_node_data['type'],
                description=new_node_data['description'],
                status="created"
            )
            results["added_nodes"].append(new_node_data)
            logger.info(f"MERGE: Created new node '{new_node_data['title']}' (ID: {new_node_id})")

            # 2. 重新连接边
            # 使用集合来存储新的边关系，避免重复添加
            new_edges_to_create = set()
            
            for old_node_id in nodes_to_merge_ids:
                # 查找所有与旧节点相关的边
                for edge in state.graph.get_edges():
                    # 如果是入边 (Incoming edge)
                    if edge['target'] == old_node_id:
                        # 将入边的目标重定向到新节点
                        new_edges_to_create.add((edge['source'], new_node_id, edge.get('relationship', 'related_to')))
                    
                    # 如果是出边 (Outgoing edge)
                    elif edge['source'] == old_node_id:
                        # 将出边的源头重定向到新节点
                        new_edges_to_create.add((new_node_id, edge['target'], edge.get('relationship', 'related_to')))
            
            # 批量创建新的、去重后的边
            for source_id, target_id, relationship in new_edges_to_create:
                # 确保自己不指向自己
                if source_id == target_id:
                    continue
                source_node = state.graph.get_node(source_id)
                target_node = state.graph.get_node(target_id)
                if source_node and target_node:
                    state.add_edge(source_id, target_id, relationship=relationship)
                    results["added_edges"].append({
                        "source_id": source_id, "source_title": source_node.get("title", source_id),
                        "target_id": target_id, "target_title": target_node.get("title", target_id),
                        "relationship": relationship
                    })
                    logger.info(f"MERGE: Re-wired edge: {source_node.get('title')} → {relationship} → {target_node.get('title')}")

            # 3. 删除所有旧的、被合并的节点
            for old_node_id in nodes_to_merge_ids:
                node = state.graph.get_node(old_node_id)
                if node:
                    state.graph.delete_node(old_node_id)
                    results["removed_nodes"].append({
                        "id": old_node_id,
                        "title": node.get("title", old_node_id),
                        "reason": "Merged into new node " + new_node_id
                    })
                    logger.info(f"MERGE: Deleted old node '{node.get('title')}' (ID: {old_node_id})")
        elif suggestion['suggestion_type'] == 'REFACTOR_AND_PROMOTE':
            details = suggestion['details']
            node_to_delete_id = details.get("node_to_delete")
            new_parent_id = details.get("new_parent_node")

            if not node_to_delete_id or not new_parent_id:
                results["errors"].append("REFACTOR_AND_PROMOTE suggestion is missing node_to_delete or new_parent_node details.")
                continue

            node_to_delete = state.graph.get_node(node_to_delete_id)
            new_parent_node = state.graph.get_node(new_parent_id)

            if not node_to_delete or not new_parent_node:
                results["errors"].append(f"REFACTOR: One or both nodes do not exist: {node_to_delete_id}, {new_parent_id}")
                continue
            
            # 1. 查找并收集所有需要重新连接的子节点
            children_to_reconnect_ids = []
            for edge in state.graph.get_edges():
                if edge['source'] == node_to_delete_id:
                    children_to_reconnect_ids.append(edge['target'])
            
            logger.info(f"REFACTOR: Identified {len(children_to_reconnect_ids)} children of '{node_to_delete.get('title')}' to promote.")

            # 2. 为每个子节点创建到新父节点的新连接
            for child_id in children_to_reconnect_ids:
                child_node = state.graph.get_node(child_id)
                if child_node:
                    # 默认提升后的关系为 is_component_of，这在大多数情况下是合理的
                    relationship = "is_component_of"
                    state.add_edge(new_parent_id, child_id, relationship=relationship)
                    results["added_edges"].append({
                        "source_id": new_parent_id, "source_title": new_parent_node.get("title", new_parent_id),
                        "target_id": child_id, "target_title": child_node.get("title", child_id),
                        "relationship": relationship
                    })
                    logger.info(f"REFACTOR: Promoted '{child_node.get('title')}' by connecting it to new parent '{new_parent_node.get('title')}'")

            # 3. 在所有子节点都安全地重新连接后，删除旧的父节点
            state.graph.delete_node(node_to_delete_id)
            results["removed_nodes"].append({
                "id": node_to_delete_id,
                "title": node_to_delete.get("title", node_to_delete_id),
                "reason": f"Refactored and promoted children to {new_parent_id}"
            })
            logger.info(f"REFACTOR: Deleted old parent node '{node_to_delete.get('title')}' (ID: {node_to_delete_id})")

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
