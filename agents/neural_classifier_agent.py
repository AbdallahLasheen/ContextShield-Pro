"""
ContextShield — Agent 3: Neural Classifier Agent

Responsibility:
    Encode the input prompt with SentenceTransformer (all-MiniLM-L6-v2) and
    run it through the trained TensorFlow neural network to produce a
    continuous risk probability in [0, 1].

Input payload:  { "text": str, "sem_risk": float, "inj_conf": float }
Output data:    { "nn_score": float, "model_used": str }
"""

import random
import numpy as np
from .base_agent import BaseAgent, AgentMessage

_MODEL = None
_ENCODER = None
_LOAD_ERROR = None


def _lazy_load():
    """Load heavy ML libraries only on first use."""
    global _MODEL, _ENCODER, _LOAD_ERROR
    if _MODEL is not None or _LOAD_ERROR is not None:
        return
    try:
        import tensorflow as tf
        from sentence_transformers import SentenceTransformer
        import os

        model_path = os.path.join(os.path.dirname(__file__), "..", "contextshield_model.h5")
        _ENCODER = SentenceTransformer("all-MiniLM-L6-v2")
        _MODEL = tf.keras.models.load_model(model_path)
    except Exception as exc:
        _LOAD_ERROR = str(exc)


class NeuralClassifierAgent(BaseAgent):
    """
    Agent 3 — Neural Classifier

    Uses a 4-layer dense neural network (512→256→128→1 sigmoid) trained on
    ~5 000 labelled prompts. Falls back to a weighted heuristic if the model
    cannot be loaded.
    """

    def __init__(self):
        super().__init__("NeuralClassifierAgent")
        _lazy_load()
        if _LOAD_ERROR:
            self._logger.warning(f"Model load failed — using heuristic fallback. Error: {_LOAD_ERROR}")
        else:
            self._logger.info("TF model and SentenceTransformer loaded successfully")

    def _process(self, message: AgentMessage) -> dict:
        text: str = message.payload["text"]
        sem_risk: float = message.payload.get("sem_risk", 0.0)
        inj_conf: float = message.payload.get("inj_conf", 0.0)

        if _MODEL is None or _ENCODER is None:
            # Heuristic fallback
            base = sem_risk * 0.6 + inj_conf * 0.4
            rng = random.Random(hash(text) % (2 ** 31))
            noise = rng.gauss(0, 0.04)
            score = round(min(max(base + noise, 0.0), 1.0), 4)
            return {"nn_score": score, "model_used": "heuristic_fallback"}

        try:
            embedding = _ENCODER.encode(text, convert_to_numpy=True, normalize_embeddings=True)
            if embedding.ndim == 1:
                embedding = np.expand_dims(embedding, axis=0)
            prediction = _MODEL.predict(embedding, verbose=0)
            score = round(float(np.clip(prediction[0][0], 0.0, 1.0)), 4)
            return {"nn_score": score, "model_used": "contextshield_nn_v2"}
        except Exception as exc:
            self._logger.error(f"Inference error: {exc}")
            base = sem_risk * 0.6 + inj_conf * 0.4
            rng = random.Random(hash(text) % (2 ** 31))
            score = round(min(max(base + rng.gauss(0, 0.04), 0.0), 1.0), 4)
            return {"nn_score": score, "model_used": "heuristic_fallback"}
