"""Builds the NeMo Guardrails engine and wires the KG in as custom actions."""
from pathlib import Path

from nemoguardrails import LLMRails, RailsConfig

from .checks import is_input_safe, mask_pii
from .kg import kg

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


async def check_input_safety(text: str) -> bool:
    return is_input_safe(text)


async def retrieve_kg_context(query: str) -> str:
    """Link entities in the query, return their 2-hop neighborhood as plain facts."""
    _, facts = kg.context_for(query)
    return "\n".join(f"- {f}" for f in facts)


async def mask_pii_action(text: str) -> str:
    return mask_pii(text)


def build_rails() -> LLMRails:
    rails = LLMRails(RailsConfig.from_path(str(CONFIG_DIR)))
    rails.register_action(check_input_safety, "check_input_safety")
    rails.register_action(retrieve_kg_context, "retrieve_kg_context")
    rails.register_action(mask_pii_action, "mask_pii")
    return rails
