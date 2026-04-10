"""
ContextShield — Base Agent
All agents inherit from this class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import logging
import time

logger = logging.getLogger("contextshield.agents")


@dataclass
class AgentMessage:
    """Message passed between agents in the pipeline."""
    sender: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Standardised result returned by every agent."""
    agent_name: str
    success: bool
    data: Dict[str, Any]
    processing_time_ms: float
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Abstract base class for all ContextShield agents.

    Each agent has a single responsibility and communicates with other agents
    exclusively through AgentMessage / AgentResult objects, keeping coupling minimal.
    """

    def __init__(self, name: str):
        self.name = name
        self._logger = logging.getLogger(f"contextshield.agents.{name}")
        self._logger.info(f"[{self.name}] Initialised")

    def run(self, message: AgentMessage) -> AgentResult:
        """Entry point — wraps _process with timing and error handling."""
        start = time.perf_counter()
        try:
            self._logger.info(f"[{self.name}] Processing message from '{message.sender}'")
            data = self._process(message)
            elapsed = (time.perf_counter() - start) * 1000
            self._logger.info(f"[{self.name}] Done in {elapsed:.1f} ms")
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=data,
                processing_time_ms=round(elapsed, 2),
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            self._logger.error(f"[{self.name}] Error: {exc}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                processing_time_ms=round(elapsed, 2),
                error=str(exc),
            )

    @abstractmethod
    def _process(self, message: AgentMessage) -> Dict[str, Any]:
        """Override in each concrete agent."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
