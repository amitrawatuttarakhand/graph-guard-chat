from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

from .guardrails import build_rails  # noqa: E402
from .kg import kg  # noqa: E402
from .store import SupabaseStore, get_supabase_client  # noqa: E402

SEED = Path(__file__).resolve().parent.parent / "data" / "seed_triples.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    kg.load_json(SEED)
    app.state.store = None
    sb = get_supabase_client()
    if sb:
        app.state.store = SupabaseStore(sb)
        for t in app.state.store.load_all():
            kg.add_triple(t["subject"], t["relation"], t["object"])
    app.state.rails = build_rails()
    yield


app = FastAPI(title="Guarded Knowledge-Graph Chat", lifespan=lifespan)


class Message(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []


class Triple(BaseModel):
    subject: str
    relation: str
    object: str


@app.get("/health")
def health():
    g = kg.export()
    return {
        "status": "ok",
        "nodes": len(g["nodes"]),
        "edges": len(g["edges"]),
        "persistent": app.state.store is not None,
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    messages = [m.model_dump() for m in req.history] + [{"role": "user", "content": req.message}]
    try:
        result = await app.state.rails.generate_async(messages=messages)
    except Exception as e:  # LLM/config errors
        raise HTTPException(status_code=502, detail=f"Guardrails/LLM error: {e}")
    entities, facts = kg.context_for(req.message)
    return {"answer": result["content"], "entities": entities, "facts_used": facts}


@app.get("/kg/graph")
def graph():
    return kg.export()


@app.get("/kg/neighbors/{entity}")
def neighbors(entity: str, hops: int = 1):
    found = kg.find_entities(entity)
    if not found:
        raise HTTPException(404, "Unknown entity")
    return {"entity": found[0], "facts": kg.neighborhood_facts(found[:1], hops)}


@app.post("/kg/triples", status_code=201)
def add_triples(triples: list[Triple]):
    for t in triples:
        kg.add_triple(t.subject, t.relation, t.object)
        if app.state.store:
            app.state.store.add_triple(t.subject, t.relation, t.object)
    return {"added": len(triples), "persistent": app.state.store is not None}
