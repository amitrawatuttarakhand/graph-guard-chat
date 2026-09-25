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
