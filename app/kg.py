"""Small in-memory knowledge graph (networkx) with entity linking + subgraph retrieval."""
import json
import re
from pathlib import Path

import networkx as nx


def _norm_rel(r: str) -> str:
    return re.sub(r"\s+", "_", r.strip().upper())


class KnowledgeGraph:
    def __init__(self) -> None:
        self.g = nx.MultiDiGraph()
        self._index: dict[str, str] = {}  # lowercase name -> canonical name

    # ---------- write ----------
    def add_triple(self, subject: str, relation: str, obj: str) -> None:
        subject, obj, rel = subject.strip(), obj.strip(), _norm_rel(relation)
        for name in (subject, obj):
            self._index.setdefault(name.lower(), name)
        s, o = self._index[subject.lower()], self._index[obj.lower()]
        if not self.g.has_edge(s, o, key=rel):
            self.g.add_edge(s, o, key=rel)

    def load_json(self, path: str | Path) -> None:
        for t in json.loads(Path(path).read_text()):
            self.add_triple(t["subject"], t["relation"], t["object"])

    # ---------- read ----------
    def find_entities(self, text: str) -> list[str]:
        low = text.lower()
        found = []
        for key in sorted(self._index, key=len, reverse=True):
            if re.search(rf"\b{re.escape(key)}\b", low):
                found.append(self._index[key])
        return found

    def neighborhood_facts(self, entities: list[str], hops: int = 2, max_facts: int = 40) -> list[str]:
        nodes: set[str] = set()
        und = self.g.to_undirected(as_view=True)
        for e in entities:
            if e in self.g:
                reach = nx.single_source_shortest_path_length(und, e, cutoff=hops)
                nodes.update(reach)
        facts = [
            f"{u} {k} {v}"
            for u, v, k in self.g.edges(keys=True)
            if u in nodes and v in nodes
        ]
        return facts[:max_facts]

    def context_for(self, query: str, hops: int = 2) -> tuple[list[str], list[str]]:
        entities = self.find_entities(query)
        return entities, self.neighborhood_facts(entities, hops)

    def export(self) -> dict:
        return {
            "nodes": list(self.g.nodes),
            "edges": [{"subject": u, "relation": k, "object": v} for u, v, k in self.g.edges(keys=True)],
        }


kg = KnowledgeGraph()
