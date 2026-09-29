from app.agent.discovery import (
    AgentDecision,
    DiscoveryAgent,
)
from app.surface.base import (
    Action,
    Target,
)
from app.surface.web import WebSurface


class FakeDecisionProvider:
    def decide(
        self,
        goal,
        observation,
        history,
    ):

        step = len(history)

        if step == 0:
            return AgentDecision(
                reasoning=(
                    "Navigate to MockCore."
                ),
                action=Action(
                    action="navigate",
                    value=(
                        "http://127.0.0.1:5000"
                    ),
                ),
            )

        if step == 1:
            return AgentDecision(
                reasoning=(
                    "Enter member 12345."
                ),
                action=Action(
                    action="type",
                    target=Target(
                        strategy="label",
                        value="Member ID",
                    ),
                    value="12345",
                ),
            )

        if step == 2:
            return AgentDecision(
                reasoning=(
                    "Submit the search."
                ),
                action=Action(
                    action="click",
                    target=Target(
                        strategy="role",
                        role="button",
                        value="Search",
                    ),
                ),
            )

        if step == 3:
            return AgentDecision(
                reasoning=(
                    "Read the savings balance."
                ),
                action=Action(
                    action="read",
                    target=Target(
                        strategy="text",
                        value="Savings Balance",
                    ),
                ),
            )

        return AgentDecision(
            reasoning=(
                "The requested information "
                "has been found."
            ),
            goal_complete=True,
            result="$8420.37",
        )


def test_discovery_loop():

    surface = WebSurface(
        headless=False
    )

    provider = FakeDecisionProvider()

    agent = DiscoveryAgent(
        surface=surface,
        decision_provider=provider,
    )

    try:
        result = agent.run(
            goal=(
                "Look up member 12345 "
                "and read their savings balance."
            )
        )

        print(
            result.model_dump_json(
                indent=2
            )
        )

        assert result.success is True

        assert (
            result.result
            == "$8420.37"
        )

    finally:
        surface.close()