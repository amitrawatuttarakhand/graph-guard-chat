"""Streamlit UI. Embedded mode by default (one app, deployable on Streamlit Community Cloud);
set API_URL (env or secret) to use a separate FastAPI backend instead."""
import os

import streamlit as st

from client import EmbeddedBackend, HttpBackend

st.set_page_config(page_title="Guarded KG Chat", page_icon="🕸️", layout="wide")


def secret(name: str, default: str = "") -> str:
    try:
        return st.secrets.get(name, default)
    except Exception:  # no secrets file locally
        return default


if secret("OPENROUTER_API_KEY"):
    os.environ["OPENROUTER_API_KEY"] = secret("OPENROUTER_API_KEY")
API_URL = os.getenv("API_URL") or secret("API_URL")


@st.cache_resource(show_spinner="Starting backend…")
def get_backend():
    return HttpBackend(API_URL) if API_URL else EmbeddedBackend()


def call(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        st.error(f"Backend error: {e}")
        return None


def to_dot(graph: dict, highlight: set[str]) -> str:
    esc = lambda s: s.replace('"', '\\"')
    lines = [
        "digraph G {",
        "rankdir=LR;",
        'node [shape=box, style="rounded,filled", fillcolor="#eef2ff", fontname="Helvetica"];',
        'edge [fontname="Helvetica", fontsize=10];',
    ]
    for n in graph["nodes"]:
        fill = ' [fillcolor="#fde68a"]' if n in highlight else ""
        lines.append(f'"{esc(n)}"{fill};')
    for e in graph["edges"]:
        lines.append(f'"{esc(e["subject"])}" -> "{esc(e["object"])}" [label="{esc(e["relation"])}"];')
    lines.append("}")
    return "\n".join(lines)


if not API_URL and not os.getenv("OPENROUTER_API_KEY"):
    st.warning("Set `OPENROUTER_API_KEY` (Streamlit secret or env var), or `API_URL` for a FastAPI backend.")
    st.stop()

try:
    backend = get_backend()
except Exception as e:
    st.error(f"Could not start backend: {e}")
    st.stop()

st.session_state.setdefault("messages", [])
st.session_state.setdefault("last_entities", [])

# ---------------- sidebar ----------------
with st.sidebar:
    st.header("Backend")
    st.caption("FastAPI: " + API_URL if API_URL else "Embedded (in-process)")
    health = call(backend.health)
    if health:
        st.success(f"{health['nodes']} nodes · {health['edges']} edges")

    st.header("Add a fact")
    with st.form("add_triple", clear_on_submit=True):
        s = st.text_input("Subject", placeholder="Dave")
        r = st.text_input("Relation", placeholder="works at")
        o = st.text_input("Object", placeholder="Globex")
        if st.form_submit_button("Add") and s and r and o:
            if call(backend.add_triple, s, r, o):
                st.toast("Fact added")

    if st.button("Clear chat"):
        st.session_state.messages = []
        st.session_state.last_entities = []
        st.rerun()

# ---------------- tabs ----------------
chat_tab, graph_tab = st.tabs(["💬 Chat", "🕸️ Knowledge graph"])

with chat_tab:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m.get("facts"):
                with st.expander(f"Facts used ({len(m['facts'])})"):
                    st.markdown("\n".join(f"- {f}" for f in m["facts"]))

    if prompt := st.chat_input("Ask about people, companies, projects…"):
        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                res = call(backend.chat, prompt, history)
            if res:
                st.markdown(res["answer"])
                if res["facts_used"]:
                    with st.expander(f"Facts used ({len(res['facts_used'])})"):
                        st.markdown("\n".join(f"- {f}" for f in res["facts_used"]))
                st.session_state.last_entities = res["entities"]
                st.session_state.messages.append(
                    {"role": "assistant", "content": res["answer"], "facts": res["facts_used"]}
                )

with graph_tab:
    graph = call(backend.graph)
    if graph:
        if st.session_state.last_entities:
            st.caption("Highlighted: entities from your last question")
        st.graphviz_chart(to_dot(graph, set(st.session_state.last_entities)))
        with st.expander("Raw triples"):
            st.dataframe(graph["edges"])
