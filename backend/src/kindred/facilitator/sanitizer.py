"""Sanitizer — injection pattern detection, query cleanup, artifact framing.

The Facilitator is a RAG librarian. It never passes raw queries or raw artefact
text into an LLM directly. Instead:
  1. `sanitize_query` strips control chars and caps length.
  2. `detect_injection_patterns` flags common prompt-injection attempts so the
     /ask endpoint can reject them with a 400 and log to audit.
  3. `frame_artifact` wraps retrieved content in a delimited envelope with the
     closing-tag escaped, so a downstream consumer can parse provenance without
     being fooled by content that tries to break out of the envelope.

All detection is regex — deterministic, zero LLM calls. Covered by the
adversarial corpus in `tests/adversarial/`.
"""
from __future__ import annotations

import re
from typing import NamedTuple


class InjectionHit(NamedTuple):
    pattern: str
    match: str


_CLOSING_TAG = "</kin:artifact>"
_ESCAPED_CLOSING_TAG = "&lt;/kin:artifact&gt;"
_MAX_QUERY_LEN = 10_000
# Control chars to strip: C0 except \t, \n, \r; plus DEL and C1.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


# Ordered: first list → first pattern wins when reporting; all hits collected.
INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ignore_previous",
        re.compile(
            r"\b(ignore|disregard|forget)\s+(all\s+|the\s+|any\s+)?"
            r"(previous|prior|above)\s+"
            r"(instructions?|prompts?|rules?|messages?)",
            re.IGNORECASE,
        ),
    ),
    (
        "system_role_spoof",
        re.compile(
            r"<\|im_start\|>|<\|im_end\|>|<\|system\|>|\bsystem\s*:",
            re.IGNORECASE,
        ),
    ),
    (
        "tool_call_injection",
        re.compile(r"<function_calls>|<invoke\s+name=", re.IGNORECASE),
    ),
    (
        "jailbreak_persona",
        re.compile(
            r"\b(DAN|do anything now|developer mode|jailbreak)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "prompt_leak",
        re.compile(
            r"\b(print|reveal|show|repeat|expose|dump|output)\s+"
            r"(me\s+|us\s+)?"
            r"(your\s+|the\s+)?"
            r"(system\s+|initial\s+|original\s+)?"
            r"(prompt|instructions|system\s+message)",
            re.IGNORECASE,
        ),
    ),
    (
        "url_fetch_redirect",
        re.compile(
            r"\bfetch\s+(this|the)\s+url\s*:\s*https?://",
            re.IGNORECASE,
        ),
    ),
    (
        "shell_execution",
        re.compile(
            r"\b(rm\s+-rf|curl\s+\S+\s*\|\s*sh|wget\s+\S+\s*\|\s*sh|"
            r"eval\s*\(|exec\s*\(|bash\s+-c|/bin/sh\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "data_exfiltration",
        re.compile(r"\bpost\s+.*\bto\s+https?://", re.IGNORECASE),
    ),
    (
        "delimiter_break",
        re.compile(re.escape(_CLOSING_TAG), re.IGNORECASE),
    ),
    (
        "instruction_override",
        re.compile(
            r"\b(new|updated|corrected|revised|real)\s+instructions?\s*:",
            re.IGNORECASE,
        ),
    ),
    (
        "markdown_inject",
        re.compile(r"!\[.*?\]\(javascript:", re.IGNORECASE),
    ),
    (
        "role_hijack",
        re.compile(
            r"\b(you are now|from now on,?\s+you are|pretend to be|act as)\s+"
            r"(a\s+|an\s+)?(different|new|malicious|evil|unfiltered)",
            re.IGNORECASE,
        ),
    ),
]


def detect_injection_patterns(text: str) -> list[InjectionHit]:
    """Return all pattern matches in `text`. Empty list means clean."""
    hits: list[InjectionHit] = []
    for name, pat in INJECTION_PATTERNS:
        m = pat.search(text)
        if m:
            hits.append(InjectionHit(pattern=name, match=m.group(0)))
    return hits


def sanitize_query(query: str) -> str:
    """Strip control chars (except \\t\\n\\r) and enforce max length.

    Raises ValueError if query exceeds 10k chars — the caller maps this to HTTP 400.
    """
    if len(query) > _MAX_QUERY_LEN:
        raise ValueError(f"query too long: {len(query)} > {_MAX_QUERY_LEN}")
    return _CONTROL_CHARS_RE.sub("", query)


def frame_artifact(
    *, content_id: str, tier: str, author_pubkey: str, content: str
) -> str:
    """Wrap artifact content in a delimited envelope safe from break-out.

    Output: ``<kin:artifact id=... tier=... author=...>\\n<body>\\n</kin:artifact>``

    Any embedded closing tag in ``content`` is HTML-escaped so the outer envelope
    stays unambiguous.
    """
    escaped = content.replace(_CLOSING_TAG, _ESCAPED_CLOSING_TAG)
    return (
        f"<kin:artifact id={content_id} tier={tier} author={author_pubkey}>\n"
        f"{escaped}\n"
        f"{_CLOSING_TAG}"
    )
