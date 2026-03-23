"""
pipeline.py
Top-level orchestrator: run Bronze → Silver → Gold in sequence.
Each layer passes its output path to the next so no file-discovery
logic is needed during a single pipeline run.
"""

import sys
import time
from datetime import datetime, timezone

from utils.logger import get_logger
from bronze.ingest    import run as bronze_run
from silver.transform import run as silver_run
from gold.aggregate   import run as gold_run

logger = get_logger("pipeline")


def run_pipeline(limit: int = 1_000) -> bool:
    """
    Execute the full medallion pipeline.

    Parameters
    ----------
    limit : int
        Number of rows to fetch from the source API.

    Returns
    -------
    bool
        True on success, False if any layer raised an exception.
    """
    start = time.time()
    logger.info("━" * 60)
    logger.info("  MEDALLION ELT PIPELINE — starting")
    logger.info(f"  Run time : {datetime.now(timezone.utc).isoformat()} UTC")
    logger.info(f"  API limit: {limit:,} rows")
    logger.info("━" * 60)

    try:
        # ── Layer 1: Bronze ────────────────────────────────────────────────────
        bronze_path = bronze_run(limit=limit)

        # ── Layer 2: Silver ────────────────────────────────────────────────────
        silver_path = silver_run(bronze_path=bronze_path)

        # ── Layer 3: Gold ──────────────────────────────────────────────────────
        gold_paths = gold_run(silver_path=silver_path)

    except Exception as exc:
        logger.error(f"Pipeline failed: {exc}", exc_info=True)
        return False

    elapsed = time.time() - start
    logger.info("━" * 60)
    logger.info(f"  PIPELINE COMPLETE — {elapsed:.1f}s")
    logger.info(f"  Bronze  : {bronze_path}")
    logger.info(f"  Silver  : {silver_path}")
    logger.info(f"  Gold    : {len(gold_paths)} tables")
    logger.info("━" * 60)
    return True


if __name__ == "__main__":
    # Optional CLI arg: python pipeline.py 500
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1_000
    success = run_pipeline(limit=limit)
    sys.exit(0 if success else 1)
