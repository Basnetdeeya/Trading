"""LLM-backed agent. Wraps Anthropic Claude or OpenAI with a structured prompt,
and falls back to the heuristic agent on any error so the loop never stalls.
"""
from __future__ import annotations

import json
from typing import List, Optional

import pandas as pd

from app.core.logging import get_logger
from app.core.types import Signal

from .base import AgentBackend
from .features import compute_features
from .heuristic import HeuristicAgent

logger = get_logger(__name__)


_SYSTEM_PROMPT = """You are a cautious quantitative trading agent.
You will be given: (a) a market features dict, (b) a list of strategy signals.

Your job: decide BUY / SELL / HOLD for a single symbol, pick the single
best-fit strategy for the current regime, and assign a calibrated confidence.

Hard rules:
- You MUST reply with ONE compact JSON object, no prose, no markdown fences.
- Keys: side, confidence, chosen_strategy, regime, rationale.
- side ∈ {"BUY","SELL","HOLD"}; confidence ∈ [0,1].
- Prefer HOLD when signals disagree or volatility is extreme.
- Never claim certainty. Keep rationale under 200 characters.
"""


class ClaudeAgent(AgentBackend):
    name = "claude"

    def __init__(self, api_key: str, model: str = "claude-opus-4-7") -> None:
        from anthropic import AsyncAnthropic  # local import to keep optional
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self._fallback = HeuristicAgent()

    async def decide(self, symbol, asset_class, df, signals):
        payload = _build_payload(symbol, asset_class, df, signals)
        try:
            resp = await self.client.messages.create(
                model=self.model,
                max_tokens=400,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": json.dumps(payload)}],
            )
            text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
            return _parse_or_fallback(text, symbol, asset_class, df, signals, self._fallback)
        except Exception as exc:  # noqa: BLE001
            logger.warning("claude agent failed: %s — falling back to heuristic", exc)
            return await self._fallback.decide(symbol, asset_class, df, signals)


class OpenAIAgent(AgentBackend):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self._fallback = HeuristicAgent()

    async def decide(self, symbol, asset_class, df, signals):
        payload = _build_payload(symbol, asset_class, df, signals)
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload)},
                ],
            )
            text = resp.choices[0].message.content or ""
            return _parse_or_fallback(text, symbol, asset_class, df, signals, self._fallback)
        except Exception as exc:  # noqa: BLE001
            logger.warning("openai agent failed: %s — falling back to heuristic", exc)
            return await self._fallback.decide(symbol, asset_class, df, signals)


# ------------------------------------------------------------------ helpers
def _build_payload(symbol: str, asset_class: str, df: pd.DataFrame, signals: List[Signal]) -> dict:
    feats = compute_features(df, signals)
    return {
        "symbol": symbol,
        "asset_class": asset_class,
        "last_price": float(df["close"].iloc[-1]),
        "features": feats.__dict__,
        "signals": [
            {
                "strategy": s.strategy,
                "side": s.side.value,
                "confidence": round(s.confidence, 3),
                "rationale": s.rationale,
            }
            for s in signals
        ],
    }


def _parse_or_fallback(
    text: str,
    symbol: str,
    asset_class: str,
    df: pd.DataFrame,
    signals: List[Signal],
    fallback: AgentBackend,
) -> dict:
    try:
        data = json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
            except Exception:
                data = None
        else:
            data = None
    if not isinstance(data, dict) or data.get("side") not in {"BUY", "SELL", "HOLD"}:
        return _run_sync_fallback(fallback, symbol, asset_class, df, signals)
    # Clamp / sanitise
    conf = data.get("confidence", 0.0)
    try:
        conf = max(0.0, min(float(conf), 1.0))
    except Exception:
        conf = 0.0
    return {
        "side": data["side"],
        "confidence": conf,
        "chosen_strategy": str(data.get("chosen_strategy", "")),
        "regime": str(data.get("regime", "unknown")),
        "rationale": str(data.get("rationale", ""))[:400],
    }


def _run_sync_fallback(fallback, symbol, asset_class, df, signals) -> dict:
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        # The caller is inside an event loop already — but we are on the same
        # loop. Build the fallback result synchronously from features.
        from .features import compute_features
        feats = compute_features(df, signals)
        return {
            "side": "HOLD",
            "confidence": 0.1,
            "chosen_strategy": "",
            "regime": feats.regime,
            "rationale": "LLM returned unparseable output; holding",
        }
    return asyncio.run(fallback.decide(symbol, asset_class, df, signals))
