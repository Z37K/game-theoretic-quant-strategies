"""
target_rank_agent.py - answers "what rank does this book reach, and what should I aim at?"

A SIMPLIFIED DEMO. During the competition this loop was run interactively: take the current
book, work out what rank it reaches, decide a target. This file is a cut-down repackage of
that loop as a Claude Agent SDK agent, small enough to read in one sitting, built to show the
shape of the thing rather than to be the thing.

What makes it worth reading is the constraint, not the wiring. The agent is structurally
prevented from doing the part it would be bad at.

The capability split is enforced in code, not by trust:
  - Claude reasons and translates your stats into a recommendation.
  - Two deterministic in-process tools do the factual work, and the system prompt forbids
    Claude from estimating a rank itself:
      leaderboard_rank(pnl, sharpe) - rank lookup against the real Round-3 snapshot
      read_benchmark()              - the fitted scoring model + tier->P&L table

Requires: `claude-agent-sdk` (installed), the `claude` CLI on PATH, and Claude auth (existing
Claude Code login or ANTHROPIC_API_KEY).

Run:
    python target_rank_agent.py --pnl 40000 --sharpe 0.12
    python target_rank_agent.py --pnl 40000 --sharpe 0.12 --trades 35 --target "top 25"
"""

import os
import sys
import csv
import asyncio
import argparse

# Windows consoles default to cp1252; Claude may emit unicode (e.g. emoji). Force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from claude_agent_sdk import (
    tool,
    create_sdk_mcp_server,
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)

HERE = os.path.dirname(os.path.abspath(__file__))
LEADERBOARD = os.path.join(HERE, "..", "scoreboard-analysis", "leaderboard_1830.csv")
BENCHMARK = os.path.join(HERE, "..", "scoreboard-analysis", "round3_leaderboard_benchmark.md")
MODEL = "claude-sonnet-5"


def _load_rows():
    with open(LEADERBOARD, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["rank"] = int(r["rank"])
        r["pnl"] = float(r["pnl"])
        r["sharpe"] = float(r["sharpe"])
    return rows


def _band(pnl: float) -> str:
    if pnl < 0:
        return "negative"
    if pnl < 1_000:
        return "0-1k"
    if pnl < 10_000:
        return "1k-10k"
    if pnl < 100_000:
        return "10k-100k"
    return "100k+"


@tool(
    "leaderboard_rank",
    "Project where a result lands using the REAL Round-3 leaderboard snapshot. Returns the "
    "rank range of players in the same P&L band so a target can be set on data, not a guess.",
    {"pnl": float, "sharpe": float},
)
async def leaderboard_rank(args):
    pnl = float(args["pnl"])
    rows = _load_rows()
    band = _band(pnl)
    peers = [r for r in rows if _band(r["pnl"]) == band]
    ranks = sorted(r["rank"] for r in peers)
    median = ranks[len(ranks) // 2] if ranks else None
    text = (
        f"P&L ${pnl:,.0f} falls in the '{band}' band.\n"
        f"Players in that band on the real snapshot: {len(peers)}.\n"
        f"Their rank range: {ranks[0]}-{ranks[-1]} (median ~{median}).\n"
        f"Field size: {len(rows)} (elimination at rank 100)."
    )
    return {"content": [{"type": "text", "text": text}]}


@tool(
    "read_benchmark",
    "Read the fitted scoring model and tier->P&L threshold tables from the real "
    "benchmark analysis. Call this to ground target advice in the fitted model, not memory.",
    {},
)
async def read_benchmark(args):
    with open(BENCHMARK, encoding="utf-8") as f:
        text = f.read()
    return {"content": [{"type": "text", "text": text}]}


async def main():
    ap = argparse.ArgumentParser(description="Target-rank agent: what rank does this book reach, and what should I aim at?")
    ap.add_argument("--pnl", type=float, required=True, help="current P&L in USD (e.g. 40000)")
    ap.add_argument("--sharpe", type=float, required=True, help="current Sharpe (e.g. 0.12)")
    ap.add_argument("--trades", type=int, default=None, help="trades executed (for Best-Sharpe-Award check)")
    ap.add_argument("--target", type=str, default="top 25", help="target tier (default: top 25)")
    args = ap.parse_args()

    server = create_sdk_mcp_server(name="quant", version="1.0.0",
                                   tools=[leaderboard_rank, read_benchmark])
    options = ClaudeAgentOptions(
        model=MODEL,
        mcp_servers={"quant": server},
        allowed_tools=["mcp__quant__leaderboard_rank", "mcp__quant__read_benchmark"],
        system_prompt=(
            "You are a systematic quant research assistant. The human is the lead researcher; "
            "you handle data lookups and translate them into a recommendation. You must NEVER "
            "estimate a leaderboard rank or a tier threshold from your own knowledge - call "
            "leaderboard_rank for any rank claim and read_benchmark for the tier->P&L model. "
            "Be concise and concrete."
        ),
        max_turns=6,
    )

    trades_line = (f" I have executed {args.trades} trades." if args.trades is not None else "")
    prompt = (
        f"My current book: P&L ${args.pnl:,.0f} at Sharpe {args.sharpe}.{trades_line}\n"
        f"Using the real leaderboard and the benchmark model: what rank am I near now, what "
        f"P&L/Sharpe target would clear {args.target}, and is it worth pushing for?"
        + (" Also tell me if I'm eligible for the Best Sharpe Award (needs Top 50, >=30 trades, "
           "no red-line violation)." if args.trades is not None else "")
    )

    print(f"# Target-rank agent (model: {MODEL})")
    print(f"# Your book: P&L ${args.pnl:,.0f} @ Sharpe {args.sharpe}"
          + (f", {args.trades} trades" if args.trades is not None else "") + f" | target: {args.target}\n")
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    print(block.text, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
