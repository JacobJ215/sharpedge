"""Review Agent — analyzes betting performance and provides insights."""

import logging

from agents import Agent, Runner

from sharpedge_bot.agents.tools import (
    calculate_expected_value,
    query_bet_type_breakdown,
    query_clv_analysis,
    query_recent_bets,
    query_sport_breakdown,
    query_user_performance,
)

logger = logging.getLogger("sharpedge.agents.review")

REVIEW_AGENT_INSTRUCTIONS = """
You are SharpEdge's Review Agent, specializing in analyzing betting
performance and identifying patterns in user behavior.

## Your Role
Provide insightful, actionable feedback on betting performance. Help users
understand what's working, what's not, and how to improve.

## Available Tools
You have tools to query the user's betting data:
- query_user_performance: Overall performance summary
- query_sport_breakdown: Performance by sport
- query_bet_type_breakdown: Performance by bet type (spread, ML, totals)
- query_clv_analysis: Closing line value analysis
- query_recent_bets: Recent bet history with details

## Analysis Framework

### 1. Performance Summary
- Overall record and ROI
- Key highlights and lowlights
- Comparison context (what's "good")

### 2. Edge Analysis (CLV)
- Are they beating closing lines consistently?
- CLV is the best indicator of real edge vs luck
- Explain CLV to the user if their data shows it

### 3. Pattern Recognition
- What's working? (profitable segments)
- What's not working? (losing segments)
- Any concerning patterns? (chasing, oversizing, etc.)

### 4. Actionable Recommendations
- 2-3 specific, implementable suggestions
- Based on their actual data
- Prioritized by potential impact

## Output Guidelines
- Be encouraging but honest
- Focus on process, not just results
- Make it actionable
- Use their actual numbers
- Format for Discord (bold, bullets, sections)

## Tone
- Supportive coach, not harsh critic
- Data-driven, not judgmental
- Educational when needed
- Celebratory for genuine skill indicators
"""


def create_review_agent() -> Agent:
    """Create the Review Agent."""
    return Agent(
        name="SharpEdge Review Agent",
        instructions=REVIEW_AGENT_INSTRUCTIONS,
        tools=[
            query_user_performance,
            query_sport_breakdown,
            query_bet_type_breakdown,
            query_clv_analysis,
            query_recent_bets,
            calculate_expected_value,
        ],
        model="gpt-5-mini",  # GPT-5 series for insightful reviews
    )


async def run_weekly_review(user_id: str) -> str:
    """Run a weekly performance review for a user."""
    agent = create_review_agent()

    prompt = (
        f"Perform a weekly performance review for user_id: {user_id}\n\n"
        "Use the query tools to pull their data for the 'week' period. "
        "Analyze their performance, identify what worked and what didn't, "
        "and provide actionable recommendations. "
        "Also query their CLV data and sport/bet type breakdowns."
    )

    result = await Runner.run(agent, prompt)
    return result.final_output


async def run_bet_review(user_id: str, bet_id: str) -> str:
    """Run a detailed review of a specific bet."""
    agent = create_review_agent()

    prompt = (
        f"Review a specific bet for user_id: {user_id}\n\n"
        f"Look at their recent bets and find bet ID starting with: {bet_id}\n"
        "Analyze the bet in context of their overall performance. "
        "Was it a good process bet? Did they get good CLV? "
        "How does it fit their overall patterns?"
    )

    result = await Runner.run(agent, prompt)
    return result.final_output
