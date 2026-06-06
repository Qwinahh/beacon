"""
Quick smoke-test for X_SCRAPER_COOKIES via twscrape.
Run: python test_cookies.py
"""
import asyncio
import os
import sys
import tempfile


async def test():
    try:
        from twscrape import API
    except ImportError:
        print("ERROR: twscrape not installed. Run: pip install twscrape")
        sys.exit(1)

    cookies = os.environ.get("X_SCRAPER_COOKIES", "").strip()
    if not cookies:
        print("ERROR: X_SCRAPER_COOKIES is not set.")
        sys.exit(1)

    print(f"Cookie length : {len(cookies)} chars")
    print(f"Cookie preview: {cookies[:40]}...")

    # Fresh db each test run — avoids leftover rate-limit timestamps
    db_path = os.path.join(tempfile.gettempdir(), "twscrape_test.db")
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass
    api = API(db_path)

    try:
        await api.pool.add_account(
            username="test_scraper",
            password="placeholder",
            email="placeholder@placeholder.com",
            email_password="placeholder",
            cookies=cookies,
        )
        print("Account added to pool — OK")
    except Exception as exc:
        print(f"ERROR adding account: {exc}")
        sys.exit(1)

    # Try fetching a well-known public account
    test_account = "DefiIgnas"
    print(f"\nFetching @{test_account} ...")
    try:
        user = await api.user_by_login(test_account)
        if user:
            print(f"  User found    : @{user.username}")
            print(f"  Followers     : {user.followersCount:,}")
        else:
            print("  ERROR: user not found (None returned)")
            sys.exit(1)
    except Exception as exc:
        print(f"  ERROR: {exc}")
        sys.exit(1)

    print(f"\nFetching latest tweet from @{test_account} (may be rate-limited if run repeatedly)...")
    try:
        async for tweet in api.user_tweets(user.id, limit=1):
            print(f"  Tweet ID      : {tweet.id}")
            print(f"  Likes         : {tweet.likeCount}")
            print(f"  Text preview  : {(tweet.rawContent or '')[:100]}")
            break
        else:
            print("  No tweets returned (rate limit or empty feed).")
    except Exception as exc:
        print(f"  Tweet fetch skipped (rate limit): {exc}")

    print("\nOK - Cookie authentication working correctly (user lookup passed).")

    # Clean up temp db
    try:
        os.remove(db_path)
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(test())
