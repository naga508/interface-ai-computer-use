from typing import Protocol

from pydantic import BaseModel

from app.surface.base import (
    Action,
    Observation,
    Surface,
)


class AgentDecision(BaseModel):
    action: Action | None = None

    goal_complete: bool = False

    reasoning: str

    result: str | None = None


class DecisionProvider(Protocol):
    def decide(
        self,
        goal: str,
        observation: Observation,
        history: list[dict],
    ) -> AgentDecision:
        ...


class DiscoveryResult(BaseModel):
    success: bool

    result: str | None = None

    steps: list[dict]

    error: str | None = None


class DiscoveryAgent:
    def __init__(
        self,
        surface: Surface,
        decision_provider: DecisionProvider,
        max_steps: int = 15,
    ):
        self.surface = surface
        self.decision_provider = decision_provider
        self.max_steps = max_steps

    def run(
        self,
        goal: str,
    ) -> DiscoveryResult:

        history: list[dict] = []

        for step_number in range(
            1,
            self.max_steps + 1,
        ):
            observation = (
                self.surface.perceive()
            )

            decision = (
                self.decision_provider.decide(
                    goal=goal,
                    observation=observation,
                    history=history,
                )
            )

            history.append(
                {
                    "step": step_number,
                    "observation": (
                        observation.model_dump()
                    ),
                    "decision": (
                        decision.model_dump()
                    ),
                }
            )

            if decision.goal_complete:
                return DiscoveryResult(
                    success=True,
                    result=decision.result,
                    steps=history,
                )

            if decision.action is None:
                return DiscoveryResult(
                    success=False,
                    steps=history,
                    error=(
                        "Decision provider did "
                        "not return an action."
                    ),
                )

            action_result = self.surface.act(
                decision.action
            )

            history[-1][
                "action_result"
            ] = action_result.model_dump()

            if not action_result.success:
                return DiscoveryResult(
                    success=False,
                    steps=history,
                    error=action_result.error,
                )

        return DiscoveryResult(
            success=False,
            steps=history,
            error=(
                "Discovery exceeded "
                f"{self.max_steps} steps."
            ),
        )