"""
VAYORA Session Memory — SAFE VERSION (V1 Compatible)
════════════════════════════════════════════════════
- Works WITH or WITHOUT Redis
- No crash in V1
- Stores city, AQI, history
"""

import json
import time
import os
from typing import Optional, Dict, List, Any

# ── Redis Setup (SAFE FALLBACK) ─────────────────────────

try:
    import redis as _redis_lib

    _rc = _redis_lib.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    _rc.ping()
    REDIS_OK = True
    print("✅ Redis connected (persistent memory enabled)")

except Exception:
    _rc = None
    REDIS_OK = False
    print("⚠️ Redis not available → using local memory (safe)")

# fallback memory
_local: Dict[str, Any] = {}

SESSION_TTL = 3600   # 1 hour
MAX_HISTORY = 10     # last 10 turns


# ── Internal Helpers ─────────────────────────────────────

def _key(session_id: str) -> str:
    return f"vayora:{session_id}"


def _load(session_id: str) -> Dict:
    k = _key(session_id)

    if REDIS_OK:
        raw = _rc.get(k)
        return json.loads(raw) if raw else {}

    return _local.get(k, {})


def _save(session_id: str, data: Dict):
    k = _key(session_id)

    if REDIS_OK:
        _rc.setex(k, SESSION_TTL, json.dumps(data))
    else:
        _local[k] = data


# ── PUBLIC FUNCTIONS (USE THESE) ─────────────────────────

def get_session_city(session_id: str) -> Optional[str]:
    return _load(session_id).get("last_city")


def get_last_aqi(session_id: str) -> Optional[Dict]:
    return _load(session_id).get("last_aqi")


def get_history(session_id: str) -> List[Dict]:
    return _load(session_id).get("history", [])


def get_context(session_id: str) -> str:
    s = _load(session_id)

    if not s:
        return "No previous context."

    parts = []

    if s.get("last_city"):
        parts.append(f"Last city: {s['last_city']}")

    if s.get("last_aqi"):
        a = s["last_aqi"]
        parts.append(f"AQI: {a.get('aqi')} ({a.get('category', '')})")

    if s.get("history"):
        recent = s["history"][-4:]
        lines = []
        for turn in recent:
            role = "User" if turn["role"] == "user" else "Bot"
            lines.append(f"{role}: {turn['content']}")
        parts.append("\n".join(lines))

    return "\n".join(parts)


def update_session(
    session_id: str,
    user_message: str,
    bot_reply: str,
    city: Optional[str] = None,
    aqi_data: Optional[Dict] = None,
):
    s = _load(session_id)

    # update city
    if city:
        s["last_city"] = city

    # update AQI
    if aqi_data:
        s["last_aqi"] = {
            "city": aqi_data.get("city"),
            "aqi": aqi_data.get("aqi"),
            "category": aqi_data.get("category", ""),
            "time": time.time()
        }

    # update history
    history = s.get("history", [])

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": bot_reply[:500]})

    if len(history) > MAX_HISTORY * 2:
        history = history[-(MAX_HISTORY * 2):]

    s["history"] = history

    _save(session_id, s)


def clear_session(session_id: str):
    k = _key(session_id)

    if REDIS_OK:
        _rc.delete(k)
    else:
        _local.pop(k, None)