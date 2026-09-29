from app.artifact.store import ArtifactStore
from app.escalation.session import (
    SessionController,
    SessionMode,
)
from app.replay.executor import ReplayExecutor
from app.surface.base import (
    Action,
    Target,
)
from app.surface.web import WebSurface


def test_human_handoff_preserves_same_session():

    # -------------------------------------------------
    # LOAD THE GENERATED CAPABILITY ARTIFACT
    # -------------------------------------------------

    store = ArtifactStore()

    capability = store.load(
        "lookup_member_balance.json"
    )

    # -------------------------------------------------
    # CREATE ONE BROWSER SESSION
    # -------------------------------------------------

    surface = WebSurface(
        headless=True
    )

    # -------------------------------------------------
    # SIMULATED HUMAN OPERATOR
    #
    # During a real demo, the human would manually
    # click Continue in the browser.
    #
    # In the automated test, this callback simulates
    # the human action while using the SAME Surface.
    # -------------------------------------------------

    def human_operator(
        same_surface,
        request,
    ):

        assert (
            "Manual Verification Required"
            in request.accessibility_snapshot
        )

        assert (
            request.step_index == 3
        )

        result = same_surface.act(
            Action(
                action="click",
                target=Target(
                    strategy="role",
                    role="link",
                    value="Continue",
                ),
            )
        )

        assert result.success is True

    # -------------------------------------------------
    # CREATE SESSION CONTROLLER
    # -------------------------------------------------

    controller = SessionController(
        interactive=False,
        human_callback=human_operator,
    )

    # -------------------------------------------------
    # CREATE REPLAY EXECUTOR
    # -------------------------------------------------

    executor = ReplayExecutor(
        surface=surface,
        session_controller=controller,
    )

    try:

        # Member 33333 deliberately produces
        # "Manual Verification Required".
        result = executor.replay(
            capability=capability,
            params={
                "member_id": "33333"
            },
        )

        print(
            "\nHuman handoff result:"
        )

        print(
            result.model_dump_json(
                indent=2
            )
        )

        # -------------------------------------------------
        # VERIFY REPLAY RESUMED SUCCESSFULLY
        # -------------------------------------------------

        assert (
            result.status
            == "SUCCESS"
        )

        assert (
            "savings_balance"
            in result.outputs
        )

        assert (
            "7250.40"
            in result.outputs[
                "savings_balance"
            ]
        )

        # Exactly one escalation occurred.
        assert (
            controller.handoff_count
            == 1
        )

        # After the human finishes,
        # control returns to automation.
        assert (
            controller.mode
            == SessionMode.AUTOMATION
        )

        # Confirm that the handoff happened
        # at the expected replay step.
        assert (
            controller.handoffs[0].step_index
            == 3
        )

    finally:

        surface.close()