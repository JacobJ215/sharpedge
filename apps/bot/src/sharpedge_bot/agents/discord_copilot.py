"""Run the same LangGraph BettingCopilot as web/mobile (tool parity + thesis prompts).

Resolves Discord members to ``users.id`` via ``get_or_create_user`` so portfolio,
exposure, and PM-correlation tools align with bets logged from Discord.

**Conversation memory (default):** uses LangGraph ``MemorySaver`` (in-process) with a
stable ``thread_id`` per user + channel. Survives multiple ``/research`` turns until
the bot restarts or the user runs ``/copilot-reset``.

**Stateless:** set env ``DISCORD_COPILOT_STATELESS=1`` to disable checkpointing (each
slash command is an isolated turn).

**Shared DB with web:** the bot uses **in-process** ``MemorySaver`` only. The webhook
server’s Postgres checkpointer is **async** and is not wired here (sync ``invoke`` in a
worker thread). To share threads with web later, prefer proxying to
``POST /api/v1/copilot/chat`` with a user JWT or add a dedicated async runner.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any

logger = logging.getLogger("sharpedge.bot.copilot")

# Per (discord_user, guild/dm, channel) conversation generation — bump resets LangGraph thread
_version_lock = threading.Lock()
_thread_versions: dict[tuple[str, str, str], int] = {}

_graph_ephemeral: Any = None
_graph_memory: Any = None
_memory_saver: Any = None
def _use_memory_checkpointing() -> bool:
    if os.environ.get("DISCORD_COPILOT_STATELESS", "").lower() in ("1", "true", "yes"):
        return False
    return True


def bump_discord_copilot_thread(interaction) -> int:
    """Increment thread generation so the next copilot call starts a fresh checkpoint."""
    uid, gid, cid = _interaction_location_ids(interaction)
    with _version_lock:
        k = (uid, gid, cid)
        _thread_versions[k] = _thread_versions.get(k, 0) + 1
        return _thread_versions[k]


def _interaction_location_ids(interaction) -> tuple[str, str, str]:
    uid = str(interaction.user.id)
    cid = str(interaction.channel_id)
    gid = str(interaction.guild.id) if interaction.guild else "dm"
    return uid, gid, cid


def _thread_slug(interaction) -> str:
    uid, gid, cid = _interaction_location_ids(interaction)
    with _version_lock:
        v = _thread_versions.get((uid, gid, cid), 0)
    # Mirror web pattern: internal id is in configurable user_id; slug is client-owned
    return f"discord-u{uid}-g{gid}-c{cid}-v{v}"


def _ensure_internal_user_id(discord_id_str: str, discord_username: str | None) -> str:
    from sharpedge_db.queries.users import get_or_create_user

    user = get_or_create_user(discord_id_str, discord_username)
    return str(user.id)


def _discord_message_chunks(text: str, max_len: int = 1900) -> list[str]:
    text = text.strip() or "(empty response)"
    if len(text) <= max_len:
        return [text]
    return [text[i : i + max_len] for i in range(0, len(text), max_len)]


def _get_ephemeral_graph():
    global _graph_ephemeral
    from sharpedge_agent_pipeline.copilot.agent import build_copilot_graph

    if _graph_ephemeral is None:
        _graph_ephemeral = build_copilot_graph()
    return _graph_ephemeral


def _get_memory_graph():
    global _graph_memory, _memory_saver
    from langgraph.checkpoint.memory import MemorySaver
    from sharpedge_agent_pipeline.copilot.agent import build_copilot_graph

    if _graph_memory is None:
        _memory_saver = MemorySaver()
        _graph_memory = build_copilot_graph(checkpointer=_memory_saver)
    return _graph_memory


def _recursion_config() -> int:
    try:
        rl = int(os.environ.get("COPILOT_RECURSION_LIMIT", "25"))
    except ValueError:
        rl = 25
    return max(2, rl)


async def run_discord_copilot(query: str, *, interaction) -> str:
    """Invoke BettingCopilot; uses interaction for user id + conversation thread."""
    if not os.environ.get("OPENAI_API_KEY"):
        return (
            "BettingCopilot is not configured here: set **OPENAI_API_KEY** on the bot "
            "host (same model/tools as web `/copilot`)."
        )

    from langchain_core.messages import HumanMessage

    did = str(interaction.user.id)
    internal = _ensure_internal_user_id(did, interaction.user.display_name)
    rl = _recursion_config()
    config: dict[str, Any] = {
        "configurable": {"user_id": internal},
        "recursion_limit": rl,
    }

    use_cp = _use_memory_checkpointing()
    graph = _get_memory_graph() if use_cp else _get_ephemeral_graph()

    if use_cp:
        slug = _thread_slug(interaction)
        config["configurable"]["thread_id"] = f"{internal}:{slug}"

    def _invoke() -> dict:
        return graph.invoke(
            {"messages": [HumanMessage(content=query)]},
            config=config,
        )

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, _invoke)
    except Exception as exc:
        logger.exception("discord copilot invoke failed")
        return f"Copilot error: {exc!s}"

    messages = result.get("messages") or []
    if not messages:
        return "No response from Copilot."
    last = messages[-1]
    content = getattr(last, "content", None)
    if content is None:
        return str(last)
    if isinstance(content, list):
        return "\n".join(str(p) for p in content)
    return str(content)


async def send_discord_copilot_reply(
    interaction,
    query: str,
    *,
    embed_title: str | None = None,
) -> None:
    """Run copilot and send one or more followup messages (chunked)."""
    import discord

    result = await run_discord_copilot(query, interaction=interaction)
    chunks = _discord_message_chunks(result)
    for i, chunk in enumerate(chunks):
        if i == 0 and embed_title:
            embed = discord.Embed(
                title=embed_title,
                description=chunk[:4096],
                color=0x3498DB,
            )
            embed.set_footer(
                text="SharpEdge BettingCopilot | Informational only — not financial advice",
            )
            await interaction.followup.send(embed=embed)
        elif i == 0:
            await interaction.followup.send(chunk)
        else:
            await interaction.followup.send(chunk)
