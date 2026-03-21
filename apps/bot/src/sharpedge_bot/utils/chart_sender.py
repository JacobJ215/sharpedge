"""Utility for sending charts to Discord.

Converts matplotlib figures to Discord-compatible file uploads.
"""

import io

import discord


async def send_chart_to_channel(
    channel: discord.TextChannel | discord.Thread,
    chart_bytes: bytes,
    filename: str = "chart.png",
    embed: discord.Embed | None = None,
    content: str | None = None,
) -> discord.Message:
    """Send a chart image to a Discord channel.

    Args:
        channel: Discord channel or thread
        chart_bytes: PNG bytes from visualization module
        filename: Name for the file attachment
        embed: Optional embed to accompany the image
        content: Optional text content

    Returns:
        The sent message
    """
    file = discord.File(io.BytesIO(chart_bytes), filename=filename)

    if embed:
        embed.set_image(url=f"attachment://{filename}")
        return await channel.send(content=content, embed=embed, file=file)
    else:
        return await channel.send(content=content, file=file)


async def send_chart_followup(
    interaction: discord.Interaction,
    chart_bytes: bytes,
    filename: str = "chart.png",
    embed: discord.Embed | None = None,
    content: str | None = None,
) -> None:
    """Send a chart as an interaction followup.

    Args:
        interaction: Discord interaction
        chart_bytes: PNG bytes from visualization module
        filename: Name for the file attachment
        embed: Optional embed to accompany the image
        content: Optional text content
    """
    file = discord.File(io.BytesIO(chart_bytes), filename=filename)

    if embed:
        embed.set_image(url=f"attachment://{filename}")
        await interaction.followup.send(content=content, embed=embed, file=file)
    else:
        await interaction.followup.send(content=content, file=file)


def create_chart_embed(
    title: str,
    description: str | None = None,
    color: int = 0x3498DB,
    footer: str | None = None,
) -> discord.Embed:
    """Create a standard embed for chart messages.

    Args:
        title: Embed title
        description: Optional description
        color: Embed color
        footer: Optional footer text

    Returns:
        Configured Discord embed
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
    )

    if footer:
        embed.set_footer(text=footer)
    else:
        embed.set_footer(text="SharpEdge Analytics")

    return embed
