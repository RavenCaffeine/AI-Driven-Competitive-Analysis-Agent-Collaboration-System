"""
Long-term Memory Storage (inspired by deerflow)

Provides persistent competitive intelligence memory across runs:
- Industry knowledge facts
- Previous analysis results
- Competitor historical data
- User preferences and context

Supports file-based storage with JSON, thread-safe caching.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("competitive_analysis.memory")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def create_empty_memory() -> Dict[str, Any]:
    """Create an empty memory structure following deerflow's schema."""
    return {
        "version": "1.0",
        "lastUpdated": utc_now_iso(),
        "industry_context": {
            "summary": "",
            "updatedAt": "",
        },
        "competitor_history": {},       # {competitor_name: [historical snapshots]}
        "analysis_patterns": {
            "summary": "",
            "updatedAt": "",
        },
        "facts": [],                    # [{fact, confidence, source, created_at}]
        "user_preferences": {
            "preferred_format": "markdown",
            "focus_areas": [],
        },
    }


class MemoryStorage:
    """
    File-based memory storage with thread-safe caching.

    Inspired by deerflow's FileMemoryStorage pattern.
    """

    def __init__(self, storage_path: str = ""):
        self.storage_path = storage_path
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_mtime: Optional[float] = None
        self._lock = threading.Lock()

    def _get_path(self) -> Path:
        if self.storage_path:
            return Path(self.storage_path)
        return Path("./outputs/memory/competitive_memory.json")

    def load(self) -> Dict[str, Any]:
        """Load memory with file modification time caching."""
        path = self._get_path()
        try:
            current_mtime = path.stat().st_mtime if path.exists() else None
        except OSError:
            current_mtime = None

        with self._lock:
            if self._cache is not None and self._cache_mtime == current_mtime:
                return self._cache

        if not path.exists():
            memory = create_empty_memory()
        else:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    memory = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load memory: %s", e)
                memory = create_empty_memory()

        with self._lock:
            self._cache = memory
            self._cache_mtime = current_mtime
        return memory

    def save(self, memory: Dict[str, Any]) -> bool:
        """Save memory with atomic write."""
        path = self._get_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            memory["lastUpdated"] = utc_now_iso()

            temp = path.with_suffix(f".{uuid.uuid4().hex[:8]}.tmp")
            with open(temp, "w", encoding="utf-8") as f:
                json.dump(memory, f, indent=2, ensure_ascii=False, default=str)
            temp.replace(path)

            with self._lock:
                self._cache = memory
                try:
                    self._cache_mtime = path.stat().st_mtime
                except OSError:
                    self._cache_mtime = None

            return True
        except OSError as e:
            logger.error("Failed to save memory: %s", e)
            return False

    def add_fact(self, fact: str, confidence: float = 0.8, source: str = "") -> None:
        """Add a new fact to memory."""
        memory = self.load()
        facts = memory.get("facts", [])

        # Deduplicate by checking similarity
        for existing in facts:
            if existing.get("fact", "").lower().strip() == fact.lower().strip():
                existing["confidence"] = max(existing.get("confidence", 0), confidence)
                existing["updated_at"] = utc_now_iso()
                self.save(memory)
                return

        facts.append({
            "fact_id": f"F{len(facts) + 1}",
            "fact": fact,
            "confidence": confidence,
            "source": source,
            "created_at": utc_now_iso(),
        })
        memory["facts"] = facts
        self.save(memory)

    def update_competitor_history(self, competitor: str, snapshot: Dict[str, Any]) -> None:
        """Store a historical snapshot for a competitor."""
        memory = self.load()
        history = memory.setdefault("competitor_history", {})
        history.setdefault(competitor, []).append({
            "timestamp": utc_now_iso(),
            "data": snapshot,
        })
        # Keep last 10 snapshots per competitor
        if len(history[competitor]) > 10:
            history[competitor] = history[competitor][-10:]
        self.save(memory)

    def get_relevant_context(self, query: str, competitors: List[str]) -> str:
        """Retrieve relevant memory context for a new analysis run."""
        memory = self.load()
        context_parts = []

        # Industry context
        industry = memory.get("industry_context", {}).get("summary", "")
        if industry:
            context_parts.append(f"Industry Context: {industry}")

        # Previous competitor data
        history = memory.get("competitor_history", {})
        for comp in competitors:
            if comp in history and history[comp]:
                latest = history[comp][-1]
                context_parts.append(
                    f"Previous data for {comp} (from {latest.get('timestamp', '?')}): "
                    f"{json.dumps(latest.get('data', {}), ensure_ascii=False)[:500]}"
                )

        # Relevant facts
        facts = memory.get("facts", [])
        relevant = [f for f in facts if any(c.lower() in f.get("fact", "").lower() for c in competitors)]
        if relevant:
            context_parts.append("Relevant Facts:\n" + "\n".join(
                f"- {f['fact']} (confidence: {f.get('confidence', '?')})" for f in relevant[:10]
            ))

        return "\n\n".join(context_parts) if context_parts else ""
