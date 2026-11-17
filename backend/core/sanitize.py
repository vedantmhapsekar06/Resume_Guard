import html
from typing import Any


def escape_payload(obj: Any) -> Any:
    """
    HTML-escapes every string in an API response. The frontend inserts candidate names,
    bullets and skills with innerHTML, so text extracted from an uploaded resume
    (e.g. '<img src=x onerror=...>') would otherwise execute in the reviewer's browser.
    Escaping at the API boundary keeps the UI untouched; if the UI later switches to
    textContent, remove this call to avoid double-escaping.
    """
    if isinstance(obj, str):
        return html.escape(obj, quote=True)
    if isinstance(obj, dict):
        return {k: escape_payload(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [escape_payload(v) for v in obj]
    return obj
