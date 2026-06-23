#!/usr/bin/env python3
"""Interactive REPL for the migrant-archive conversational agent (Cero).

Usage:
    python backend/scripts/agent_cli.py

Type 'quit' or 'salir' to exit.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow imports from backend/ and backend/agents/.
_BACK_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACK_DIR))
sys.path.insert(0, str(_BACK_DIR / "agents"))

from dotenv import load_dotenv

load_dotenv()

from agent import create_agent


def main() -> None:
    """Run the interactive Spanish REPL."""
    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)

    agent = create_agent()

    print("Bienvenido a Cero, tu asistente sobre testimonios migratorios.")
    print("Escribe 'quit' o 'salir' para salir.")
    print("─" * 60)

    while True:
        try:
            query = input("Pregunta> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAdiós.")
            break

        if not query:
            continue

        if query.lower() in ("quit", "salir", "q"):
            print("Adiós.")
            break

        result = agent.invoke({"input": query})
        answer = result.get("output", "")
        print(f"\n{answer}\n")
        print("─" * 60)


if __name__ == "__main__":
    main()
