"""
utils/storage.py
Thin wrapper that writes/reads Parquet when pyarrow is available,
and falls back to gzipped CSV otherwise.
"""

from pathlib import Path
import pandas as pd

try:
    import pyarrow  # noqa: F401
    _PARQUET = True
except ImportError:
    _PARQUET = False


def write(df: pd.DataFrame, path: Path) -> Path:
    """Write df to path; adjusts extension based on available engine."""
    if _PARQUET:
        out = path.with_suffix(".parquet")
        df.to_parquet(out, index=False, engine="pyarrow")
    else:
        out = path.with_suffix(".csv.gz")
        df.to_csv(out, index=False, compression="gzip")
    return out


def read(path: Path) -> pd.DataFrame:
    """Read a file written by write(), detecting format from extension."""
    if path.suffix == ".parquet":
        return pd.read_parquet(path, engine="pyarrow")
    # .gz or .csv
    return pd.read_csv(path, compression="infer")


def glob_latest(directory: Path, stem_pattern: str) -> Path:
    """Return the most recent file matching stem_pattern in directory."""
    candidates = sorted(
        list(directory.glob(f"{stem_pattern}*.parquet")) +
        list(directory.glob(f"{stem_pattern}*.csv.gz"))
    )
    if not candidates:
        raise FileNotFoundError(f"No files matching '{stem_pattern}*' in {directory}")
    return candidates[-1]
