"""Small synthetic fixture with the same multi-index CSV layout as official FMA."""
from pathlib import Path
import numpy as np
import pandas as pd


def make_fma(root: Path) -> tuple[Path, Path]:
    metadata = root / "kaggle" / "fma_metadata"
    audio = root / "kaggle" / "fma_medium" / "fma_medium"
    metadata.mkdir(parents=True)
    ids = [2, 3, 4, 5, 6, 7]
    tracks = pd.DataFrame([
        ["small", 'Canção, "A"\nsegunda linha', "Artista Á", "Rock"],
        ["medium", "Faixa B", "Artista B", "Jazz"],
        ["medium", "Faixa C", "Artista C", "Rock"],
        ["large", "Não incluir", "Artista D", "Folk"],
        ["medium", "Feature inválida", "Artista E", "Jazz"],
        ["medium", "Sem features", "Artista F", "Rock"],
    ], index=pd.Index(ids, name="track_id"), columns=pd.MultiIndex.from_tuples([
        ("set", "subset"), ("track", "title"), ("artist", "name"), ("track", "genre_top")
    ]))
    tracks.to_csv(metadata / "tracks.csv")
    groups = [("rmse", 1), ("zcr", 1), ("spectral_centroid", 1),
              ("spectral_bandwidth", 1), ("spectral_rolloff", 1),
              ("mfcc", 20), ("chroma_cqt", 12), ("spectral_contrast", 7)]
    columns = pd.MultiIndex.from_tuples([(group, "mean", f"{i:02d}")
              for group, count in groups for i in range(count, 0, -1)])
    values = np.arange(5 * 44, dtype=float).reshape(5, 44)
    values[4, 0] = np.inf
    features = pd.DataFrame(values, index=pd.Index(ids[:5], name="track_id"), columns=columns)
    features.to_csv(metadata / "features.csv")
    pd.DataFrame({"title": ["Rock", "Jazz"], "parent": [0, 0]},
                 index=pd.Index([1, 2], name="genre_id")).to_csv(metadata / "genres.csv")
    for tid in ids:
        if tid == 5:
            continue
        path = audio / f"{tid:06d}"[:3] / f"{tid:06d}.mp3"
        path.parent.mkdir(parents=True, exist_ok=True)
        # This checks file discovery/player wiring, not MP3 decoding.
        path.write_bytes(b"ID3-test-fixture")
    return metadata, audio
