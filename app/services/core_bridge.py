"""Bridge between Music Explorer, Structures Lab and the C++ core.

The C++ binary (``build/ame_core_app``) owns the Skip List and Splay Tree.
This module communicates with it via a persistent subprocess: one text command
per stdin line, one JSON object per stdout line.

Commands: load, search, track, skiplist_state, lab_skip, lab_splay, quit.

Usage in Streamlit pages:
    from services.core_bridge import get_bridge

    bridge = get_bridge()          # returns None if binary is not built yet
    if bridge is None:
        st.error("C++ core not available — see instructions")
        st.stop()
    results, metrics = bridge.find_similar(track_id)
"""

from __future__ import annotations

import json
import os
import selectors
import threading
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Paths resolved relative to this file so the module works from any CWD.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BINARY = Path(os.environ.get("AME_CORE_BINARY", _REPO_ROOT / "build" / "ame_core_app"))
from .dataset import PROCESSED_CSV as CSV


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
    initial_candidates: int = 0
    pruned: int = 0
    visited: int = 0
    exact: bool = False
    recall: float = -1
    brute_force_ms: float = 0
    acoustic_key: str = ""


@dataclass
class SkipListState:
    size: int
    comparisons: int
    insertions: int
    searches: int


# ── CoreBridge class ──────────────────────────────────────────────────────────

class CoreBridge:
    """Manages a single long-lived C++ subprocess for the Streamlit session."""

    def __init__(self, binary: Path = BINARY, csv_path: Path = CSV) -> None:
        self._lock = threading.Lock()
        if not binary.exists():
            raise FileNotFoundError(
                f"C++ binary not found: {binary}\n"
                "Build with:  cmake -S . -B build && cmake --build build"
            )

        self._proc = subprocess.Popen(
            [str(binary)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,  # line-buffered
        )

        self._loaded = False
        self._track_count = 0

        if csv_path.exists():
            try:
                resp = self._cmd(f"load {csv_path.resolve()}")
                self._check(resp)
                self._loaded = True
                self._track_count = resp["loaded"]
            except Exception:
                self.close()
                raise

    # ── public interface ──────────────────────────────────────────────────────

    @property
    def is_loaded(self) -> bool:
        """True when the dataset CSV was found and loaded into the index."""
        return self._loaded

    @property
    def track_count(self) -> int:
        return self._track_count

    def find_similar(
        self,
        track_id: int,
        num_candidates: int = 500,
        top_k: int = 10,
        exact: bool = True,
        evaluate: bool = False,
    ) -> tuple[list[SearchResult], SearchMetrics]:
        """Search for the top-k tracks most similar to track_id.

        Raises RuntimeError if the dataset is not loaded.
        """
        if not self._loaded:
            raise RuntimeError(
                "Dataset not loaded. Provide data/processed/tracks_processed.csv "
                "and restart the app."
            )
        resp = self._cmd(f"search {track_id} {num_candidates} {top_k} {'exact' if exact else 'approx'} {int(evaluate)}")
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
            initial_candidates=m.get("initial_candidates", 0),
            pruned=m.get("pruned", 0), visited=m.get("visited", 0),
            exact=m.get("exact", False), recall=m.get("recall", -1),
            brute_force_ms=m.get("brute_force_ms", 0), acoustic_key=m.get("acoustic_key", ""),
        )
        return results, metrics

    def get_skiplist_state(self) -> SkipListState:
        resp = self._cmd("skiplist_state")
        self._check(resp)
        return SkipListState(
            size        = resp["size"],
            comparisons = resp["comparisons"],
            insertions  = resp["insertions"],
            searches    = resp["searches"],
        )

    def track_key(self, track_id: int) -> str:
        response = self._cmd(f"track {track_id}")
        self._check(response)
        return response["acoustic_key"]

    def lab_skip(self, operation: str = "state", key: int = 0, track_id: int = 1,
                 new_key: int = 0) -> dict:
        if operation not in {"state", "insert", "remove", "search", "update", "traverse", "reset"}:
            raise ValueError("Unknown operation")
        command = f"lab_skip {operation}"
        if operation in {"insert", "remove", "search", "update"}:
            command += f" {key}"
        if operation in {"insert", "remove", "update"}:
            command += f" {track_id}"
        if operation == "update":
            command += f" {new_key}"
        response = self._cmd(command)
        self._check(response)
        return response

    def lab_splay(self, operation: str = "state", track_id: int = 1) -> dict:
        if operation not in {"state", "insert", "remove", "search", "access", "reset"}:
            raise ValueError("Unknown operation")
        command = f"lab_splay {operation}"
        if operation not in {"state", "reset"}:
            command += f" {track_id}"
        response = self._cmd(command)
        self._check(response)
        return response

    @property
    def alive(self) -> bool:
        return self._proc.poll() is None

    def close(self) -> None:
        try:
            if self.alive:
                self._cmd("quit", timeout=2)
            self._proc.wait(timeout=2)
        except Exception:
            self._proc.kill()
            self._proc.wait()
        finally:
            for stream in (self._proc.stdin, self._proc.stdout, self._proc.stderr):
                if stream:
                    stream.close()

    def _cmd(self, line: str, timeout: float = 30) -> dict:
        if "\n" in line or "\r" in line:
            raise ValueError("Commands and paths must not contain line breaks")
        with self._lock:
            if not self.alive:
                raise RuntimeError("C++ core process is no longer running")
            assert self._proc.stdin and self._proc.stdout
            self._proc.stdin.write(line + "\n")
            self._proc.stdin.flush()
            with selectors.DefaultSelector() as selector:
                selector.register(self._proc.stdout, selectors.EVENT_READ)
                if not selector.select(timeout):
                    self._proc.kill()
                    raise RuntimeError("C++ core timed out; reload the page to restart it")
            raw = self._proc.stdout.readline().strip()
            if not raw:
                raise RuntimeError("C++ bridge produced no response")
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

    stat = CSV.stat() if CSV.is_file() else None
    binary_stat = BINARY.stat() if BINARY.is_file() else None
    signature = ((stat.st_mtime_ns, stat.st_size) if stat else None,
                 (binary_stat.st_mtime_ns, binary_stat.st_size) if binary_stat else None)
    current = st.session_state.get("bridge")
    if current is None or not current.alive or st.session_state.get("dataset_signature") != signature:
        previous = st.session_state.get("bridge")
        if previous is not None:
            previous.close()
        # Search results and laboratory snapshots belong to the previous core.
        for key in list(st.session_state):
            if key.startswith(("search_", "sl_", "sp_")):
                del st.session_state[key]
        st.session_state.dataset_signature = signature
        try:
            st.session_state.bridge = CoreBridge()
            st.session_state.bridge_error = None
        except Exception as exc:
            st.session_state.bridge = None
            st.session_state.bridge_error = str(exc)

    return st.session_state.bridge  # type: ignore[return-value]
