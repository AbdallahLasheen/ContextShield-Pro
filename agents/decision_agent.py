"""
ContextShield — Agent 4: Decision Agent

Responsibility:
    Fuse scores from the three upstream agents using a weighted formula and
    produce the final risk score + SAFE / FLAG / BLOCK verdict.

    Final risk = 0.60 × nn_score + 0.25 × sem_risk + 0.15 × inj_conf

    Thresholds:
        BLOCK  ≥ 0.70
        FLAG   ≥ 0.40
        SAFE   < 0.40

Input payload:  { "nn_score": float, "sem_risk": float, "inj_conf": float,
                  "cat_scores": dict, "triggered": list, "dominant": str,
                  "inj_signals": list, "length_anomaly": bool,
                  "word_count": int }
Output data:    full analysis dict ready to return to the caller
"""

from .base_agent import BaseAgent, AgentMessage

WEIGHTS = {"nn": 0.60, "semantic": 0.25, "injection": 0.15}

THRESHOLDS = {"block": 0.70, "flag": 0.40}


class DecisionAgent(BaseAgent):
    """
    Agent 4 — Decision Agent

    The final stage in the pipeline. Combines upstream scores, applies
    threshold logic, and produces the verdict consumed by the API and UI.
    """

    def __init__(self):
        super().__init__("DecisionAgent")

    def _process(self, message: AgentMessage) -> dict:
        p = message.payload

        nn_score: float  = p.get("nn_score",  0.0)
        sem_risk: float  = p.get("sem_risk",  0.0)
        inj_conf: float  = p.get("inj_conf",  0.0)

        final_risk = round(
            WEIGHTS["nn"] * nn_score
            + WEIGHTS["semantic"] * sem_risk
            + WEIGHTS["injection"] * inj_conf,
            4,
        )

        if final_risk >= THRESHOLDS["block"]:
            decision, icon = "BLOCK", "🚫"
        elif final_risk >= THRESHOLDS["flag"]:
            decision, icon = "FLAG", "⚠️"
        else:
            decision, icon = "SAFE", "✅"

        self._logger.info(
            f"final_risk={final_risk} → {decision} "
            f"(nn={nn_score}, sem={sem_risk}, inj={inj_conf})"
        )

        return {
            "final_risk":    final_risk,
            "decision":      decision,
            "icon":          icon,
            "nn_score":      nn_score,
            "sem_risk":      sem_risk,
            "inj_conf":      inj_conf,
            "cat_scores":    p.get("cat_scores", {}),
            "triggered":     p.get("triggered", []),
            "dominant":      p.get("dominant", "none"),
            "inj_signals":   p.get("inj_signals", []),
            "length_anomaly": p.get("length_anomaly", False),
            "word_count":    p.get("word_count", 0),
            "model_used":    p.get("model_used", "unknown"),
            "weights":       WEIGHTS,
            "thresholds":    THRESHOLDS,
        }
