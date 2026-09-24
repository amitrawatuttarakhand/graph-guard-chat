# Guarded Knowledge-Graph Chat

Streamlit UI + FastAPI API, both grounded in a networkx knowledge graph and
wrapped in NeMo Guardrails.

Flow: message -> input rail (prompt-injection check) -> input rail (KG entity
linking + 2-hop subgraph -> `$relevant_chunks`; refuses if nothing found)
-> LLM -> output rail (PII masking).

## Run locally
    pip install -r requirements.txt
    export OPENROUTER_API_KEY=sk-or-...
    streamlit run streamlit_app.py            # embedded mode, no API needed

Optional separate backend:

    uvicorn app.main:app --reload
    API_URL=http://localhost:8000 streamlit run streamlit_app.py

Tests (no key needed): `pip install -r requirements-dev.txt && python -m pytest`

## Push to GitHub
    git init && git add . && git commit -m "Guarded KG chat"
    git branch -M main
    git remote add origin https://github.com/<you>/<repo>.git
    git push -u origin main
(or `gh repo create <repo> --public --source . --push`)

## Deploy on Streamlit Community Cloud
1. share.streamlit.io -> New app -> pick the repo, branch `main`, main file `streamlit_app.py`.
2. Advanced settings -> Python 3.11; Secrets:
       OPENROUTER_API_KEY = "sk-or-..."
3. Deploy. `packages.txt` installs the compiler NeMo Guardrails' deps need.

Notes: in embedded mode, added facts live in memory, are shared by all
visitors, and reset on restart. Edit `data/seed_triples.json` for permanent data.

## LLM provider
Uses OpenRouter (OpenAI-compatible). Get a key at openrouter.ai/keys and set
`OPENROUTER_API_KEY`. Change the model in `config/config.yml`
(`model:` takes any OpenRouter id, e.g. `anthropic/claude-3.5-sonnet`).
