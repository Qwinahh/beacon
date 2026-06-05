"""
Obsidian vault reader/writer.

The vault at data/vault/ is the bot's persistent knowledge base.
Files are plain markdown — you can open the folder in Obsidian and
browse, edit, or extend what the bot knows.

Structure:
  data/vault/
    projects/<name>.md    -- per-project thesis, observations, airdrop status
    narratives/<name>.md  -- macro narrative tracking
    log/YYYY-MM-DD.md     -- daily post/skip/research log
    index.md              -- landing page

The bot reads project files before generating posts (replaces
data/projects/*.json). It appends observations and daily log entries
after each cycle. You can edit any file — the bot will pick up changes
on the next run.

Frontmatter parsing is intentionally simple: we only look for lines of
the form `key: value` between the opening and closing `---` delimiters.
No external YAML library required.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

VAULT_DIR  = Path("data/vault")
PROJ_DIR   = VAULT_DIR / "projects"
NARR_DIR   = VAULT_DIR / "narratives"
LOG_DIR    = VAULT_DIR / "log"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_name(name: str) -> str:
    """Convert a project name to a safe filename stem."""
    return re.sub(r"[^\w\-]", "_", name.lower().strip())[:60]


def _today() -> str:
    return date.today().isoformat()


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Parse YAML-ish frontmatter from a markdown file.

    Returns (frontmatter_dict, body_text).
    Only handles simple `key: value` lines — no nested structures.
    """
    fm: dict = {}
    if not text.startswith("---"):
        return fm, text

    end = text.find("\n---", 3)
    if end == -1:
        return fm, text

    raw_fm = text[3:end].strip()
    body   = text[end + 4:].lstrip("\n")

    for line in raw_fm.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            # Coerce obvious booleans and numbers
            if val.lower() == "true":
                fm[key] = True
            elif val.lower() == "false":
                fm[key] = False
            else:
                try:
                    fm[key] = int(val)
                except ValueError:
                    try:
                        fm[key] = float(val)
                    except ValueError:
                        fm[key] = val

    return fm, body


def _render_frontmatter(fm: dict) -> str:
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def _extract_section(body: str, heading: str) -> str:
    """Extract the content of a ## Section by heading name."""
    pattern = rf"## {re.escape(heading)}\n(.*?)(?=\n## |\Z)"
    m = re.search(pattern, body, re.DOTALL)
    return m.group(1).strip() if m else ""


def _append_to_section(body: str, heading: str, bullet: str) -> str:
    """
    Append a bullet line to a ## Section.

    If the section ends with a HTML comment (<!-- ... -->), inserts
    the bullet before it so the comment stays at the bottom.
    If the section doesn't exist, appends it at the end.
    """
    section_pattern = rf"(## {re.escape(heading)}\n)(.*?)(\n## |\Z)"
    m = re.search(section_pattern, body, re.DOTALL)

    if not m:
        # Section doesn't exist — append it.
        return body.rstrip() + f"\n\n## {heading}\n{bullet}\n"

    section_body = m.group(2)

    # Insert before trailing comment block if present.
    comment_match = re.search(r"\n<!-- .+? -->\n?$", section_body, re.DOTALL)
    if comment_match:
        insert_at = comment_match.start()
        new_section_body = (
            section_body[:insert_at]
            + f"\n{bullet}"
            + section_body[insert_at:]
        )
    else:
        new_section_body = section_body.rstrip() + f"\n{bullet}\n"

    return body[:m.start()] + m.group(1) + new_section_body + m.group(3) + body[m.end():]


# ---------------------------------------------------------------------------
# Project vault API
# ---------------------------------------------------------------------------

def project_path(name: str) -> Path:
    return PROJ_DIR / f"{_safe_name(name)}.md"


def read_project(name: str) -> Optional[dict]:
    """
    Read a project vault file and return a structured dict, or None if
    the file doesn't exist or the project is blocked.
    """
    path = project_path(name)
    if not path.exists():
        # Try fuzzy match on filename stems.
        stem = _safe_name(name)
        matches = list(PROJ_DIR.glob(f"*{stem[:6]}*.md"))
        if not matches:
            return None
        path = matches[0]

    text = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)

    if fm.get("blocked"):
        return None

    return {
        "name":          fm.get("name", name),
        "trust_score":   fm.get("trust_score", 0),
        "category":      fm.get("category", ""),
        "chain":         fm.get("chain", ""),
        "last_updated":  fm.get("last_updated", ""),
        "airdrop_status":fm.get("airdrop_status", "none"),
        "worth_farming": fm.get("worth_farming", False),
        "thesis":        _extract_section(body, "Thesis"),
        "stance":        _extract_section(body, "Stance"),
        "risks":         _extract_section(body, "Risks"),
        "observations":  _extract_section(body, "Observations"),
        "x_consensus":   _extract_section(body, "X Consensus"),
        "airdrop_notes": _extract_section(body, "Airdrop"),
        "_path":         str(path),
    }


def get_project_context(name: str) -> str:
    """
    Return a compact context string for the writer, or empty string if
    this project has no vault entry.
    """
    data = read_project(name)
    if not data:
        return ""

    parts = [f"## Project Memory: {data['name']}"]

    trust = data.get("trust_score", 0)
    if trust:
        parts.append(f"Trust score: {trust}/5")

    if data.get("thesis"):
        parts.append(f"\n**Thesis:** {data['thesis']}")

    if data.get("stance"):
        parts.append(f"\n**Current stance:** {data['stance']}")

    # Last 3 observation bullets.
    obs_text = data.get("observations", "")
    if obs_text:
        bullets = [l.strip() for l in obs_text.splitlines() if l.strip().startswith("- ")]
        recent = bullets[-3:]
        if recent:
            parts.append("\n**Recent observations:**\n" + "\n".join(recent))

    if data.get("x_consensus"):
        parts.append(f"\n**X consensus:** {data['x_consensus']}")

    return "\n".join(parts)


def add_observation(name: str, note: str, source: str = "bot") -> bool:
    """
    Append a timestamped observation bullet to a project's Observations section.
    Creates the file with a minimal template if it doesn't exist yet.
    """
    PROJ_DIR.mkdir(parents=True, exist_ok=True)
    path = project_path(name)

    if not path.exists():
        _create_project_stub(name, path)

    text = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)

    bullet = f"- **{_today()}** — {note}"
    if source and source != "bot":
        bullet += f" *(source: {source})*"

    new_body = _append_to_section(body, "Observations", bullet)

    # Update last_updated in frontmatter.
    fm["last_updated"] = _today()
    path.write_text(
        _render_frontmatter(fm) + "\n\n" + new_body,
        encoding="utf-8",
    )
    log.info("Vault: observation added for '%s'", name)
    return True


def update_thesis(name: str, thesis: str) -> bool:
    """Overwrite the Thesis section in a project file."""
    path = project_path(name)
    if not path.exists():
        _create_project_stub(name, path)

    text = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)

    # Replace the Thesis section content.
    pattern = r"(## Thesis\n)(.*?)(\n## |\Z)"
    replacement = rf"\g<1>{thesis}\n\g<3>"
    new_body = re.sub(pattern, replacement, body, flags=re.DOTALL)

    if new_body == body:
        # Section didn't exist — append it.
        new_body = body.rstrip() + f"\n\n## Thesis\n{thesis}\n"

    fm["last_updated"] = _today()
    path.write_text(_render_frontmatter(fm) + "\n\n" + new_body, encoding="utf-8")
    log.info("Vault: thesis updated for '%s'", name)
    return True


def update_trust_score(name: str, score: int) -> bool:
    """Update the trust_score frontmatter field."""
    path = project_path(name)
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)
    fm["trust_score"]  = max(1, min(5, score))
    fm["last_updated"] = _today()
    path.write_text(_render_frontmatter(fm) + "\n\n" + body, encoding="utf-8")
    return True


def update_airdrop_status(name: str, status: str, worth: Optional[bool] = None) -> bool:
    """Update airdrop frontmatter fields."""
    path = project_path(name)
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)
    fm["airdrop_status"] = status
    if worth is not None:
        fm["worth_farming"] = worth
    fm["last_updated"] = _today()
    path.write_text(_render_frontmatter(fm) + "\n\n" + body, encoding="utf-8")
    return True


def _create_project_stub(name: str, path: Path) -> None:
    """Create a minimal project file for an unknown project."""
    fm = {
        "name":           name,
        "trust_score":    0,
        "category":       "unknown",
        "chain":          "unknown",
        "last_updated":   _today(),
        "airdrop_status": "none",
        "worth_farming":  False,
        "blocked":        False,
    }
    body = f"""
# {name}

## Thesis
*Not yet researched. Bot will update after first deep-dive.*

## Observations
<!-- Bot appends new observations below. Newest at bottom. -->

## Airdrop
- Status: none
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_frontmatter(fm) + "\n" + body.lstrip(), encoding="utf-8")
    log.info("Vault: created stub for new project '%s'", name)


# ---------------------------------------------------------------------------
# Daily log API
# ---------------------------------------------------------------------------

def _log_path(day: Optional[str] = None) -> Path:
    return LOG_DIR / f"{day or _today()}.md"


def _ensure_log(path: Path) -> None:
    """Create today's log file if it doesn't exist."""
    if path.exists():
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# {path.stem}\n\n"
        "## Posts\n\n"
        "## Skipped\n\n"
        "## Research\n\n"
        "## Signals\n\n",
        encoding="utf-8",
    )


def log_post(tweet_text: str, topic: str, fmt: str) -> None:
    """Append a posted tweet to today's log."""
    path = _log_path()
    _ensure_log(path)
    text = path.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(text)

    proj_file = PROJ_DIR / f"{_safe_name(topic)}.md"
    if topic and proj_file.exists():
        project_link = f"[[projects/{_safe_name(topic)}|{topic}]]"
    else:
        project_link = topic or "general"
    bullet = (
        f"- **{_now_ts()}** | `{fmt}` | {project_link}\n"
        f"  > {tweet_text}"
    )
    new_body = _append_to_section(body, "Posts", bullet)
    path.write_text(new_body, encoding="utf-8")


def log_skip(topic: str, reason: str) -> None:
    """Append a skipped cycle to today's log."""
    path = _log_path()
    _ensure_log(path)
    text = path.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(text)

    bullet = f"- **{_now_ts()}** — {reason} — {topic or 'no topic'}"
    new_body = _append_to_section(body, "Skipped", bullet)
    path.write_text(new_body, encoding="utf-8")


def log_research(project: str, trust_score: int, notes: str = "") -> None:
    """Append a research run to today's log."""
    path = _log_path()
    _ensure_log(path)
    text = path.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(text)

    project_link = f"[[projects/{_safe_name(project)}|{project}]]"
    bullet = f"- **{_now_ts()}** — Researched {project_link} → trust: {trust_score}/5"
    if notes:
        bullet += f" — {notes}"
    new_body = _append_to_section(body, "Research", bullet)
    path.write_text(new_body, encoding="utf-8")


def log_signal(kind: str, topic: str, urgency: int) -> None:
    """Append a detected signal to today's log."""
    path = _log_path()
    _ensure_log(path)
    text = path.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(text)

    stars = "⚡" * urgency
    bullet = f"- {stars} `{kind}` — {topic} (urgency {urgency})"
    new_body = _append_to_section(body, "Signals", bullet)
    path.write_text(new_body, encoding="utf-8")


# ---------------------------------------------------------------------------
# Listing helpers
# ---------------------------------------------------------------------------

def list_projects() -> list[dict]:
    """Return frontmatter dicts for all non-blocked project files."""
    if not PROJ_DIR.exists():
        return []
    results = []
    for p in sorted(PROJ_DIR.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        fm, _ = _parse_frontmatter(text)
        if not fm.get("blocked"):
            results.append(fm)
    return results


def search_projects(query: str) -> list[str]:
    """Return project names whose files contain the query string."""
    if not PROJ_DIR.exists():
        return []
    q = query.lower()
    return [
        p.stem for p in PROJ_DIR.glob("*.md")
        if q in p.read_text(encoding="utf-8").lower()
    ]
