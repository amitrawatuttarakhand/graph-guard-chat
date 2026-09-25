"""Backend adapters: FastAPI over HTTP, or everything in-process (single-app deploys)."""
from pathlib import Path

import requests

SEED = Path(__file__).resolve().parent / "data" / "seed_triples.json"


class HttpBackend:
    def __init__(self, base_url: str) -> None:
        self.base = base_url.rstrip("/")

    def _req(self, method: str, path: str, **kw):
        r = requests.request(method, f"{self.base}{path}", timeout=60, **kw)
        r.raise_for_status()
        return r.json()

    def health(self):
        return self._req("GET", "/health")

    def chat(self, message: str, history: list[dict]):
        return self._req("POST", "/chat", json={"message": message, "history": history})

    def graph(self):
        return self._req("GET", "/kg/graph")

    def add_triple(self, s: str, r: str, o: str):
        return self._req("POST", "/kg/triples", json=[{"subject": s, "relation": r, "object": o}])


class EmbeddedBackend:
    """Runs the KG + NeMo Guardrails inside the Streamlit process (no FastAPI needed)."""

    def __init__(self) -> None:
        from app.guardrails import build_rails
        from app.kg import kg
        from app.store import SupabaseStore, get_supabase_client

        self.kg = kg
        kg.load_json(SEED)

        self.store = None
        sb = get_supabase_client()
        if sb:
            self.store = SupabaseStore(sb)
            for t in self.store.load_all():
                kg.add_triple(t["subject"], t["relation"], t["object"])

        self.rails = build_rails()

    def health(self):
        g = self.kg.export()
        return {
            "status": "ok",
            "nodes": len(g["nodes"]),
            "edges": len(g["edges"]),
            "persistent": self.store is not None,
        }

    def chat(self, message: str, history: list[dict]):
        result = self.rails.generate(messages=history + [{"role": "user", "content": message}])
        entities, facts = self.kg.context_for(message)
        return {"answer": result["content"], "entities": entities, "facts_used": facts}

    def graph(self):
        return self.kg.export()

    def add_triple(self, s: str, r: str, o: str):
        self.kg.add_triple(s, r, o)
        if self.store:
            self.store.add_triple(s, r, o)
        return {"added": 1, "persistent": self.store is not None}
