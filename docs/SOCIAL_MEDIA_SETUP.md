# Social Media Automation — Setup Guide

This guide covers everything needed to configure SharpEdge to automatically post
value play alerts and win announcements to Discord, Instagram, and X/Twitter.

**Do not enable posting until all credentials are in place and tested.**
The master switch `ALERT_ENABLED=false` keeps everything dormant by default.

---

## Overview

When enabled, two background jobs run alongside the webhook server:

| Job | What it does |
|-----|--------------|
| `alert_poster` | Polls `value_plays` every 60s. Posts new high-EV plays to all platforms. |
| `result_watcher` | Polls `bets` every 60s. Posts win announcements when bets settle as WIN. |

Both jobs post to **Discord → Instagram → X/Twitter** in that order. A failure on
one platform does not block the others. Every post is recorded in `social_posts`
and every alert attempt in `alert_queue` for full auditability.

---

## Part 1 — Database

Run the Part 6 block from `scripts/schema.sql` in the **Supabase SQL Editor**
(Dashboard → SQL Editor → New query).

The block creates three tables:
- `social_posts` — record of every post sent, with engagement counters
- `alert_queue` — deduplication and retry state for each alert
- `win_announcements` — structured win data linked to the announcing post

The block is idempotent (`CREATE TABLE IF NOT EXISTS`) — safe to re-run.

---

## Part 2 — Discord

Discord uses the existing bot token already configured in `.env`. No new
application registration is needed.

### Steps

1. **Create two channels** in your Discord server (or reuse existing):
   - A channel for live value play alerts (e.g. `#value-alerts`)
   - A channel for win announcements (e.g. `#winners`)

2. **Copy the channel IDs**
   Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode),
   then right-click each channel → Copy Channel ID.

3. **Add to `.env`:**
   ```
   VALUE_ALERTS_CHANNEL_ID=123456789012345678
   WIN_ANNOUNCEMENTS_CHANNEL_ID=123456789012345679
   ```

4. **Ensure the bot has permissions** in both channels:
   - Send Messages
   - Embed Links
   - Attach Files (required for image cards)

No additional OAuth scopes or API keys are required — the bot token is already
present as `DISCORD_BOT_TOKEN`.

---

## Part 3 — Instagram

Instagram requires a **Professional account** (Business or Creator) linked to a
**Facebook Developer app**.

### 3a — Account setup

1. Convert your Instagram account to a **Business** or **Creator** account
   (Instagram Settings → Account → Switch to Professional Account).

2. Link it to a **Facebook Page** (required by Meta for API access).

### 3b — Facebook Developer app

1. Go to [developers.facebook.com](https://developers.facebook.com) → My Apps → Create App.
2. Choose **Business** as the app type.
3. Add the **Instagram Graph API** product to the app.

### 3c — Get your Account ID and Access Token

#### Account ID
In the Facebook Developer console, navigate to:
**Instagram Graph API → Basic Display → Instagram Tester** or use the Graph API
Explorer:

```
GET https://graph.instagram.com/me?fields=id,username&access_token=YOUR_TOKEN
```

The `id` field is your `INSTAGRAM_ACCOUNT_ID`.

#### Access Token (long-lived)

1. In the **Graph API Explorer**, generate a short-lived User token with these
   permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_read_engagement`

2. Exchange for a **long-lived token** (valid 60 days):
   ```
   GET https://graph.facebook.com/v21.0/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id=YOUR_APP_ID
     &client_secret=YOUR_APP_SECRET
     &fb_exchange_token=SHORT_LIVED_TOKEN
   ```

3. **Token refresh** — long-lived tokens expire after 60 days. Refresh before
   expiry:
   ```
   GET https://graph.instagram.com/refresh_access_token
     ?grant_type=ig_refresh_token
     &access_token=LONG_LIVED_TOKEN
   ```
   Set a calendar reminder at day 50 to refresh. A future enhancement will
   automate this.

### 3d — Add to `.env`

```
INSTAGRAM_ACCESS_TOKEN=EAAxxxxxxx...
INSTAGRAM_ACCOUNT_ID=17841400000000000
INSTAGRAM_ACCOUNT_HANDLE=@yourhandle
```

### 3e — Image hosting requirement

Instagram requires images to be served from a **publicly accessible URL** —
you cannot upload raw bytes directly. SharpEdge uploads generated cards to
**Supabase Storage** first, then passes the public URL to Instagram.

1. In Supabase Dashboard → Storage → Create a new bucket called `social-cards`.
2. Set the bucket to **Public**.
3. Add to `.env`:
   ```
   SUPABASE_STORAGE_BUCKET=social-cards
   ```

---

## Part 4 — X / Twitter

Twitter requires an app registered in the **Twitter Developer Portal** with
**OAuth 1.0a** credentials (for posting as your own account).

### 4a — Developer account

1. Apply for a developer account at [developer.twitter.com](https://developer.twitter.com).
2. Create a **Project** and an **App** within it.
3. Set the app's **permissions** to **Read and Write** (default is Read Only —
   this must be changed before generating tokens).

### 4b — Required tier

| Tier | Monthly cost | Write limit | Minimum for SharpEdge |
|------|-------------|-------------|----------------------|
| Free | $0 | 1,500 tweets/month | Not recommended |
| Basic | $100 | 3,000 tweets/month | **Minimum viable** |
| Pro | $5,000 | 300,000 tweets/month | High volume |

At 3–5 alerts per day plus win announcements, the **Basic tier** covers typical
usage. Sign up at [developer.twitter.com/en/portal/products/basic](https://developer.twitter.com/en/portal/products/basic).

### 4c — Generate credentials

In the Developer Portal → your App → **Keys and Tokens**:

| Credential | Where to find it |
|-----------|-----------------|
| API Key | "Consumer Keys" section |
| API Key Secret | "Consumer Keys" section |
| Access Token | "Authentication Tokens" → generate for your account |
| Access Token Secret | "Authentication Tokens" → generate for your account |

**Important:** The Access Token and Secret are tied to the account that will
be posting. Generate them while logged in as the SharpEdge account.

### 4d — Add to `.env`

```
TWITTER_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
TWITTER_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWITTER_ACCESS_TOKEN=0000000000-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWITTER_ACCESS_TOKEN_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Part 5 — Pillow (image card generation)

Image cards are generated using Pillow. Without it, posts are sent as text only.

```bash
uv add pillow --package sharpedge-webhooks
```

Cards are 1080×1080px (square — fits Instagram feed, Reels thumbnail, and
Twitter). Alert cards use a teal accent; win announcement cards use an amber accent.

---

## Part 6 — Posting behaviour configuration

These control how aggressively the jobs post. Start conservative.

| Variable | Default | Description |
|----------|---------|-------------|
| `ALERT_ENABLED` | `false` | Master switch. Set to `true` to activate both jobs. |
| `ALERT_MIN_EV_THRESHOLD` | `3.0` | Minimum EV% for a play to trigger an alert. |
| `ALERT_COOLDOWN_MINUTES` | `5` | Suppress duplicate alerts for the same play within this window. |
| `ALERT_POLL_INTERVAL_SECONDS` | `60` | How often the jobs check for new plays/wins. |
| `SOCIAL_IMAGE_ENABLED` | `true` | Generate and attach image cards. Set to `false` to post text only. |

Add to `.env`:
```
ALERT_ENABLED=false
ALERT_MIN_EV_THRESHOLD=3.0
ALERT_COOLDOWN_MINUTES=5
ALERT_POLL_INTERVAL_SECONDS=60
SOCIAL_IMAGE_ENABLED=true
```

---

## Part 7 — Full `.env` additions checklist

Copy this block into your `.env` and fill in the values:

```bash
# ── Social media ──────────────────────────────────────────────────────────────

# Discord channels
VALUE_ALERTS_CHANNEL_ID=
WIN_ANNOUNCEMENTS_CHANNEL_ID=

# X / Twitter (Basic tier required for reliable posting volume)
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_TOKEN_SECRET=

# Instagram Graph API
INSTAGRAM_ACCESS_TOKEN=
INSTAGRAM_ACCOUNT_ID=
INSTAGRAM_ACCOUNT_HANDLE=

# Supabase Storage (for Instagram image hosting)
SUPABASE_STORAGE_BUCKET=social-cards

# Posting behaviour
ALERT_ENABLED=false
ALERT_MIN_EV_THRESHOLD=3.0
ALERT_COOLDOWN_MINUTES=5
ALERT_POLL_INTERVAL_SECONDS=60
SOCIAL_IMAGE_ENABLED=true
```

---

## Part 8 — Enabling and verifying

### Step 1 — Run the schema

Run Part 6 of `scripts/schema.sql` in the Supabase SQL Editor. Confirm the three
tables appear in the Table Editor.

### Step 2 — Enable posting

Set `ALERT_ENABLED=true` in `.env` and restart the server:
```bash
uv run --env-file .env sharpedge-webhooks
```

The server logs should show:
```
result_watcher job started (poll interval 60s)
alert_poster job started
```

### Step 3 — Verify a post

To trigger a test without waiting for a live signal, temporarily insert a
value play into the database with a high EV:
```sql
-- Run in Supabase SQL Editor — delete after testing
INSERT INTO value_plays (game_id, game, sport, bet_type, side, sportsbook,
  market_odds, model_probability, implied_probability, fair_odds,
  edge_percentage, ev_percentage, confidence, is_active, game_start_time)
VALUES ('test_001', 'Test Game', 'NFL', 'SPREAD', 'Team A -3', 'FanDuel',
  -108, 0.55, 0.52, -115, 3.2, 5.8, 'high', true,
  NOW() + INTERVAL '6 hours');
```

Within 60 seconds, the `alert_poster` job should fire and you should see:
- An embed in your Discord `#value-alerts` channel
- An Instagram feed post (if credentials are set)
- A tweet on your connected Twitter account (if credentials are set)
- A row in `alert_queue` with `status='posted'`
- Rows in `social_posts` for each platform

Delete the test row after verifying:
```sql
DELETE FROM value_plays WHERE game_id = 'test_001';
```

---

## Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| No posts appearing | `ALERT_ENABLED=false` or `ALERT_MIN_EV_THRESHOLD` too high |
| Discord posts but not Instagram | Instagram token expired (60-day limit) or `INSTAGRAM_ACCOUNT_ID` wrong |
| Instagram posts but no image | `SUPABASE_STORAGE_BUCKET` not created or bucket is private |
| Twitter returns 403 | App permissions are Read Only — change to Read+Write in Developer Portal |
| Twitter returns 429 | Rate limit hit — Basic tier allows 3,000/month; check volume |
| `alert_queue` rows stuck at `pending` | Exception in `post_service` — check server logs |
| Image cards are blank/missing | Pillow not installed — run `uv add pillow --package sharpedge-webhooks` |
