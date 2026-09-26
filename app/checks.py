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

_PRESIDIO_ENTITIES = [
    "EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON", "CREDIT_CARD",
    "US_SSN", "IBAN_CODE", "IP_ADDRESS", "LOCATION",
]


def is_input_safe(text: str) -> bool:
    return not _INJECTION.search(text or "")


def _regex_mask_pii(text: str) -> str:
    text = _EMAIL.sub("[email removed]", text or "")
    return _PHONE.sub("[phone removed]", text)


def _load_presidio():
    """Build Presidio's analyzer+anonymizer once, pointed at the spaCy model
    that's actually installed (avoids Presidio's own auto-download path,
    which can fail under restricted network setups)."""
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine

    conf = {"nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]}
    nlp_engine = NlpEngineProvider(nlp_configuration=conf).create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
    return analyzer, AnonymizerEngine()


try:
    _analyzer, _anonymizer = _load_presidio()
except Exception:
    _analyzer, _anonymizer = None, None  # spaCy model missing, etc. — fall back to regex


def mask_pii(text: str) -> str:
    """Mask emails, phone numbers, names, and more via Presidio (real NER)
    when available; otherwise fall back to the regex-only version."""
    if not text:
        return text
    if _analyzer is None:
        return _regex_mask_pii(text)
    try:
        results = _analyzer.analyze(text=text, language="en", entities=_PRESIDIO_ENTITIES, score_threshold=0.4)
        return _anonymizer.anonymize(text=text, analyzer_results=results).text
    except Exception:
        return _regex_mask_pii(text)  # never let a detector bug break the response