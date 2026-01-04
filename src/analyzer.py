import json
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, List, Set, Any
import sys
import os

# Ensure schema can be imported if needed, though we operate on JSON dicts here mostly
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

def load_data(filepath: str) -> Dict[str, Any]:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_graph(data: Dict[str, Any]) -> nx.DiGraph:
    G = nx.DiGraph()
    
    entities = data.get("entities", [])
    
    for entity in entities:
        # Add nodes for each state
        for state in entity.get("states", []):
            node_id = state["id"]
            G.add_node(node_id, 
                       label=state["name"], 
                       description=state.get("description", ""),
                       entity_id=entity["id"])
            
            # Add edges for transitions
            for transition in state.get("transitions", []):
                target_id = transition["target_state_id"]
                trigger_id = transition["trigger_id"]
                # Create edge
                G.add_edge(node_id, target_id, trigger=trigger_id, outputs=transition.get("output_ids", []))

    return G

def analyze_reachability(G: nx.DiGraph) -> List[str]:
    issues = []
    # 1. Dead Ends (Nodes with no outgoing edges)
    # Note: Using out_degree directly
    dead_ends = [n for n in G.nodes() if G.out_degree(n) == 0]
    if dead_ends:
        issues.append(f"[FAIL] Dead Ends Detected (States with no exit): {dead_ends}")
    
    # 2. Unreachable Nodes (from a potential start node)
    # Heuristic: 'idle' is usually a start node. Let's look for nodes with 0 in-degree that are NOT 'idle' or 'init'.
    roots = [n for n in G.nodes() if G.in_degree(n) == 0]
    issues.append(f"[INFO] Root Nodes (States with no entry): {roots}")

    return issues

def analyze_cycles(G: nx.DiGraph) -> List[str]:
    issues = []
    try:
        cycles = list(nx.simple_cycles(G))
        if cycles:
            issues.append(f"[WARN] Cycles Detected (Potential Loops): {len(cycles)} found.")
            for i, cycle in enumerate(cycles[:5]): # Show up to 5
                issues.append(f"   - Cycle {i+1}: {' -> '.join(cycle)}")
    except Exception as e:
        issues.append(f"[ERR] Cycle detection failed: {e}")
    return issues

def analyze_connectivity(G: nx.DiGraph) -> List[str]:
    issues = []
    # Weakly connected components (Subgraphs that are isolated)
    wcc = list(nx.weakly_connected_components(G))
    if len(wcc) > 1:
        issues.append(f"[WARN] Disconnected Subgraphs Detected: {len(wcc)} components found.")
        for comp in wcc:
            issues.append(f"   - Component: {comp}")
    return issues

def analyze_conflicts(G: nx.DiGraph, outputs_map: Dict[str, Any]) -> List[str]:
    issues = []
    # Iterate over all edges (transitions)
    for u, v, data in G.edges(data=True):
        output_ids = data.get("outputs", [])
        if not output_ids or len(output_ids) < 2:
            continue
        
        # Check for conflicts within this transition's outputs
        conflict_groups = {} # group_id -> output_id
        for oid in output_ids:
            # Safely get output definition
            out_def = outputs_map.get(oid)
            if not out_def:
                continue
            
            group = out_def.get("conflict_group")
            if group:
                if group in conflict_groups:
                    # Conflict found!
                    conflicting_oid = conflict_groups[group]
                    issues.append(f"[CRITICAL] Conflicting Outputs Detected on transition {u}->{v}: "
                                  f"'{oid}' and '{conflicting_oid}' both belong to conflict group '{group}'")
                else:
                    conflict_groups[group] = oid
    return issues

def generate_mermaid_diagram(G: nx.DiGraph) -> str:
    lines = ["stateDiagram-v2"]
    
    # Group by Entity if possible, but for v0 just flat
    # To handle Entity grouping, we can use subgraphs aka "state EntityName {}"
    
    # Group nodes by entity
    entity_map = {} # entity_id -> [nodes]
    for node, data in G.nodes(data=True):
        ent_id = data.get("entity_id", "unknown")
        if ent_id not in entity_map:
            entity_map[ent_id] = []
        entity_map[ent_id].append(node)
        
    for ent_id, nodes in entity_map.items():
        lines.append(f"    state \"{ent_id}\" {{")
        for node in nodes:
            label = G.nodes[node].get('label', node)
            lines.append(f"        {node} : {label}")
        lines.append("    }")

    # Edges
    for u, v, data in G.edges(data=True):
        trigger = data.get("trigger", "")
        lines.append(f"    {u} --> {v} : {trigger}")

    return "\n".join(lines)

import argparse

def dump_graph_debug(G: nx.DiGraph):
    print("\n=== DEBUG: Graph Structure Dump ===")
    print(f"Graph Type: {type(G)}")
    print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
    
    print("\n[Nodes]")
    for n, data in G.nodes(data=True):
        print(f"  {n}: {data}")

    print("\n[Edges]")
    for u, v, data in G.edges(data=True):
        print(f"  {u} -> {v}: {data}")
    print("===================================\n")

def main():
    parser = argparse.ArgumentParser(description='Requirement Analysis Tool')
    parser.add_argument('json_file', help='Path to extracted JSON file')
    parser.add_argument('--debug', action='store_true', help='Enable debug output of graph structure')
    args = parser.parse_args()

    json_file = args.json_file
    data = load_data(json_file)
    G = build_graph(data)
    
    if args.debug:
        dump_graph_debug(G)
    
    print("=== Analysis Report ===")
    print(f"Nodes: {G.number_of_nodes()}")
    print(f"Edges: {G.number_of_edges()}")
    
    print("\n--- Reachability Analysis ---")
    for msg in analyze_reachability(G):
        print(msg)
        
    print("\n--- Cycle Analysis ---")
    for msg in analyze_cycles(G):
        print(msg)

    print("\n--- Connectivity Analysis ---")
    for msg in analyze_connectivity(G):
        print(msg)
        
    print("\n--- Mermaid Diagram ---")
    print(generate_mermaid_diagram(G))
    
    # Pre-process outputs for conflict analysis
    # Flatten defined_outputs + unbound_outputs (if any legacy) into a map
    outputs_map = {}
    for out in data.get("defined_outputs", []):
        outputs_map[out["id"]] = out
    # Also check unbound just in case (though schema changed, data might lag)
    for out in data.get("unbound_outputs", []):
        outputs_map[out["id"]] = out

    print("\n--- Conflict Analysis ---")
    for msg in analyze_conflicts(G, outputs_map):
        print(msg)

    print("\n--- Semantic Analysis (LLM Simulated) ---")
    # For the POC, we iterate entities and simulate the LLM check
    for entity in data.get("entities", []):
        for state in entity.get("states", []):
            # Gather descriptions for triggers in this state
            trigger_descriptions = []
            for t in state.get("transitions", []):
                tid = t["trigger_id"]
                # Look up trigger description from unbound/global (simplified)
                # In real app, we need a better lookup.
                # For POC, let's rely on the ID name as a proxy for description if not found
                trigger_descriptions.append(tid) 
                
            # Special handling for our known samples using heuristic
            # In prod, this function `mock_llm_missing_else_check` is replaced by `ask_llm_about_missing_else`
            from semantic_checker import mock_llm_missing_else_check
            
            # Map IDs to 'Human Readable Conditions' for the simulation
            conditions = []
            for tid in trigger_descriptions:
                if tid == "trigger_start_cooling": conditions.append("Temp > 28.0")
                if tid == "trigger_stop_cooling": conditions.append("Temp < 24.0")
                # Add more mappings for other samples if needed
            
            if conditions:
                res = mock_llm_missing_else_check(state["name"], conditions)
                if res:
                    print(res)

if __name__ == "__main__":
    main()
