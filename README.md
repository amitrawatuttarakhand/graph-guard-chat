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

## Caching
The app caches chat answers (keyed on the question + prior turns) and the
graph fetch for 1 hour, so repeating a question or reopening the graph tab
doesn't re-call the LLM or re-fetch the graph. Adding a fact in the sidebar
clears both caches so answers reflect it immediately.

## Permanent storage for facts added in the app (optional)
Without this, facts added via the sidebar/`/kg/triples` are temporary — only
`data/seed_triples.json` survives a restart (see above). To make added facts
permanent too, connect a free Supabase (Postgres) project:

1. Create a project at supabase.com (free tier).
2. In the SQL editor, run:
       create table triples (
         id bigint generated always as identity primary key,
         subject text not null,
         relation text not null,
         object text not null,
         created_at timestamptz default now(),
         unique (subject, relation, object)
       );
       alter table triples enable row level security;
       create policy "public read" on triples for select using (true);
       create policy "public insert" on triples for insert with check (true);
   (These policies allow anyone to read/insert — fine for a demo, not for
   sensitive data. Add auth before using this for anything real.)
3. In Project Settings -> API, copy the Project URL and the `anon` public key.
4. Add them as secrets/env vars: `SUPABASE_URL` and `SUPABASE_KEY`.
5. Redeploy / restart. The sidebar will show "Facts you add are saved
   permanently" once it's connected, and on every startup the app loads
   `data/seed_triples.json` plus everything in the `triples` table.

Without `SUPABASE_URL`/`SUPABASE_KEY` set, the app runs exactly as before —
this is fully optional.
