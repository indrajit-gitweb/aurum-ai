import json
import re
from pydantic import BaseModel
from typing import Optional


class AgentSignal(BaseModel):
    agent_id: str
    agent_name: str
    signal: str  # "bullish", "bearish", "neutral"
    confidence: int  # 0-100
    reasoning: str
    key_points: list[str]  # 3-5 bullet points


class BaseAgent:
    agent_id: str = "base"
    agent_name: str = "Base Agent"

    def __init__(self, llm_router):
        self.llm = llm_router

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        raise NotImplementedError

    def _build_system_prompt(self) -> str:
        raise NotImplementedError

    def _parse_response(self, response: str, ticker: str) -> AgentSignal:
        """Parse JSON from LLM response, with fallback to text parsing."""
        # Try to extract JSON block from response
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response)
        if json_match:
            raw = json_match.group(1)
        else:
            # Try to find raw JSON object
            json_match = re.search(r"\{[\s\S]*\}", response)
            raw = json_match.group(0) if json_match else None

        if raw:
            try:
                parsed = json.loads(raw)
                signal = parsed.get("signal", "neutral").lower()
                if signal not in ("bullish", "bearish", "neutral"):
                    signal = "neutral"
                confidence = int(parsed.get("confidence", 50))
                confidence = max(0, min(100, confidence))
                reasoning = parsed.get("reasoning", response)
                key_points = parsed.get("key_points", [])
                if not isinstance(key_points, list):
                    key_points = [str(key_points)]
                key_points = key_points[:5]
                return AgentSignal(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    signal=signal,
                    confidence=confidence,
                    reasoning=reasoning,
                    key_points=key_points,
                )
            except (json.JSONDecodeError, ValueError, KeyError):
                pass

        # Fallback: derive signal from text
        lower = response.lower()
        if "bullish" in lower or "buy" in lower or "strong" in lower:
            signal = "bullish"
            confidence = 55
        elif "bearish" in lower or "sell" in lower or "avoid" in lower:
            signal = "bearish"
            confidence = 55
        else:
            signal = "neutral"
            confidence = 40

        return AgentSignal(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            signal=signal,
            confidence=confidence,
            reasoning=response,
            key_points=["See full reasoning above."],
        )
