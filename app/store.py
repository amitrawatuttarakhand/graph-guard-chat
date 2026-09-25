"""Optional persistent store for facts added at runtime, backed by Supabase
(Postgres). Configure SUPABASE_URL + SUPABASE_KEY to enable it; without them
the app just falls back to the seed file only (no error)."""
import os


def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    from supabase import create_client  # imported lazily: optional dependency

    return create_client(url, key)


class SupabaseStore:
    """Thin wrapper around a `triples` table: subject, relation, object."""

    def __init__(self, client) -> None:
        self.client = client

    def load_all(self) -> list[dict]:
        res = self.client.table("triples").select("subject,relation,object").execute()
        return res.data or []

    def add_triple(self, subject: str, relation: str, obj: str) -> None:
        self.client.table("triples").upsert(
            {"subject": subject, "relation": relation, "object": obj},
            on_conflict="subject,relation,object",
        ).execute()
