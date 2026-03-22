# Copilot playbook

How to use **BettingCopilot** (web `/copilot`) with NBA line shopping, prediction markets (e.g. Kalshi), and bankroll discipline. Copilot **does not** place bets or exchange orders; it retrieves data, runs analysis tools, and returns streamed guidance.

---

## Access & requirements

| Item | Notes |
|------|--------|
| **Web UI** | Dashboard route **`/copilot`** — SSE streaming, optional **tool steps** panel. |
| **API** | `POST /api/v1/copilot/chat` (see `apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py`). |
| **Discord (Pro)** | **`/research`**, **`/breakdown`**, **`/trends`**, and **`/copilot-reset`** use the **same** LangGraph + tools as web (`discord_copilot.py`). Set **`OPENAI_API_KEY`** on the **bot** process. **Multi-turn memory** uses LangGraph **`MemorySaver`** in the bot process: same **user + channel** shares a **`thread_id`** until **`/copilot-reset`** or a bot restart. Set **`DISCORD_COPILOT_STATELESS=1`** to disable memory (each slash = isolated turn). Portfolio tools use **`get_or_create_user`** → internal **`users.id`**. **Web + Discord** do not share the same Postgres checkpoint unless you later proxy Discord to the webhook API with a user JWT. |
| **OpenAI** | Webhook server needs **`OPENAI_API_KEY`**. If missing, the stream returns a configuration message. |
| **Odds (compare / games)** | **`ODDS_API_KEY`** (and webhook config) for The Odds API — same source as Line shop / Props. |
| **Kalshi / Polymarket tools** | **`KALSHI_API_KEY`** (and optional `KALSHI_PRIVATE_KEY` where used), **`POLYMARKET_API_KEY`** when applicable — see tool implementations in `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py`. |
| **Auth** | Log in on the web app so requests include your Supabase **Bearer** token. Then tools that need **`user_id`** (`get_active_bets`, `get_portfolio_stats`, `get_user_exposure`, `check_pm_correlation`, `analyze_game`) resolve to **your** account. Without auth, user-scoped tools may be empty or generic. |

---

## Conversation threading

- The client stores a **`thread_id`** in `localStorage` (`sharpedge_copilot_thread_id`) and sends it as `thread_id` in the JSON body.
- If the server enables **Postgres checkpointer** persistence (`copilot_persist_threads` on app state), **`thread_id` is required**; otherwise requests without it still work with an ephemeral graph.
- **Discord:** follow-up questions in the **same channel** reuse the in-memory checkpoint until **`/copilot-reset`** or process restart. Use **`/copilot-reset`** before switching topics. For a clean slate without commands, set **`DISCORD_COPILOT_STATELESS=1`** on the bot.

---

## Operator environment variables

| Variable | Purpose |
|----------|---------|
| **`COPILOT_ROUTER_FOCUS`** | `all` (default) \| `sports` \| `pm` \| `portfolio` — restricts which tools are bound and adds a short system hint (`packages/agent_pipeline/.../copilot/router.py`). |
| **`COPILOT_COMPARE_BOOKS`** | Set to `0` to disable the **`compare_books`** tool. |
| **`COPILOT_VENUE_EXPOSURE_SIM`** | `1` / `true` / `yes` — adds **`get_exposure_status`** (simulated exposure book; `SHARPEDGE_BANKROLL` default 10000). |
| **`COPILOT_RECURSION_LIMIT`** | Max agent/tool loop depth (default **25**). |
| **`COPILOT_RATE_LIMIT_PER_MINUTE`** | Sliding-window cap per client key (default **20**). |
| **`COPILOT_RATE_BURST`** | Optional extra slots on top of the per-minute cap. |

Rate limiting is **in-memory per process**; multiple server instances do not share the same window.

### Discord bot (BettingCopilot)

| Variable | Purpose |
|----------|---------|
| **`DISCORD_COPILOT_STATELESS`** | `1` / `true` — no `MemorySaver`; each `/research` (and related) is one isolated turn. |
| (default) | In-process **multi-turn** memory per user + channel; use **`/copilot-reset`** to clear. |

---

## What the agent can call (summary)

Tools are defined in `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py`, `venue_tools.py`, and `tools_extended.py`.

**Portfolio / risk:** `get_active_bets`, `get_portfolio_stats`, `get_user_exposure`, `estimate_bankroll_risk`, `compute_kelly`

**NBA / sportsbook context (The Odds API):** `search_games`, `resolve_game`, `compare_books`, `get_model_predictions`, `check_line_movement`, `get_sharp_indicators`, `search_value_plays` (reads **`value_plays`** in Supabase), `analyze_game` (9-node analysis graph)

**Injuries:** `get_injury_report` (ESPN public API by team)

**Prediction markets:** `get_prediction_market_edge`, `scan_top_pm_edges`, `check_pm_correlation`, `get_venue_dislocation` (Kalshi vs Polymarket mids / dislocation when adapters are configured)

**Bovada note:** If The Odds API returns bookmaker key `bovada`, it appears in **`compare_books`** output like other books — Copilot does not scrape Bovada directly.

---

## Prompt patterns (copy and adapt)

### Before an NBA bet (line shop + context)

1. `Resolve NBA game [Team A] [Team B] and compare books for spread, total, and moneyline.`
2. `Injury report for [Team A] and for [Team B], sport NBA.`
3. `Get model predictions for game_id [id] sport NBA if available.`
4. `Any sharp indicators or significant line movement for game_id [id]?`

### Sizing (match your bankroll rules)

Use your **NBA sleeve** as `bankroll` when sizing (e.g. $700 on a $1k total plan):

- `Compute Kelly: bankroll 700, odds -110, win_prob 0.54, kelly_fraction 0.25`
- `Estimate bankroll risk for stake 7, odds -108, win_prob 0.52`

### Value plays (database scanner)

- `Top NBA value plays with brief summary of sides and EV.`
- Optional filter: the `search_value_plays` tool exposes `min_alpha` in its schema, but the implementation currently passes that value to the DB as **`min_ev`** (filters `ev_percentage`). Use it as an EV floor unless the tool is renamed in code.

### Kalshi / PM sleeve

1. `Scan top prediction market edges, max 10.`
2. `Edge analysis for Kalshi ticker [TICKER].`
3. `Check PM correlation for market title: [paste exact title].`
4. `Venue dislocation for market_id [TICKER] across kalshi and polymarket.`

### Logged portfolio (requires bets in SharpEdge)

- `How much do I have at risk? Open bets and exposure by sport.`
- `Portfolio stats: win rate, ROI, total bets.`
- `List my open bets with stake and odds; flag if any single bet is more than 5% of a 700 dollar bankroll.`
- `Given my portfolio stats, what sample-size caveats should I keep in mind before changing strategy?`

---

### NBA — slate & discovery

- `Search NBA games with query [Lakers] and list matchups with commence times.`
- `What NBA games are on the board today? Use search_games sport NBA query empty or tonight.`
- `Resolve NBA [Away] at [Home] and give me the Odds API game_id only, then compare books.`
- `Of these two games [A vs B] and [C vs D], which has wider disagreement between books on the total? Use resolve + compare for each.`

### NBA — single-game deep dive

- `Run analyze_game for NBA matchup [Team] vs [Team]. Summarize in 5 bullets; flag anything I should verify manually.`
- `Full betting analysis: [Team A] [Team B] NBA — then cross-check injuries for both teams.`
- `game_id [paste id]: pull model projections, line movement summary, and sharp indicators; one paragraph each.`
- `Is the market total for game_id [id] higher or lower than the model projected total? Show numbers.`

### Line movement & steam

- `Explain line movement for game_id [id] in plain English: what moved, how much, and what it might imply (not certainty).`
- `get_sharp_indicators and recent significant movements for game_id [id]; distinguish steam vs RLM if present.`
- `Compare current books for game_id [id] to the movement history: did the line stabilize or keep drifting?`

### Value-play triage

- `Pull top 5 NBA value plays from the scanner; for each, state the implied edge and one reason the market might disagree.`
- `Any value plays for sport NBA? I only want sides/totals confidence HIGH or MEDIUM if available in the data.`
- `I’m looking at value play [describe side/game]. What tools would falsify it—run injuries and compare_books if you can resolve the game.`

### Sizing & risk (variations)

- `Half Kelly vs quarter Kelly: same odds -115, win_prob 0.56, bankroll 700—show stakes for kelly_fraction 0.5 and 0.25.`
- `I want to risk at most 7 dollars on one bet; odds -108. What implied win rate do I need for that to be positive EV?`
- `estimate_bankroll_risk with stake 7, odds -110, win_prob 0.53 — interpret ruin_probability qualitatively (the tool uses fixed internal simulation params; use compute_kelly for dollar sizing on your real bankroll).`
- `I already have [X] dollars at risk tonight from logged bets; is adding a 7 dollar bet reasonable on a 700 dollar NBA sleeve?`

### Props-adjacent (game context; use `/props` in app for multi-book prop rows)

- `Before I bet a player points over on [game], summarize injuries and pace-related context for both NBA teams.`
- `analyze_game for [teams] NBA — focus on factors that affect scoring and minutes distribution for props.`

### Prediction markets — Kalshi & cross-venue

- `Scan top PM edges max_markets 40 max_edges 15; group by platform and highlight only alpha_badge PREMIUM or HIGH if present.`
- `get_prediction_market_edge for [ticker]; explain edge_pct vs fees in words a beginner would understand.`
- `get_venue_dislocation for [ticker] kalshi,polymarket — is the spread wide enough that “arb” is probably fake?`
- `I hold a position in [Kalshi title]. check_pm_correlation with that exact title and summarize overlap with my sportsbook exposure.`
- `Two Kalshi tickers [A] and [B]—are they likely correlated? Use scan + reasoning; no order placement.`

### Session discipline & meta

- `Help me prep one NBA bet using only line shopping, injuries, and line movement—skip prediction markets entirely.`
- `I’m over-betting emotionally—give a 3-question checklist before I stake anything (no tools required).`
- `Summarize what tools you just used and what you did not have access to, so I know gaps in this answer.`
- `Start a new thread mentally: ignore prior messages. Only use compare_books + injuries for [teams] NBA.`

### Post-session review

- `Based on my get_portfolio_stats, what’s one metric I should track next week and why?`
- `My thesis was [X] and the result was [Y]. Help me separate luck from process in 4 bullets (no new tool calls unless you need stats).`

---

## Thesis assistance (NBA / prediction markets)

Copilot can **help you build and stress-test a thesis** by combining reasoning with tools. It is **not** a proof of edge: models and APIs can be wrong, stale, or incomplete. Use it to **organize assumptions**, **pull facts**, and **list what would falsify your idea** before you size a bet.

**What it does well**

- Turn a vague lean into a **short thesis statement** (claim → mechanism → what has to be true).
- Run a **pre-mortem**: “If this bet loses, what are the top three reasons?”
- **Fetch** injuries, multi-book prices, line movement, scanner value plays, PM edge scans — then **summarize** how they support or contradict you.
- **`analyze_game`** for a **single** NBA matchup when you want a structured report to react to (still verify key facts).

**What to watch**

- **Win probability** for Kelly must come from **your** view (or a clearly labeled model output)—don’t let the chat invent a number without justification.
- **Correlation:** for PM + sports overlap, ask for **`check_pm_correlation`** after you name the market.
- **Execution:** Bovada/Kalshi prices at click time can differ from **`compare_books`** / API snapshots.

**One-shot thesis pass (paste and fill in)**

1. `My thesis: [e.g. over 225.5 in TEAM A vs TEAM B because pace and weak interior D]. Sport NBA. List assumptions, then contradict me.`
2. `Resolve that game, compare books for spread and total, then pull injury reports for both teams.`
3. `Any model projection or sharp/line-movement signal for this game_id? Summarize conflicts with my thesis.`
4. `If I still believe the thesis, what single fact would make me skip the bet?`
5. (PM only) `I’m considering Kalshi [ticker]. Scan edges if useful, then check PM correlation with my open bets.`

For a **PM-only** thesis, start with **`scan_top_pm_edges`** or a known ticker, then ask for **resolution rules, fees, liquidity caveats**, and **what would change your mind** before sizing.

**Extra thesis prompts**

- `Steel-man the opposite side of my thesis [X] for game [teams] NBA, then steel-man mine; which needs fewer assumptions?`
- `What would a sharp bettor need to see to bet against me here? Pull any data you can with tools.`
- `After analyze_game, give me three specific stats or facts I should double-check on a second source.`
- `PM thesis: I believe [ticker] is mispriced because [reason]. Scan edge + dislocation; list risks to settlement and liquidity.`

---

## UI shortcuts

The copilot page includes suggestion chips such as **“Best spread across books for a game?”** and **“Size my bet using Kelly criterion”**. Add **sport and team names** (or **`game_id`**) in the same message so the model can call **`resolve_game`** / **`compare_books`** without guessing.

---

## Failure modes (quick)

| Symptom | Likely cause |
|---------|----------------|
| “BettingCopilot is not configured” | Missing **`OPENAI_API_KEY`** on webhook server. |
| Empty portfolio / exposure | Not logged in, or no **`/bet`** (or API) data in DB for your user. |
| `compare_books` errors | Missing **`ODDS_API_KEY`**, or tool disabled via **`COPILOT_COMPARE_BOOKS=0`**. |
| PM tools empty / errors | Missing venue keys or market id mismatch. |
| 429 / throttling | **`COPILOT_RATE_LIMIT_*`**; wait or raise caps carefully. |

---

## Code map (maintainers)

| Piece | Path |
|--------|------|
| SSE route | `apps/webhook_server/src/sharpedge_webhooks/routes/v1/copilot.py` |
| Graph + model bind | `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/agent.py` |
| Tool registry | `packages/agent_pipeline/.../copilot/tools.py` |
| Focus router | `packages/agent_pipeline/.../copilot/router.py` |
| Web chat client | `apps/web/src/components/copilot/chat-stream.tsx` |

---

## Related docs

- **Tier / pricing / surfaces:** `docs/PLATFORM_FEATURES.md`  
- **Day-to-day product usage:** `docs/USER_GUIDE.md`  
- **Feature matrix:** `docs/FEATURE_OVERVIEW.md`
