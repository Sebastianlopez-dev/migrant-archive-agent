#!/usr/bin/env python3
"""Interactive REPL for the migrant-archive conversational agent (Cero).

Usage:
    python backend/scripts/agent_cli.py
    python backend/scripts/agent_cli.py "pregunta"

Type 'quit' or 'salir' to exit. Type 'history' to see conversation history.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow the script to find backend/agents/ when run directly.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "backend"))
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "agents"))

from dotenv import load_dotenv

load_dotenv()

from agents.agent import clear_session, create_agent, get_session_history

SESSION_ID = "cli-session"


def _show_history() -> None:
    """Print the current session's conversation history."""
    messages = get_session_history(SESSION_ID).messages
    if not messages:
        print("No hay historial todavia.")
        return
    print()
    for msg in messages:
        role = "Tu" if msg.type == "human" else "Cero"
        print(f"[{role}] {msg.content}")
        print()
    print(f"({len(messages)} messages)")


def main() -> None:
    """Run the interactive Spanish REPL or single-question mode."""
    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)

    agent = create_agent(verbose=True)
    args = sys.argv[1:]

    # ── Single-question mode ──────────────────────────────────────
    if args:
        question = " ".join(args)
        try:
            result = agent.invoke(
                {"input": question},
                config={"configurable": {"session_id": SESSION_ID}},
            )
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
        print(result["output"])
        return

    # ── REPL mode ─────────────────────────────────────────────────
    print("=" * 50)
    print("\nHi, I'm Cero - The Plataforma Cero's Youtube Q&A Agent.")
    print("=" * 50)
    print("\nCommands: 'history' to check memory, 'q'/'quit'/'exit' to finish.")
    print("=" * 50)
    print("\nAsk me anything about the archived videos:\n")

    try:
        while True:
            try:
                question = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nAdios.")
                break

            if not question:
                continue
            if question.lower() in ("q", "quit", "salir", "exit"):
                print("Adios.")
                break
            if question.lower() == "history":
                _show_history()
                continue

            try:
                result = agent.invoke(
                    {"input": question},
                    config={"configurable": {"session_id": SESSION_ID}},
                )
            except Exception as e:
                print(f"Error: {e}. Try again later.")
                continue
            print(result["output"])
            print()
    finally:
        clear_session(SESSION_ID)


if __name__ == "__main__":
    main()
