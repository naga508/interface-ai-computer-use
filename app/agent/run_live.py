import os
from pathlib import Path

from dotenv import load_dotenv

from app.agent.discovery import (
    DiscoveryAgent,
)
from app.agent.gemini_provider import (
    GeminiDecisionProvider,
)
from app.surface.web import WebSurface


def main():

    # ---------------------------------------------
    # LOAD LOCAL ENVIRONMENT VARIABLES
    # ---------------------------------------------

    load_dotenv()

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing "
            "from the .env file."
        )

    model = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.5-flash-lite",
    )

    print(
        "\n================================="
    )
    print(
        "LIVE GEMINI DISCOVERY"
    )
    print(
        "================================="
    )

    print(
        f"\nModel: {model}"
    )

    # ---------------------------------------------
    # USER GOAL
    # ---------------------------------------------

    goal = (
        "Open MockCore at "
        "http://127.0.0.1:5000, "
        "look up member 12345, "
        "and return their savings balance."
    )

    print(
        "\nGoal:"
    )

    print(goal)

    # ---------------------------------------------
    # CREATE BROWSER SURFACE
    # ---------------------------------------------

    surface = WebSurface(
        headless=False
    )

    # ---------------------------------------------
    # CREATE REAL GEMINI PROVIDER
    # ---------------------------------------------

    provider = (
        GeminiDecisionProvider(
            model=model
        )
    )

    # ---------------------------------------------
    # CREATE DISCOVERY AGENT
    # ---------------------------------------------

    agent = DiscoveryAgent(
        surface=surface,
        decision_provider=provider,
        max_steps=10,
    )

    try:

        # -----------------------------------------
        # RUN REAL MODEL-DRIVEN DISCOVERY
        # -----------------------------------------

        result = agent.run(
            goal=goal
        )

        print(
            "\n================================="
        )

        print(
            "DISCOVERY RESULT"
        )

        print(
            "=================================\n"
        )

        print(
            result.model_dump_json(
                indent=2
            )
        )

        # -----------------------------------------
        # SAVE DISCOVERY EVIDENCE
        # -----------------------------------------

        evidence_directory = Path(
            "evidence"
        )

        evidence_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        evidence_path = (
            evidence_directory
            / "live_discovery_run.json"
        )

        evidence_path.write_text(
            result.model_dump_json(
                indent=2
            ),
            encoding="utf-8",
        )

        print(
            "\nEvidence saved to:"
        )

        print(
            evidence_path
        )

        # Return non-zero exit status
        # if discovery failed.
        if not result.success:
            raise SystemExit(1)

    finally:

        surface.close()


if __name__ == "__main__":
    main()