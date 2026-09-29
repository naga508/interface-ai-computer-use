from app.artifact.schema import Locator
from app.artifact.sample import (
    build_lookup_member_balance_capability,
)
from app.replay.executor import (
    ReplayExecutor,
)
from app.surface.web import (
    WebSurface,
)


def test_replay_member_balance():

    capability = (
        build_lookup_member_balance_capability()
    )

    surface = WebSurface(
        headless=False
    )

    executor = ReplayExecutor(
        surface=surface
    )

    try:
        result = executor.replay(
            capability=capability,
            params={
                "member_id": "12345"
            },
        )

        print(
            "\nReplay result:"
        )
        print(
            result.model_dump_json(
                indent=2
            )
        )

        assert (
            result.status
            == "SUCCESS"
        )

        assert (
            "savings_balance"
            in result.outputs
        )

        assert (
            "8420.37"
            in result.outputs[
                "savings_balance"
            ]
        )

    finally:
        surface.close()

def test_replay_member_not_found():

    capability = (
        build_lookup_member_balance_capability()
    )

    surface = WebSurface(
        headless=False
    )

    executor = ReplayExecutor(
        surface=surface
    )

    try:
        result = executor.replay(
            capability=capability,
            params={
                "member_id": "99999"
            },
        )

        print(
            "\nBusiness outcome result:"
        )

        print(
            result.model_dump_json(
                indent=2
            )
        )

        assert (
            result.status
            == "BUSINESS_OUTCOME"
        )

        assert (
            result.outcome_code
            == "MEMBER_NOT_FOUND"
        )

        assert (
            result.step_index
            == 3
        )

    finally:
        surface.close()

def test_replay_missing_required_parameter():

    capability = (
        build_lookup_member_balance_capability()
    )

    surface = WebSurface(
        headless=True
    )

    executor = ReplayExecutor(
        surface=surface
    )

    try:
        result = executor.replay(
            capability=capability,
            params={},
        )

        print("\nMissing parameter result:")

        print(
            result.model_dump_json(
                indent=2
            )
        )

        assert result.status == "FAILURE"

        assert (
            "member_id"
            in result.detail
        )

    finally:
        surface.close()

def test_replay_hard_failure_when_locator_cannot_resolve():

    capability = (
        build_lookup_member_balance_capability()
    )

    # Deliberately break the Search button locator.
    search_step = capability.steps[2]

    search_step.target.primary = Locator(
        strategy="css",
        value={
            "selector": "#definitely-missing"
        },
    )

    search_step.target.fallbacks = []

    surface = WebSurface(
        headless=True
    )

    executor = ReplayExecutor(
        surface=surface
    )

    try:
        result = executor.replay(
            capability=capability,
            params={
                "member_id": "12345"
            },
        )

        print("\nHard failure result:")

        print(
            result.model_dump_json(
                indent=2
            )
        )

        assert result.status == "FAILURE"

        assert result.step_index == 3

        assert (
            "locator"
            in result.detail.lower()
        )

    finally:
        surface.close()