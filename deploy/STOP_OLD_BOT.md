# Stopping the Old X Bot

The old bot is running via GitHub Actions. Here are three ways to stop it,
fastest first.

---

## Option 1 — Disable workflows in the GitHub UI (30 seconds)

1. Go to your old bot repo on GitHub
2. Click the **Actions** tab
3. In the left sidebar, find every workflow that has a schedule (e.g. "Post", "Bot", "Twitter Bot")
4. Click the workflow name → click the **...** menu (top right) → **Disable workflow**
5. Repeat for each scheduled workflow

This is instant and reversible.

---

## Option 2 — Delete the workflow files (permanent)

SSH into anywhere you have the old repo checked out, or use GitHub's web editor:

```bash
git clone https://github.com/YOUR_USER/OLD_REPO.git old-bot
cd old-bot
rm -rf .github/workflows/
git add -A
git commit -m "chore: disable all scheduled workflows"
git push
```

After this, no workflows will ever run again on that repo.

---

## Option 3 — Nuke the cron trigger (keep workflows, just stop the schedule)

If you want to keep the workflow files but stop auto-posting:

Open each workflow file (`.github/workflows/*.yml`) and replace:

```yaml
on:
  schedule:
    - cron: "..."
```

with:

```yaml
on:
  workflow_dispatch:
```

Then commit and push. The workflows still exist but only run when you
manually trigger them from the Actions tab.

---

## Confirming it's stopped

After disabling, go to the **Actions** tab on the old repo.
If no new runs appear after the next scheduled time, it's stopped.

You can also check: Actions → (workflow name) → look at the last run time.
If it's still running, try Option 2.
