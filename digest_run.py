"""
Daily digest entry point.

Generates a summary of everything the bot did and saw today, writes it
to data/digests/YYYY-MM-DD.md, and outputs it to the GitHub Actions
step summary so you can read it directly in the Actions tab.

Usage:
    python digest_run.py
"""
from __future__ import annotations

import logging

from bot.digest import write_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


if __name__ == "__main__":
    content = write_digest()
    log.info("Digest complete.")
    # Print to stdout as well so it appears in the raw Actions log.
    print("\n" + content)
