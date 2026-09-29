"""Locate extracted FMA files or selectively import Kaggle/official ZIPs.

Only metadata tables and Medium MP3s are extracted. Archive paths never become
output paths directly, so unrelated files and traversal entries are ignored.
"""
from __future__ import annotations

import shutil
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

TABLES = {"tracks.csv", "features.csv", "genres.csv"}


def import_zip(archive: Path, raw_dir: Path) -> int:
    count = 0
    with ZipFile(archive) as source:
        for entry in source.infolist():
            parts = PurePosixPath(entry.filename).parts
            if entry.is_dir() or "__MACOSX" in parts or ".." in parts:
                continue
            name = parts[-1]
            if name in TABLES:
                relative = Path("fma_metadata") / name
            elif "fma_medium" in parts and name.endswith(".mp3"):
                # Kaggle mirrors sometimes repeat fma_medium/fma_medium/.
                pos = max(i for i, part in enumerate(parts) if part == "fma_medium")
                tail = parts[pos + 1:]
                if (len(tail) != 2 or len(tail[0]) != 3 or not tail[0].isdigit()
                        or len(name) != 10 or not name[:6].isdigit()
                        or tail[0] != name[:3]):
                    continue
                relative = Path("fma_medium", *tail)
            else:
                continue
            dest = raw_dir / relative
            if dest.exists():
                if dest.stat().st_size != entry.file_size:
                    raise FileExistsError(f"Different file already exists: {dest}")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                temp = dest.with_suffix(dest.suffix + ".part")
                try:
                    with source.open(entry) as src, temp.open("wb") as dst:
                        shutil.copyfileobj(src, dst, length=1024 * 1024)
                    temp.replace(dest)
                finally:
                    temp.unlink(missing_ok=True)
            count += 1
            if count % 1000 == 0:
                print(f"[import] {count:,} files imported/reused", flush=True)
    if count == 0:
        raise ValueError(f"No FMA metadata or Medium MP3s found in {archive}")
    print(f"[import] {archive.name}: {count:,} files imported/reused")
    return count


def metadata_dir(source: Path) -> Path:
    """Accept direct CSVs, official fma_metadata/, or nested Kaggle folders."""
    source = source.expanduser().resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"Dataset folder not found: {source}")
    for folder in (source, source / "fma_metadata"):
        if (folder / "tracks.csv").is_file() and (folder / "features.csv").is_file():
            return folder
    matches = sorted({p.parent for p in source.rglob("tracks.csv")
                      if (p.parent / "features.csv").is_file()})
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(
            f"tracks.csv and features.csv not found under {source}. "
            "Extract fma_metadata.zip or pass --import-zip /path/fma_metadata.zip."
        )
    raise ValueError("Multiple metadata folders found; use --source with the desired folder")


def audio_dir(source: Path, explicit: Path | None = None) -> Path:
    """Return the folder containing the 000/, 001/, ... audio directories."""
    if explicit is not None:
        folder = explicit.expanduser().resolve()
        if not folder.is_dir():
            raise FileNotFoundError(f"Audio folder not found: {folder}")
        return folder
    source = source.expanduser().resolve()
    candidates = {source / "fma_medium", source / "fma_medium" / "fma_medium"}
    if source.name == "fma_medium":
        candidates.add(source)
    candidates.update(p for p in source.rglob("fma_medium") if p.is_dir())
    matches = sorted(p for p in candidates if p.is_dir() and next(p.glob("[0-9][0-9][0-9]/*.mp3"), None))
    if len(matches) > 1:
        raise ValueError("Multiple Medium audio folders found; select one with --audio-dir")
    return matches[0] if matches else source / "fma_medium"
