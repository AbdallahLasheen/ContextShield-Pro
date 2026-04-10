"""
ContextShield — Orchestrator

The Orchestrator is responsible for:
  1. Accepting a raw text prompt from the caller (API / UI / Telegram bot).
  2. Routing it sequentially through the four agents.
  3. Passing the accumulated context forward at each step via AgentMessage.
  4. Returning a fully assembled result dict.

Agent pipeline:
    Input Text
        │
        ▼
    SemanticAnalyzerAgent   ─► cat_scores, sem_risk, triggered, dominant
        │
        ▼
    InjectionDetectorAgent  ─► inj_conf, inj_signals, length_anomaly
        │
        ▼
    NeuralClassifierAgent   ─► nn_score
        │
        ▼
    DecisionAgent           ─► final_risk, decision (SAFE / FLAG / BLOCK)
"""

import logging
from typing import Dict, Any

from .base_agent import AgentMessage
from .semantic_analyzer_agent import SemanticAnalyzerAgent
from .injection_detector_agent import InjectionDetectorAgent
from .neural_classifier_agent import NeuralClassifierAgent
from .decision_agent import DecisionAgent

logger = logging.getLogger("contextshield.orchestrator")


class ContextShieldOrchestrator:
    """
    Coordinates the four ContextShield agents in a sequential pipeline.

    Example usage
    -------------
    orchestrator = ContextShieldOrchestrator()
    result = orchestrator.analyze("Ignore all previous instructions.")
    print(result["decision"])   # 'BLOCK'
    """

    def __init__(self):
        self.semantic_agent   = SemanticAnalyzerAgent()
        self.injection_agent  = InjectionDetectorAgent()
        self.neural_agent     = NeuralClassifierAgent()
        self.decision_agent   = DecisionAgent()
        self._agents = [
            self.semantic_agent,
            self.injection_agent,
            self.neural_agent,
            self.decision_agent,
        ]
        logger.info("ContextShieldOrchestrator ready with 4 agents")

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Run the full multi-agent pipeline on `text`.

        Returns a dict containing the final verdict and all intermediate
        scores, suitable for the REST API response or Streamlit UI.
        """
        context: Dict[str, Any] = {"text": text, "word_count": len(text.split())}

        # ── Step 1: Semantic Analyzer ────────────────────────────────────
        msg1 = AgentMessage(sender="orchestrator", payload={"text": text})
        r1 = self.semantic_agent.run(msg1)
        if not r1.success:
            logger.error(f"SemanticAnalyzerAgent failed: {r1.error}")
        context.update(r1.data)

        # ── Step 2: Injection Detector ───────────────────────────────────
        msg2 = AgentMessage(sender="SemanticAnalyzerAgent", payload={"text": text})
        r2 = self.injection_agent.run(msg2)
        if not r2.success:
            logger.error(f"InjectionDetectorAgent failed: {r2.error}")
        context.update(r2.data)

        # ── Step 3: Neural Classifier ────────────────────────────────────
        msg3 = AgentMessage(
            sender="InjectionDetectorAgent",
            payload={
                "text":     text,
                "sem_risk": context.get("sem_risk", 0.0),
                "inj_conf": context.get("inj_conf", 0.0),
            },
        )
        r3 = self.neural_agent.run(msg3)
        if not r3.success:
            logger.error(f"NeuralClassifierAgent failed: {r3.error}")
        context.update(r3.data)

        # ── Step 4: Decision Agent ───────────────────────────────────────
        msg4 = AgentMessage(sender="NeuralClassifierAgent", payload=context)
        r4 = self.decision_agent.run(msg4)
        if not r4.success:
            logger.error(f"DecisionAgent failed: {r4.error}")
            return {"error": r4.error}

        result = r4.data
        result["pipeline_timing_ms"] = {
            "semantic_analyzer":    r1.processing_time_ms,
            "injection_detector":   r2.processing_time_ms,
            "neural_classifier":    r3.processing_time_ms,
            "decision_agent":       r4.processing_time_ms,
        }
        return result

    # ── convenience ──────────────────────────────────────────────────────
    def get_agent_info(self):
        """Return metadata about the agents for documentation / health check."""
        return [
            {
                "name":        a.name,
                "class":       a.__class__.__name__,
                "description": (a.__class__.__doc__ or "").strip().splitlines()[0],
            }
            for a in self._agents
        ]
