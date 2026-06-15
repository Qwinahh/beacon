"""
Patch for twscrape's XClIdGen.create() -- works around a Cloudflare
bot-challenge on the reference page twscrape uses to derive the
x-client-transaction-id header required by every X GraphQL request.

twscrape 0.18.1 hardcodes https://x.com/tesla as that reference page.
From many hosting environments (incl. GitHub Actions runners) that URL
returns a Cloudflare JS-challenge page instead of real X markup, so
get_scripts_list() finds no script-hash matches and raises
"Failed to parse scripts". XClIdGenStore.get() then exhausts its 3
retries and raises AbortReqError, so every twscrape call (mentions,
search, quote-tweet candidates, inspiration feed, etc.) silently fails
-- regardless of whether the account cookies are valid.

https://x.com (the homepage) is not challenged and exposes the same
script-hash maps, so we redo XClIdGen.create() against that URL instead.

Import this module for its side effect right after `from twscrape import API`.
Upstream issue: https://github.com/vladkens/twscrape/issues/248
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

_PATCHED = False


def apply() -> None:
    """Idempotently patch twscrape.xclid.XClIdGen.create(). Safe to call repeatedly."""
    global _PATCHED
    if _PATCHED:
        return
    try:
        import bs4
        from twscrape import xclid

        async def _patched_create() -> "xclid.XClIdGen":
            clt = xclid._make_client()
            try:
                text = await xclid.get_tw_page_text("https://x.com", clt)
                soup = bs4.BeautifulSoup(text, "html.parser")
                vk_bytes, anim_key = await xclid.load_keys(soup, clt)
                return xclid.XClIdGen(vk_bytes, anim_key)
            finally:
                await clt.aclose()

        xclid.XClIdGen.create = staticmethod(_patched_create)
        _PATCHED = True
        log.debug("twscrape_patch: XClIdGen.create patched to derive keys from x.com homepage")
    except Exception as exc:
        log.debug("twscrape_patch: failed to apply XClIdGen patch: %s", exc)


apply()
