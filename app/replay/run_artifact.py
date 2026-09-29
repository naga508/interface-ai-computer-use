import argparse

from app.artifact.store import ArtifactStore
from app.escalation.session import SessionController
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
        help="Member ID to look up.",
    )

    args = parser.parse_args()

    # -------------------------------------------------
    # LOAD GENERATED CAPABILITY ARTIFACT
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
    # CREATE LIVE BROWSER SESSION
    # -------------------------------------------------

    surface = WebSurface(
        headless=False
    )

    # -------------------------------------------------
    # HUMAN HANDOFF CONTROLLER
    #
    # If replay reaches an unexpected UI state,
    # automation pauses but this SAME browser
    # session stays open.
    # -------------------------------------------------

    session_controller = SessionController(
        interactive=True
    )

    # -------------------------------------------------
    # CREATE DETERMINISTIC REPLAY EXECUTOR
    # -------------------------------------------------

    executor = ReplayExecutor(
        surface=surface,
        session_controller=session_controller,
    )

    try:

        # ---------------------------------------------
        # EXECUTE SAVED CAPABILITY
        # ---------------------------------------------

        result = executor.replay(
            capability=capability,
            params={
                "member_id": args.member_id
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

        print(
            "\nHuman handoffs:"
            f" {session_controller.handoff_count}"
        )

        # A business outcome is expected application
        # behavior, so only a true automation FAILURE
        # should produce a non-zero exit status.
        if result.status == "FAILURE":
            raise SystemExit(1)

    finally:

        surface.close()


if __name__ == "__main__":
    main()