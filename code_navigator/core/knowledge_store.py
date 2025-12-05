"""
Phase 1 knowledge store: persistence + simple metadata access.

Responsibility:
- Store the graph.
- Save/load it from disk.
- Provide a few convenience methods (stats, basic lookups).

No embeddings or LLMs here.
"""

import os
import pickle
from dataclasses import dataclass
from typing import Optional

import networkx as nx


@dataclass
class GraphStats:
    num_nodes: int
    num_edges: int
    num_files: int
    num_functions: int
    num_classes: int


class KnowledgeStore:
    def __init__(self, cache_dir: str = ".code_nav_cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.graph: Optional[nx.DiGraph] = None

    def _cache_path(self, codebase_id: str) -> str:
        return os.path.join(self.cache_dir, f"{codebase_id}_graph.pkl")

    def save_graph(self, codebase_id: str, graph: nx.DiGraph) -> None:
        path = self._cache_path(codebase_id)
        with open(path, "wb") as f:
            pickle.dump(graph, f)
        self.graph = graph

    def load_graph(self, codebase_id: str) -> Optional[nx.DiGraph]:
        path = self._cache_path(codebase_id)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            graph = pickle.load(f)
        self.graph = graph
        return graph

    def get_stats(self) -> GraphStats:
        if self.graph is None:
            return GraphStats(0, 0, 0, 0, 0)

        g = self.graph
        num_nodes = g.number_of_nodes()
        num_edges = g.number_of_edges()

        num_files = sum(1 for _, a in g.nodes(data=True) if a.get("type") == "file")
        num_functions = sum(1 for _, a in g.nodes(data=True) if a.get("type") == "function")
        num_classes = sum(1 for _, a in g.nodes(data=True) if a.get("type") == "class")

        return GraphStats(
            num_nodes=num_nodes,
            num_edges=num_edges,
            num_files=num_files,
            num_functions=num_functions,
            num_classes=num_classes,
        )
