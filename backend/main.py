"""
AURUM AI — FastAPI backend entry point.

Endpoints:
  GET  /api/health                 — liveness probe
  GET  /api/providers/status       — which LLM providers are configured
  POST /api/analyze/start          — validate request, check rate limit, issue session_id
  WS   /ws/analyze/{session_id}    — streaming analysis pipeline

Session-based rate limiting: 3 free analyses per unique session_id.
Users who supply their own API key bypass the limit.
"""

import asyncio
import logging
import os
import time
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AURUM AI",
    version="1.0.0",
    description="Luxury AI-powered stock analysis — multi-persona debate engine.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # BUG-10 fix: wildcard origin + credentials=True is invalid
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# In-memory session store
# ─────────────────────────────────────────────────────────────────────────────
# Maps session_id (str) → {"usage": int, "request": AnalysisRequest | None}
sessions: dict[str, dict] = {}

SESSION_FREE_LIMIT = int(os.getenv("SESSION_FREE_LIMIT", "3"))

# Pending analyses waiting for their WebSocket connection
_pending_analyses: dict[str, "AnalysisRequest"] = {}

_SESSION_TTL_SECONDS = 3600  # 1 hour


async def _cleanup_stale_sessions() -> None:
    """Background task: remove sessions and pending analyses older than TTL."""
    while True:
        await asyncio.sleep(300)  # run every 5 minutes
        now = time.time()
        # Clean pending analyses (stale if WebSocket never connected)
        stale_pending = [
            sid for sid, req in list(_pending_analyses.items())
            if hasattr(req, '_created_at') and now - req._created_at > 300
        ]
        for sid in stale_pending:
            _pending_analyses.pop(sid, None)
        # Clean sessions older than TTL
        stale_sessions = [
            sid for sid, data in list(sessions.items())
            if now - data.get('created_at', now) > _SESSION_TTL_SECONDS
        ]
        for sid in stale_sessions:
            sessions.pop(sid, None)
        if stale_sessions or stale_pending:
            logger.info(
                "Cleaned %d stale sessions, %d pending analyses.",
                len(stale_sessions),
                len(stale_pending),
            )


@app.on_event("startup")
async def startup_event() -> None:
    asyncio.create_task(_cleanup_stale_sessions())


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    """Parameters for a full stock analysis run."""

    ticker: str = Field(..., description="Stock ticker symbol, e.g. AAPL")
    start_date: str = Field(..., description="Price history start date YYYY-MM-DD")
    end_date: str = Field(..., description="Price history end date YYYY-MM-DD")
    personas: list[str] = Field(
        default=["buffett", "burry"],
        description="Persona IDs to include in the debate",
    )
    user_groq_key: Optional[str] = Field(None, description="User-supplied Groq API key")
    user_gemini_key: Optional[str] = Field(None, description="User-supplied Gemini API key")
    user_openrouter_key: Optional[str] = Field(None, description="User-supplied OpenRouter API key")
    session_id: Optional[str] = Field(None, description="Existing session ID for rate-limit tracking")

    @validator("ticker")
    def ticker_uppercase(cls, v: str) -> str:  # noqa: N805
        return v.upper().strip()

    @validator("personas")
    def personas_nonempty(cls, v: list[str]) -> list[str]:  # noqa: N805
        if not v:
            raise ValueError("At least one persona must be specified.")
        return v


class PersonaSignal(BaseModel):
    """Analysis signal emitted by a single investor persona."""

    agent: str
    signal: str = Field(..., description="bullish | bearish | neutral")
    confidence: int = Field(..., ge=0, le=100)
    reasoning: str


class FinalResult(BaseModel):
    """Aggregate result returned at the end of the analysis pipeline."""

    verdict: str = Field(
        ...,
        description="STRONG BUY | BUY | HOLD | SELL | STRONG SELL",
    )
    confidence: int = Field(..., ge=0, le=100)
    target_price: Optional[float] = None
    summary: str
    persona_signals: list[PersonaSignal] = Field(default_factory=list)
    bull_case: str
    bear_case: str
    risk_assessment: str
    key_metrics: dict = Field(default_factory=dict)


class AnalysisStartResponse(BaseModel):
    session_id: str
    message: str
    free_analyses_remaining: int


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _has_user_key(req: AnalysisRequest) -> bool:
    """Return True if the user provided at least one personal API key."""
    return bool(
        (req.user_groq_key and req.user_groq_key.strip())
        or (req.user_gemini_key and req.user_gemini_key.strip())
        or (req.user_openrouter_key and req.user_openrouter_key.strip())
    )


def _get_user_key_and_provider(req: AnalysisRequest) -> tuple[Optional[str], str]:
    """Extract the first available user-supplied key and its provider name."""
    if req.user_groq_key and req.user_groq_key.strip():
        return req.user_groq_key.strip(), "groq"
    if req.user_gemini_key and req.user_gemini_key.strip():
        return req.user_gemini_key.strip(), "gemini"
    if req.user_openrouter_key and req.user_openrouter_key.strip():
        return req.user_openrouter_key.strip(), "openrouter"
    return None, "groq"


# ─────────────────────────────────────────────────────────────────────────────
# HTTP routes
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health() -> dict:
    """Liveness probe — always returns 200 when the server is up."""
    return {"status": "online", "version": "1.0.0"}


@app.get("/api/providers/status")
async def provider_status() -> dict:
    """Return which LLM providers are configured (not the key values)."""
    return {
        "groq": bool(os.getenv("GROQ_API_KEY", "").strip()),
        "gemini": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "openrouter": bool(os.getenv("OPENROUTER_API_KEY", "").strip()),
    }


@app.post("/api/analyze/start", response_model=AnalysisStartResponse)
async def start_analysis(request: AnalysisRequest) -> AnalysisStartResponse:
    """Validate the analysis request and issue (or reuse) a session_id.

    Rate-limit logic:
    - Users with their own API key → unlimited.
    - Users without a key → SESSION_FREE_LIMIT free analyses per session_id.
    """
    # Determine or create session_id
    session_id = request.session_id or str(uuid.uuid4())

    if session_id not in sessions:
        sessions[session_id] = {"usage": 0, "created_at": time.time()}

    session = sessions[session_id]
    has_key = _has_user_key(request)

    if not has_key:
        if session["usage"] >= SESSION_FREE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Free analysis limit reached ({SESSION_FREE_LIMIT} per session). "
                    "Provide your own Groq, Gemini, or OpenRouter API key to continue."
                ),
            )

    # Bump usage counter (we count on start, before the WebSocket connects)
    if not has_key:
        session["usage"] += 1

    remaining = max(0, SESSION_FREE_LIMIT - session["usage"]) if not has_key else -1

    # Stash the request so the WS handler can retrieve it
    _pending_analyses[session_id] = request

    logger.info(
        "Analysis started: ticker=%s session=%s usage=%d",
        request.ticker,
        session_id,
        session["usage"],
    )

    return AnalysisStartResponse(
        session_id=session_id,
        message=f"Session ready. Connect to /ws/analyze/{session_id} to begin.",
        free_analyses_remaining=remaining,
    )


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket — streaming analysis pipeline
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/analyze/{session_id}")
async def analyze_websocket(websocket: WebSocket, session_id: str) -> None:
    """Accept a WebSocket and stream the full analysis pipeline to the client.

    Emits JSON events:
      {"type": "agent_start",     "agent": "...", "message": "..."}
      {"type": "agent_progress",  "agent": "...", "message": "..."}
      {"type": "agent_complete",  "agent": "...", "signal": "...",
                                  "confidence": 0-100, "reasoning": "..."}
      {"type": "debate_start"}
      {"type": "debate_message",  "side": "bull|bear", "message": "..."}
      {"type": "final_result",    ...FinalResult fields...}
      {"type": "error",           "message": "..."}
    """
    await websocket.accept()

    # Retrieve the request that was registered via POST /api/analyze/start
    request = _pending_analyses.pop(session_id, None)
    if request is None:
        await websocket.send_json(
            {
                "type": "error",
                "message": (
                    "Session not found or expired. "
                    "Call POST /api/analyze/start before opening the WebSocket."
                ),
            }
        )
        await websocket.close(code=4000)
        return

    try:
        from llm.router import LLMRouter
        from graph.trading_graph import TradingGraph

        llm_router = LLMRouter(
            user_groq_key=request.user_groq_key,
            user_gemini_key=request.user_gemini_key,
            user_openrouter_key=request.user_openrouter_key,
        )

        async def on_event(event: dict) -> None:
            """Forward graph events to the WebSocket client."""
            try:
                await websocket.send_json(event)
            except Exception:
                pass  # client may have disconnected

        graph = TradingGraph()
        # 4-minute hard timeout — prevents the WebSocket from hanging
        # indefinitely if an LLM provider or data source stops responding.
        result = await asyncio.wait_for(
            graph.run(
                ticker=request.ticker,
                date_range={"start": request.start_date, "end": request.end_date},
                personas=request.personas,
                llm_router=llm_router,
                on_event=on_event,
            ),
            timeout=240.0,
        )

        # Emit the final result — use result.dict() which handles all serialisation
        final_payload = result.dict()
        final_payload["type"] = "final_result"
        await websocket.send_json(final_payload)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: session=%s", session_id)
    except asyncio.TimeoutError:
        logger.error("Analysis timed out after 240s: session=%s", session_id)
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": (
                        "Analysis timed out (4 minutes). "
                        "Try selecting fewer personas or providing your own API key "
                        "for faster inference."
                    ),
                }
            )
        except Exception:
            pass
    except Exception as exc:
        logger.exception("Analysis pipeline error for session %s: %s", session_id, exc)
        try:
            await websocket.send_json(
                {"type": "error", "message": f"Analysis failed: {exc}"}
            )
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
