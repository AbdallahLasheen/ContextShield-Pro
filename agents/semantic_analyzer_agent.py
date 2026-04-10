"""
ContextShield — Agent 1: Semantic Analyzer Agent

Responsibility:
    Scan the input prompt using regex-based pattern matching across 5 attack
    categories (jailbreak, role_override, data_exfiltration, rag_poisoning,
    obfuscation) and compute a per-category risk score.

Input payload:  { "text": str }
Output data:    { "cat_scores": dict, "triggered": list, "sem_risk": float,
                  "dominant": str }
"""

import re
from typing import Dict, List
from .base_agent import BaseAgent, AgentMessage


ATTACK_PATTERNS: Dict[str, List[str]] = {
    "jailbreak": [
        r"\bignore\s+(all\s+)?(previous|prior|above|former)\s+(instructions?|rules?|guidelines?|context)\b",
        r"\byou\s+are\s+now\s+(an?\s+)?(unrestricted|uncensored|unfiltered|free|different|new)\b",
        r"\bact\s+as\s+(an?\s+)?(unrestricted|uncensored|unfiltered|DAN|evil|jailbroken)\b",
        r"\bforget\s+(everything|all|your)\s*(you'?ve?\s*)?(been\s+)?(trained|told|instructed|taught)\b",
        r"\bpretend\s+(you\s+)?(have\s+no\s+|don'?t\s+have\s+)(restrictions?|rules?|limits?|guidelines?)\b",
        r"\bDAN\b.*\bmode\b",
        r"\byou\s+(must|have\s+to|should)\s+(comply|obey|follow)\s+(without\s+)?(question|hesitation)\b",
    ],
    "role_override": [
        r"\byou\s+are\s+no\s+longer\s+a?\s*(helpful\s+)?assistant\b",
        r"\byour\s+(new\s+)?(role|purpose|goal|job|task|identity)\s+is\b",
        r"\bswitch\s+(to\s+)?(admin|developer|root|sudo|unrestricted)\s+mode\b",
        r"\b(admin|developer|god|root)\s+(mode|override|access|command)\b",
        r"\bsystem\s*(prompt\s*)?override\b",
        r"\byou\s+will\s+(now\s+)?(?:respond|behave|act)\s+as\s+if\b",
    ],
    "data_exfiltration": [
        r"\b(output|print|show|reveal|expose|leak|dump)\s+(all\s+)?(user|customer|employee|admin)\s*(data|info|records?|credentials?|passwords?)\b",
        r"\bSELECT\s+\*\s+FROM\b",
        r"\b(api\s+key|secret\s+key|private\s+key|access\s+token|auth\s+token)\b",
        r"\b(database|db)\s+(credentials?|password|username|connection)\b",
    ],
    "rag_poisoning": [
        r"\b(note|remember|important)\s*:\s*(for\s+this\s+(session|conversation|context)|from\s+now\s+on)\b",
        r"\bredefine\b.*\bto\s+mean\b",
        r"<\s*(hidden|secret|system|admin|inject)\s*>",
        r"\[\s*(INJECT|SYSTEM|OVERRIDE|ADMIN|HIDDEN|NEW\s+INSTRUCTION)\s*\]",
        r"\b###\s*(ADMIN|SYSTEM|OVERRIDE|COMMAND|INJECT)\b",
        r"\bbefore\s+responding\s+to\s+(any|every|all)\b",
    ],
    "obfuscation": [
        r"b[a4]s[e3]64|h[e3]x\s*(enc[o0]d[e3])?",
        r"\\u00[0-9a-f]{2}|\\x[0-9a-f]{2}",
        r"\b(encode|encrypt|obfuscate|scramble)\s+(the\s+)?(following|instruction|command|request)\b",
        r"(?:[a-z]\s){5,}",
    ],
}

CATEGORY_WEIGHTS = {
    "jailbreak": 0.30,
    "role_override": 0.25,
    "data_exfiltration": 0.25,
    "rag_poisoning": 0.15,
    "obfuscation": 0.05,
}

_COMPILED = {
    cat: [re.compile(p, re.IGNORECASE | re.DOTALL) for p in patterns]
    for cat, patterns in ATTACK_PATTERNS.items()
}


class SemanticAnalyzerAgent(BaseAgent):
    """
    Agent 1 — Semantic Analyzer

    Uses regex pattern libraries to detect known attack signatures.
    Returns per-category scores and an overall semantic risk score.
    """

    def __init__(self):
        super().__init__("SemanticAnalyzerAgent")

    def _process(self, message: AgentMessage) -> dict:
        text: str = message.payload["text"]

        cat_scores = {}
        for cat, patterns in _COMPILED.items():
            matches = sum(1 for p in patterns if p.search(text))
            cat_scores[cat] = round(min(matches / len(patterns), 1.0), 4)

        triggered = [c for c, s in cat_scores.items() if s > 0]
        sem_risk = round(
            min(sum(CATEGORY_WEIGHTS[c] * cat_scores[c] for c in cat_scores), 1.0), 4
        )
        dominant = max(cat_scores, key=cat_scores.get) if triggered else "none"

        self._logger.debug(
            f"triggered={triggered}, sem_risk={sem_risk}, dominant={dominant}"
        )
        return {
            "cat_scores": cat_scores,
            "triggered": triggered,
            "sem_risk": sem_risk,
            "dominant": dominant,
        }
