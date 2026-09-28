"""Builds the NeMo Guardrails engine and wires the KG + document store in as
custom actions."""
from pathlib import Path

from nemoguardrails import LLMRails, RailsConfig

from .checks import is_input_safe, mask_pii
from .documents import docs
from .kg import kg

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

# Upper bound on document text sent to the LLM per question. Without a cap, a
# big PDF (e.g. a personnel directory) could put tens of thousands of tokens
# in one prompt, and if the LLM call fails NeMo Guardrails replaces the whole
# answer with a generic "internal error" message.
MAX_DOC_CONTEXT_CHARS = 12000


async def check_input_safety(text: str) -> bool:
    return is_input_safe(text)


async def retrieve_context(query: str) -> str:
    """Link entities in the query for graph facts, and TF-IDF search the
    uploaded documents; merge both into one block of grounding context."""
    _, facts = kg.context_for(query)
    chunks = docs.search_or_all(query)

    parts = []
    if facts:
        parts.append("Graph facts:\n" + "\n".join(f"- {f}" for f in facts))
    if chunks:
        excerpts = "\n".join(f"- ({c.source}) {c.content}" for c in chunks)
        if len(excerpts) > MAX_DOC_CONTEXT_CHARS:
            excerpts = excerpts[:MAX_DOC_CONTEXT_CHARS] + " ...[truncated]"
        parts.append("Document excerpts:\n" + excerpts)
    return "\n\n".join(parts)


async def mask_pii_action(text: str) -> str:
    return mask_pii(text)


def build_rails() -> LLMRails:
    rails = LLMRails(RailsConfig.from_path(str(CONFIG_DIR)))
    rails.register_action(check_input_safety, "check_input_safety")
    rails.register_action(retrieve_context, "retrieve_context")
    rails.register_action(mask_pii_action, "mask_pii")
    return rails
