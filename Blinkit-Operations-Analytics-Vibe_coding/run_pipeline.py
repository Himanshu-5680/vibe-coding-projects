"""
run_pipeline.py
===============
Standalone script to run the full data pipeline:
  1. Split happy_merged.csv into sub-tables
  2. Clean and validate each sub-table

Run with:
    python run_pipeline.py
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log", mode="w"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 60)
    logger.info("Quick-Commerce Analytics — Data Pipeline")
    logger.info("=" * 60)

    # Step 1: Split
    logger.info("\n--- Step 1: Splitting happy_merged.csv ---")
    import data_splitting
    tables = data_splitting.run()

    # Step 2: Clean
    logger.info("\n--- Step 2: Cleaning & Validating sub-tables ---")
    import data_cleaning
    cleaned, reports = data_cleaning.run()

    # Summary
    logger.info("\n--- Pipeline Summary ---")
    for name, df in cleaned.items():
        logger.info("  %-15s %6d rows × %2d cols", name, len(df), len(df.columns))

    logger.info("\nValidation Report:")
    total_warns = 0
    for report in reports:
        warns = [c for c in report["checks"] if c["status"] == "WARN"]
        total_warns += len(warns)
        if warns:
            logger.warning("  %s: %d warnings", report["table"], len(warns))
            for w in warns:
                logger.warning("    - %s -- %s", w["label"], w["detail"])

    if total_warns == 0:
        logger.info("  All validation checks passed.")
    else:
        logger.warning("  Total warnings: %d (see details above)", total_warns)

    logger.info("\nPipeline complete. Run 'streamlit run app.py' to launch the dashboard.")


if __name__ == "__main__":
    main()
