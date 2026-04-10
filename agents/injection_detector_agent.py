"""
ContextShield — Agent 2: Injection Detector Agent

Responsibility:
    Detect structural and contextual injection signals that go beyond simple
    keyword matching — boundary separators, system tags, XML injections,
    base64 blocks, spaced-letter obfuscation, and length anomalies.

Input payload:  { "text": str }
Output data:    { "inj_conf": float, "inj_signals": list[str],
                  "length_anomaly": bool }
"""

import re
from .base_agent import BaseAgent, AgentMessage

INJECTION_SIGNALS = [
    ("boundary_separator",    r"(?:^|\n)\s*(?:-{3,}|={3,}|\*{3,}|#{3,})\s*(?:\n|$)",           0.15),
    ("end_of_context_marker", r"\b(?:\[END\]|\[STOP\]|\[DONE\]|<end>|<stop>|\[CONTEXT END\])\b", 0.20),
    ("system_tag",            r"<\|?\s*(?:system|user|assistant|human|im_start|im_end)\s*\|?>",  0.25),
    ("xml_injection_tag",     r"<\s*(?:inject|override|hidden|secret|admin|command)\s*>",         0.30),
    ("imperative_ignore",
        r"\b(?:ignore|disregard|forget|bypass|skip|override)\s+(?:all\s+)?(?:previous|prior|above|former|your)\s+(?:instructions?|rules?|context|guidelines?|prompt)\b",
        0.35),
    ("imperative_reveal",
        r"\b(?:reveal|expose|leak|dump|output|print|show|return)\s+(?:the\s+)?(?:system\s+prompt|api\s+key|secret|password|credentials?|token)\b",
        0.35),
    ("role_switch",
        r"\b(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be|from\s+now\s+on\s+you\s+are)\s+(?:an?\s+)?(?:unrestricted|uncensored|evil|DAN|different|new)\b",
        0.30),
    ("admin_command",
        r"\b(?:admin|developer|god|root|sudo)\s*(?:mode|command|override|access|instruction)\b",
        0.25),
    ("base64_block",          r"(?:[A-Za-z0-9+/]{40,}={0,2})",                                  0.20),
    ("spaced_letters",        r"(?:[a-zA-Z]\s){6,}[a-zA-Z]",                                    0.20),
    ("rag_redefinition",
        r"\b(?:note|remember|important)\s*:\s*(?:for\s+this\s+(?:session|conversation)|from\s+now)\b",
        0.25),
    ("rag_bracket_inject",
        r"\[\s*(?:INJECT|SYSTEM|OVERRIDE|ADMIN|HIDDEN|NEW\s+INSTRUCTION|IGNORE)\s*\]",
        0.30),
    ("before_responding",
        r"\bbefore\s+(?:you\s+)?respond(?:ing)?\b.{0,80}\b(?:output|reveal|provide|send|show)\b",
        0.30),
]

_COMPILED_SIGNALS = [
    (name, re.compile(pattern, re.IGNORECASE | re.DOTALL | re.MULTILINE), weight)
    for name, pattern, weight in INJECTION_SIGNALS
]

LENGTH_ANOMALY_THRESHOLD = 300  # words


class InjectionDetectorAgent(BaseAgent):
    """
    Agent 2 — Injection Detector

    Scans for 13 injection signal patterns and flags length anomalies.
    Returns a confidence score and the list of triggered signal names.
    """

    def __init__(self):
        super().__init__("InjectionDetectorAgent")

    def _process(self, message: AgentMessage) -> dict:
        text: str = message.payload["text"]

        triggered, confidence = [], 0.0
        for name, pattern, weight in _COMPILED_SIGNALS:
            if pattern.search(text):
                triggered.append(name)
                confidence += weight

        length_anomaly = len(text.split()) > LENGTH_ANOMALY_THRESHOLD
        if length_anomaly:
            confidence += 0.10

        result = {
            "inj_conf": round(min(confidence, 1.0), 4),
            "inj_signals": triggered,
            "length_anomaly": length_anomaly,
        }
        self._logger.debug(f"signals={triggered}, conf={result['inj_conf']}")
        return result
