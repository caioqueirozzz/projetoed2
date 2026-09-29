"""Import FMA Medium metadata/audio and produce the validated C++ dataset.

python preprocessing/build_dataset.py --source /path/to/extracted/kaggle
python preprocessing/build_dataset.py --import-zip /path/to/archive.zip
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from zipfile import BadZipFile

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_features import handle_missing, select_features
from import_fma import audio_dir, import_zip, metadata_dir
from load_fma import RAW_DIR, load_features, load_genres, load_tracks
from normalize import min_max, save_params

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def build(source: Path = RAW_DIR, output_dir: Path = PROCESSED_DIR,
          audio: Path | None = None, require_audio: bool = False) -> dict:
    source = source.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    metadata = metadata_dir(source)
    audio_root = audio_dir(source, audio)
    print(f"[build] metadata: {metadata}\n[build] audio: {audio_root}")

    tracks = load_tracks(metadata)
    raw_features = load_features(metadata, tracks.index)
    selected = select_features(raw_features)
    clean = handle_missing(selected)
    normalized, params = min_max(clean)
    if not np.isfinite(normalized.to_numpy()).all():
        raise ValueError("Normalization produced non-finite values")
    normalized = normalized.clip(0.0, 1.0)
    result = tracks.join(normalized, how="inner").sort_index()
    if result.empty:
        raise ValueError("No usable tracks remain after joining metadata and features")

    # Local absolute paths support datasets kept on another disk without
    # copying 22 GiB into this repository. The UI can override the audio root.
    paths = [audio_root / f"{tid:06d}"[:3] / f"{tid:06d}.mp3" for tid in result.index]
    result["audio_path"] = [str(p) for p in paths]
    missing_audio = [int(tid) for tid, path in zip(result.index, paths)
                     if not path.is_file() or path.stat().st_size == 0]
    if require_audio and missing_audio:
        raise ValueError(
            f"Audio missing/empty for {len(missing_audio):,} tracks under {audio_root}. "
            "Extract fma_medium or correct --audio-dir. No processed files were replaced."
        )
    genres = load_genres(metadata)
    missing_features = tracks.index.difference(raw_features.index).tolist()
    invalid_features = selected.index.difference(clean.index).tolist()
    report = {
        "dataset": "FMA Medium",
        "source_url": "https://www.kaggle.com/datasets/imsparsh/fma-free-music-archive-small-medium",
        "official_url": "https://github.com/mdeff/fma",
        "subset_labels": ["small", "medium"],
        "metadata_dir": str(metadata), "audio_dir": str(audio_root),
        "metadata_tracks": len(tracks), "processed_tracks": len(result),
        "feature_count": len(normalized.columns), "feature_columns": list(normalized.columns),
        "missing_feature_ids": missing_features, "invalid_feature_ids": invalid_features,
        "genre_counts": {str(k): int(v) for k, v in result.genre.value_counts().items()},
        "genre_catalog_loaded": genres is not None,
        "audio_available": len(result) - len(missing_audio),
        "audio_missing": len(missing_audio), "missing_audio_ids": missing_audio,
    }

    # Validate everything before publishing; a bad input must not replace a
    # working CSV. Write staging files on the same filesystem for atomic rename.
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".fma-", dir=output_dir) as tmp:
        staging = Path(tmp)
        result.to_csv(staging / "tracks_processed.csv", lineterminator="\n")
        save_params(params, staging / "normalization_params.json")
        (staging / "dataset_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        if genres is not None:
            genres.to_csv(staging / "genres.csv")
        for name in ("normalization_params.json", "genres.csv", "dataset_report.json", "tracks_processed.csv"):
            if (staging / name).exists():
                (staging / name).replace(output_dir / name)
        if genres is None:
            (output_dir / "genres.csv").unlink(missing_ok=True)
    print(f"[build] {len(result):,} tracks × 44 features written to {output_dir}")
    print(f"[build] audio present: {report['audio_available']:,}; missing/empty: {len(missing_audio):,}")
    if missing_audio:
        print("[build] Missing audio does not prevent search. Extract Medium audio and rerun for playback.")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=RAW_DIR,
                        help="Extracted Kaggle/FMA folder (default: data/raw)")
    parser.add_argument("--import-zip", type=Path, action="append", default=[],
                        help="Import a Kaggle, metadata or Medium ZIP into --source; repeatable")
    parser.add_argument("--audio-dir", type=Path,
                        help="Folder containing 000/, 001/, ... (may be on another disk)")
    parser.add_argument("--output-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--require-audio", action="store_true",
                        help="Fail if any retained track has a missing/empty MP3")
    args = parser.parse_args()
    try:
        for archive in args.import_zip:
            import_zip(archive.expanduser().resolve(), args.source.expanduser().resolve())
        build(args.source, args.output_dir, args.audio_dir, args.require_audio)
    except BadZipFile:
        parser.exit(1, "Dataset preparation failed: invalid or incomplete ZIP. Wait for the download to finish.\n")
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Dataset preparation failed: {exc}\n")


if __name__ == "__main__":
    main()
