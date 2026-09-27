"""
Convenience runner for the corpus ingestion pipeline.

Usage (from backend/):
    python scripts/run_ingestion.py --sources p0 --mode update --limit 20
    python scripts/run_ingestion.py --list
    python scripts/run_ingestion.py --status
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ingestion.__main__ import main

if __name__ == "__main__":
    sys.exit(main())