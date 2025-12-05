# code_navigator/cli.py

"""
Simple CLI for Phase 1.

Commands:
  - index <repo_path>
  - stats <repo_path>

We identify a codebase by hashing its absolute path.
Later we can switch to repo URL or git remote if needed.
"""

import argparse
import hashlib
import os
import time

from .core.parser import CodeParser
from .core.knowledge_store import KnowledgeStore


def _codebase_id_from_path(repo_path: str) -> str:
    abs_path = os.path.abspath(repo_path)
    return hashlib.sha256(abs_path.encode("utf-8")).hexdigest()[:16]


def cmd_index(args: argparse.Namespace) -> None:
    repo_path = args.path
    if not os.path.isdir(repo_path):
        raise SystemExit(f"Not a directory: {repo_path}")

    codebase_id = _codebase_id_from_path(repo_path)
    print(f"[index] Repo: {repo_path}")
    print(f"[index] Codebase id: {codebase_id}")

    t0 = time.perf_counter()
    parser = CodeParser(repo_path)
    graph = parser.parse()
    t1 = time.perf_counter()

    store = KnowledgeStore()
    store.save_graph(codebase_id, graph)
    t2 = time.perf_counter()

    print(f"[index] Parsed graph in {t1 - t0:.2f}s")
    print(f"[index] Saved graph in {t2 - t1:.2f}s")
    print(f"[index] Nodes: {graph.number_of_nodes()}, Edges: {graph.number_of_edges()}")


def cmd_stats(args: argparse.Namespace) -> None:
    repo_path = args.path
    codebase_id = _codebase_id_from_path(repo_path)
    store = KnowledgeStore()
    graph = store.load_graph(codebase_id)
    if graph is None:
        print("[stats] No cached graph found. Run 'index' first.")
        return

    stats = store.get_stats()
    print(f"[stats] Repo: {repo_path}")
    print(f"[stats] Codebase id: {codebase_id}")
    print(f"[stats] Nodes:     {stats.num_nodes}")
    print(f"[stats] Edges:     {stats.num_edges}")
    print(f"[stats] Files:     {stats.num_files}")
    print(f"[stats] Functions: {stats.num_functions}")
    print(f"[stats] Classes:   {stats.num_classes}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="code-nav", description="Code Navigator - Phase 1")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_index = subparsers.add_parser("index", help="Parse a repo and build the graph")
    p_index.add_argument("path", help="Path to the Python repository")
    p_index.set_defaults(func=cmd_index)

    p_stats = subparsers.add_parser("stats", help="Show graph statistics for a repo")
    p_stats.add_argument("path", help="Path to the Python repository")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
