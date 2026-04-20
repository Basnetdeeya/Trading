"""Select the best available agent backend."""
from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

from .base import AgentBackend
from .heuristic import HeuristicAgent

logger = get_logger(__name__)


def build_agent(settings: Settings | None = None) -> AgentBackend:
    s = settings or get_settings()
    if s.anthropic_api_key:
        try:
            from .llm import ClaudeAgent
            logger.info("using Claude agent (%s)", s.anthropic_model)
            return ClaudeAgent(s.anthropic_api_key, s.anthropic_model)
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to init Claude: %s", exc)
    if s.openai_api_key:
        try:
            from .llm import OpenAIAgent
            logger.info("using OpenAI agent (%s)", s.openai_model)
            return OpenAIAgent(s.openai_api_key, s.openai_model)
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to init OpenAI: %s", exc)
    logger.info("no LLM key configured — using heuristic agent")
    return HeuristicAgent()
