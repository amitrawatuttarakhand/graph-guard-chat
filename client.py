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

    def add_document(self, filename: str, text: str):
        return self._req("POST", "/documents", json={"filename": filename, "text": text})

    def list_documents(self):
        return self._req("GET", "/documents")


class EmbeddedBackend:
    """Runs the KG + document store + NeMo Guardrails inside the Streamlit
    process (no FastAPI needed)."""

    def __init__(self) -> None:
        from app.documents import docs
        from app.guardrails import build_rails
        from app.kg import kg
        from app.store import DocumentSupabaseStore, SupabaseStore, get_supabase_client

        self.kg = kg
        kg.load_json(SEED)
        self.docs = docs

        self.store = None
        self.doc_store = None
        sb = get_supabase_client()
        if sb:
            try:
                candidate = SupabaseStore(sb)
                for t in candidate.load_all():
                    kg.add_triple(t["subject"], t["relation"], t["object"])
                self.store = candidate  # only keep it if load_all actually worked
            except Exception:
                self.store = None  # bad URL/key surfaces here, not at connect time

            try:
                doc_candidate = DocumentSupabaseStore(sb)
                by_source: dict[str, list[str]] = {}
                for row in doc_candidate.load_all():
                    by_source.setdefault(row["source"], []).append(row["content"])
                for source, contents in by_source.items():
                    docs.add_chunks(source, contents)
                self.doc_store = doc_candidate
            except Exception:
                self.doc_store = None

        self.rails = build_rails()

    def health(self):
        g = self.kg.export()
        return {
            "status": "ok",
            "nodes": len(g["nodes"]),
            "edges": len(g["edges"]),
            "documents": len(self.docs.summary()),
            "doc_chunks": len(self.docs.chunks),
            "persistent": self.store is not None,
            "docs_persistent": self.doc_store is not None,
        }

    def chat(self, message: str, history: list[dict]):
        result = self.rails.generate(messages=history + [{"role": "user", "content": message}])
        entities, facts = self.kg.context_for(message)
        doc_chunks = self.docs.search(message)
        return {
            "answer": result["content"],
            "entities": entities,
            "facts_used": facts,
            "doc_sources": sorted({c.source for c in doc_chunks}),
        }

    def graph(self):
        return self.kg.export()

    def add_triple(self, s: str, r: str, o: str):
        self.kg.add_triple(s, r, o)
        if self.store:
            try:
                self.store.add_triple(s, r, o)
            except Exception:
                pass  # in-memory graph already has it; persistence is best-effort
        return {"added": 1, "persistent": self.store is not None}

    def add_document(self, filename: str, text: str):
        chunks = self.docs.add_document(filename, text)
        if self.doc_store:
            try:
                self.doc_store.add_chunks(filename, chunks)
            except Exception:
                pass  # in-memory store already has it; persistence is best-effort
        return {"chunks_added": len(chunks), "persistent": self.doc_store is not None}

    def list_documents(self):
        return {"documents": self.docs.summary()}