"""Bridge between the Streamlit app and the C++ core (plan §4, §5, §45).

The C++ binary (``build/ame_core_app``) owns the Skip List and Splay Tree.
This module communicates with it via a persistent subprocess: one text command
per stdin line, one JSON object per stdout line.

Commands: load, search, access, splay_state, skiplist_state, quit.

Usage in Streamlit pages:
    from services.core_bridge import get_bridge, SearchResult, AccessResult

    bridge = get_bridge()          # returns None if binary is not built yet
    if bridge is None:
        st.error("C++ core not available — see instructions")
        st.stop()
    result = bridge.register_access(track_id)
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Paths resolved relative to this file so the module works from any CWD.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BINARY = _REPO_ROOT / "build" / "ame_core_app"
CSV    = _REPO_ROOT / "data" / "processed" / "tracks_processed.csv"


# ── typed result objects ──────────────────────────────────────────────────────

@dataclass
class SearchResult:
    track_id: int
    distance: float


@dataclass
class SearchMetrics:
    total_tracks: int
    candidates: int
    skiplist_comparisons: int
    skiplist_ms: float
    similarity_ms: float
    total_ms: float


@dataclass
class AccessResult:
    track_id: int
    step: str          # "Zig", "ZigZig", "ZigZag", or "None"
    depth_before: int
    depth_after: int
    play_count: int
    rotations: int
    comparisons: int
    root_id: int
    height: int
    tree_before: str
    tree_after: str


@dataclass
class SplayState:
    root_id: int
    height: int
    size: int
    tree_ascii: str


@dataclass
class SkipListState:
    size: int
    comparisons: int
    insertions: int
    searches: int


# ── CoreBridge class ──────────────────────────────────────────────────────────

class CoreBridge:
    """Manages a single long-lived C++ subprocess for the Streamlit session."""

    def __init__(self) -> None:
        if not BINARY.exists():
            raise FileNotFoundError(
                f"C++ binary not found: {BINARY}\n"
                "Build with:  cmake -S . -B build && cmake --build build"
            )

        self._proc = subprocess.Popen(
            [str(BINARY)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # line-buffered
        )

        self._loaded = False
        self._track_count = 0

        if CSV.exists():
            resp = self._cmd(f"load {CSV}")
            if resp.get("status") == "ok":
                self._loaded = True
                self._track_count = resp.get("loaded", 0)

    # ── public interface ──────────────────────────────────────────────────────

    @property
    def is_loaded(self) -> bool:
        """True when the dataset CSV was found and loaded into the index."""
        return self._loaded

    @property
    def track_count(self) -> int:
        return self._track_count

    def register_access(self, track_id: int) -> AccessResult:
        """Register a playback event and return splay metrics + tree snapshots."""
        resp = self._cmd(f"access {track_id}")
        self._check(resp)
        return AccessResult(
            track_id    = resp["track_id"],
            step        = resp["step"],
            depth_before= resp["depth_before"],
            depth_after = resp["depth_after"],
            play_count  = resp["play_count"],
            rotations   = resp["rotations"],
            comparisons = resp["comparisons"],
            root_id     = resp["root_id"],
            height      = resp["height"],
            tree_before = resp["tree_before"],
            tree_after  = resp["tree_after"],
        )

    def find_similar(
        self,
        track_id: int,
        num_candidates: int = 500,
        top_k: int = 10,
    ) -> tuple[list[SearchResult], SearchMetrics]:
        """Search for the top-k tracks most similar to track_id.

        Raises RuntimeError if the dataset is not loaded.
        """
        if not self._loaded:
            raise RuntimeError(
                "Dataset not loaded. Provide data/processed/tracks_processed.csv "
                "and restart the app."
            )
        resp = self._cmd(f"search {track_id} {num_candidates} {top_k}")
        self._check(resp)

        results = [
            SearchResult(r["track_id"], r["distance"])
            for r in resp.get("results", [])
        ]
        m = resp.get("metrics", {})
        metrics = SearchMetrics(
            total_tracks         = m.get("total_tracks", 0),
            candidates           = m.get("candidates", 0),
            skiplist_comparisons = m.get("skiplist_comparisons", 0),
            skiplist_ms          = m.get("skiplist_ms", 0.0),
            similarity_ms        = m.get("similarity_ms", 0.0),
            total_ms             = m.get("total_ms", 0.0),
        )
        return results, metrics

    def get_splay_state(self) -> SplayState:
        resp = self._cmd("splay_state")
        self._check(resp)
        return SplayState(
            root_id   = resp["root_id"],
            height    = resp["height"],
            size      = resp["size"],
            tree_ascii= resp["tree_ascii"],
        )

    def get_skiplist_state(self) -> SkipListState:
        resp = self._cmd("skiplist_state")
        self._check(resp)
        return SkipListState(
            size        = resp["size"],
            comparisons = resp["comparisons"],
            insertions  = resp["insertions"],
            searches    = resp["searches"],
        )

    def close(self) -> None:
        """Gracefully shut down the subprocess."""
        try:
            self._cmd("quit")
        except Exception:
            pass
        try:
            self._proc.terminate()
        except Exception:
            pass

    # ── internal helpers ──────────────────────────────────────────────────────

    def _cmd(self, line: str) -> dict:
        """Send one command line and return the parsed JSON response."""
        assert self._proc.stdin and self._proc.stdout
        self._proc.stdin.write(line + "\n")
        self._proc.stdin.flush()
        raw = self._proc.stdout.readline().strip()
        if not raw:
            raise RuntimeError("C++ bridge produced no response (process may have crashed)")
        return json.loads(raw)

    @staticmethod
    def _check(resp: dict) -> None:
        if resp.get("status") != "ok":
            raise RuntimeError(resp.get("message", "Unknown C++ core error"))


# ── Streamlit session-scoped factory ─────────────────────────────────────────

def get_bridge() -> Optional[CoreBridge]:
    """Return the session-scoped CoreBridge, or None if unavailable.

    Stores the instance in ``st.session_state`` so it survives Streamlit's
    per-interaction re-runs. On failure stores the error message in
    ``st.session_state.bridge_error`` for the UI to display.

    Safe to call multiple times per session — only initialises once.
    """
    # Import here to avoid making streamlit a hard dependency of this module.
    import streamlit as st

    if "bridge" not in st.session_state:
        try:
            st.session_state.bridge = CoreBridge()
            st.session_state.bridge_error = None
        except Exception as exc:
            st.session_state.bridge = None
            st.session_state.bridge_error = str(exc)

    return st.session_state.bridge  # type: ignore[return-value]
