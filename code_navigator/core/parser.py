"""
Phase 1 parser: build a simple structural graph of a Python codebase.

Nodes:
  - file:      id = "path/to/file.py"
  - class:     id = "path/to/file.py::ClassName"
  - function:  id = "path/to/file.py::func_name"

Edges:
  - file --defined_in--> class/function
  - file --file_import--> file
  - function --calls--> function (same file only, basic resolution)

We intentionally keep this simple in Phase 1 and enrich later.
"""

import ast
import os
from dataclasses import dataclass
from typing import Dict, List

import networkx as nx

@dataclass
class ParsedFile:
    path: str            # repo-relative path
    ast_tree: ast.AST
    functions: Dict[str, ast.FunctionDef]
    classes: Dict[str, ast.ClassDef]
    imports: Dict[str, str]        # alias -> module (for "import x as y")
    from_imports: Dict[str, str]   # name -> module (for "from x import y")


class CodeParser:
    """
    Parse a Python repo into a NetworkX DiGraph with basic structure.
    """

    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(repo_path)
        self.graph = nx.DiGraph()
        self.files: Dict[str, ParsedFile] = {}

    # ---------- Public API ----------

    def parse(self) -> nx.DiGraph:
        self._collect_files()
        self._index_files()
        self._add_nodes_and_edges()
        self._resolve_calls_basic()
        return self.graph

    # ---------- Internal helpers ----------

    def _collect_files(self) -> List[str]:
        py_files: List[str] = []
        for root, _, files in os.walk(self.repo_path):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, self.repo_path)
                py_files.append(rel)

                # pre-create file node
                self.graph.add_node(
                    rel,
                    type="file",
                    display_name=rel,
                )
        return py_files

    def _index_files(self) -> None:
        """
        Parse each file into an AST and collect top-level functions, classes, and imports.
        """
        for node_id, attrs in list(self.graph.nodes(data=True)):
            if attrs.get("type") != "file":
                continue

            rel_path = node_id
            full_path = os.path.join(self.repo_path, rel_path)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    src = f.read()
                tree = ast.parse(src)
            except Exception as exc:
                # In a real app we'd log this; for now we just skip broken files.
                print(f"[parser] Failed to parse {rel_path}: {exc}")
                continue

            functions: Dict[str, ast.FunctionDef] = {}
            classes: Dict[str, ast.ClassDef] = {}
            imports: Dict[str, str] = {}
            from_imports: Dict[str, str] = {}

            for stmt in tree.body:
                if isinstance(stmt, ast.FunctionDef):
                    functions[stmt.name] = stmt
                elif isinstance(stmt, ast.ClassDef):
                    classes[stmt.name] = stmt
                elif isinstance(stmt, ast.Import):
                    for alias in stmt.names:
                        mod = alias.name.split(".")[0]
                        asname = alias.asname or mod
                        imports[asname] = mod
                elif isinstance(stmt, ast.ImportFrom) and stmt.module:
                    mod = stmt.module.split(".")[0]
                    for alias in stmt.names:
                        asname = alias.asname or alias.name
                        from_imports[asname] = mod

            self.files[rel_path] = ParsedFile(
                path=rel_path,
                ast_tree=tree,
                functions=functions,
                classes=classes,
                imports=imports,
                from_imports=from_imports,
            )

    def _add_nodes_and_edges(self) -> None:
        """
        Add class/function nodes and their 'defined_in' + 'file_import' edges.
        """
        for rel_path, pfile in self.files.items():
            # Classes
            for cname, cnode in pfile.classes.items():
                cid = f"{rel_path}::{cname}"
                start = getattr(cnode, "lineno", 0)
                end = getattr(cnode, "end_lineno", start)
                loc = max(0, end - start + 1)

                self.graph.add_node(
                    cid,
                    type="class",
                    display_name=cname,
                    file=rel_path,
                    lineno=start,
                    end_lineno=end,
                    loc=loc,
                    doc=ast.get_docstring(cnode) or "",
                )
                self.graph.add_edge(rel_path, cid, label="defined_in")

            # Functions
            for fname, fnode in pfile.functions.items():
                fid = f"{rel_path}::{fname}"
                start = getattr(fnode, "lineno", 0)
                end = getattr(fnode, "end_lineno", start)
                loc = max(0, end - start + 1)
                params = [a.arg for a in fnode.args.args]

                self.graph.add_node(
                    fid,
                    type="function",
                    display_name=f"{fname}()",
                    file=rel_path,
                    lineno=start,
                    end_lineno=end,
                    loc=loc,
                    params=params,
                    doc=ast.get_docstring(fnode) or "",
                )
                self.graph.add_edge(rel_path, fid, label="defined_in")

            # File imports (file -> file)
            for module_name in list(pfile.imports.values()) + list(pfile.from_imports.values()):
                candidate = module_name + ".py"
                for other_path in self.files.keys():
                    if os.path.basename(other_path) == candidate:
                        self.graph.add_edge(rel_path, other_path, label="file_import")
                        break

    def _resolve_calls_basic(self) -> None:
        """
        Very simple call resolution:
        - Only within the same file.
        - Only direct calls like `foo()` where foo is a top-level function in that file.
        This is intentionally basic for Phase 1; we’ll refine later.
        """
        for rel_path, pfile in self.files.items():
            local_functions = pfile.functions

            for fname, fnode in local_functions.items():
                caller_id = f"{rel_path}::{fname}"
                for sub in ast.walk(fnode):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                        target_name = sub.func.id
                        if target_name in local_functions:
                            callee_id = f"{rel_path}::{target_name}"
                            self.graph.add_edge(caller_id, callee_id, label="calls")