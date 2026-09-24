"""Pure-Python guardrail checks (no LLM calls, unit-testable)."""
import re

_INJECTION = re.compile(
    r"ignore\s+(all\s+|any\s+)?(previous|prior|above)\s+instructions"
    r"|(reveal|show|print).{0,30}system\s+prompt"
    r"|developer\s+mode|jailbreak|\bDAN\b",
    re.I,
)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{8,}\d(?!\w)")


def is_input_safe(text: str) -> bool:
    return not _INJECTION.search(text or "")


def mask_pii(text: str) -> str:
    text = _EMAIL.sub("[email removed]", text or "")
    return _PHONE.sub("[phone removed]", text)
