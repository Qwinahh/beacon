"""
Send a note to the bot's memory.

Use this whenever you want the bot to remember something specific --
a position update, a project observation, something you want it to factor
into future posts. The note is stored in data/memory/quin_notes.json and
injected into the writer context on relevant future cycles.

Usage:
    python note.py "I just entered a Meteora USDC/SOL LP position, farming MET points"
    python note.py --project Hyperliquid "HLP vault took a loss today, watch for narrative shift"
    python note.py "Kaito season 2 criteria just dropped -- engagement window is open"

The bot reads these notes when generating posts about the relevant project.
Use this to keep the bot's views current without having to edit persona.md.
"""
from __future__ import annotations

import argparse
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send a note to the bot's memory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("note", help="The note text to store.")
    parser.add_argument(
        "--project", "-p",
        default=None,
        help="Optional project name this note is about (e.g. Hyperliquid, Kaito).",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List recent notes instead of adding a new one.",
    )
    args = parser.parse_args()

    from bot.brain.memory import add_quin_note, get_quin_notes

    if args.list:
        notes = get_quin_notes(n=10)
        if notes:
            print(notes)
        else:
            print("No notes stored yet.")
        return

    add_quin_note(args.note, project=args.project)

    project_str = f" (project: {args.project})" if args.project else ""
    log.info("Note stored%s: %s", project_str, args.note[:100])
    print(f"Stored. The bot will factor this in on the next relevant post cycle.")


if __name__ == "__main__":
    main()
