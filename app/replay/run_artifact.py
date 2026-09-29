import argparse

from app.artifact.store import ArtifactStore
from app.replay.executor import ReplayExecutor
from app.surface.web import WebSurface


def main():

    # -------------------------------------------------
    # COMMAND-LINE INPUT
    # -------------------------------------------------

    parser = argparse.ArgumentParser(
        description=(
            "Replay a recorded capability "
            "without using an LLM."
        )
    )

    parser.add_argument(
        "member_id",
        help=(
            "Member ID to look up."
        ),
    )

    args = parser.parse_args()

    # -------------------------------------------------
    # LOAD GENERATED ARTIFACT
    # -------------------------------------------------

    store = ArtifactStore()

    capability = store.load(
        "lookup_member_balance.json"
    )

    print(
        "\n================================="
    )

    print(
        "DETERMINISTIC REPLAY"
    )

    print(
        "================================="
    )

    print(
        f"\nCapability: {capability.name}"
    )

    print(
        f"Member ID: {args.member_id}"
    )

    print(
        "\nLLM usage: NONE"
    )

    # -------------------------------------------------
    # CREATE BROWSER SURFACE
    # -------------------------------------------------

    surface = WebSurface(
        headless=False
    )

    executor = ReplayExecutor(
        surface=surface
    )

    try:

        # ---------------------------------------------
        # EXECUTE SAVED CAPABILITY
        # ---------------------------------------------

        result = executor.replay(
            capability=capability,
            params={
                "member_id": (
                    args.member_id
                )
            },
        )

        print(
            "\n================================="
        )

        print(
            "REPLAY RESULT"
        )

        print(
            "=================================\n"
        )

        print(
            result.model_dump_json(
                indent=2
            )
        )

        # Non-zero process exit for actual failures.
        # A business outcome is still an expected
        # application result, not an automation crash.
        if result.status == "FAILURE":
            raise SystemExit(1)

    finally:

        surface.close()


if __name__ == "__main__":
    main()