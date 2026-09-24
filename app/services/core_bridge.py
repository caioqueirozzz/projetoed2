"""Bridge between the Streamlit app and the C++ core (plan §4, §5).

The C++ binary (``build/ame_core_app``) owns the Skip List and Splay Tree; this
module is the Python-side interface the pages call. The transport (subprocess +
CSV/JSON, or a pybind11 extension) is a TODO decision — keep this API stable so
the pages don't care which one is used.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchResult:
    track_id: int
    similarity: float


@dataclass
class SearchMetrics:
    total_tracks: int
    candidates: int
    comparisons: int
    skiplist_ms: float
    similarity_ms: float
    total_ms: float


def find_similar(track_id: int, num_candidates: int = 500, top_k: int = 10):
    """Return (results, metrics) for the given query track.

    TODO: call the C++ core (Skip List candidates -> exact Top-K).
    """
    raise NotImplementedError("find_similar: wire up the C++ core bridge")


def register_access(track_id: int) -> None:
    """Register a playback/selection in the Splay Tree (plan §17, §45).

    TODO: forward to the C++ core and return the resulting splay metrics.
    """
    raise NotImplementedError("register_access: wire up the Splay Tree")
