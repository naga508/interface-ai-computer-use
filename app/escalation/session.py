from enum import Enum
from typing import Callable

from pydantic import BaseModel

from app.surface.base import Surface


class SessionMode(str, Enum):
    AUTOMATION = "AUTOMATION"
    HUMAN = "HUMAN"


class HandoffRequest(BaseModel):
    reason: str
    step_index: int | None = None

    url: str
    accessibility_snapshot: str


HumanCallback = Callable[
    [Surface, HandoffRequest],
    None,
]


class SessionController:
    def __init__(
        self,
        interactive: bool = True,
        human_callback: HumanCallback | None = None,
    ):
        self.mode = SessionMode.AUTOMATION

        self.interactive = interactive

        self.human_callback = human_callback

        self.handoffs: list[
            HandoffRequest
        ] = []

    @property
    def handoff_count(self) -> int:
        return len(self.handoffs)

    def handoff(
        self,
        surface: Surface,
        reason: str,
        step_index: int | None = None,
    ) -> HandoffRequest:

        observation = surface.perceive()

        request = HandoffRequest(
            reason=reason,
            step_index=step_index,
            url=observation.url,
            accessibility_snapshot=(
                observation.accessibility_snapshot
            ),
        )

        self.handoffs.append(request)

        self.mode = SessionMode.HUMAN

        print(
            "\n================================="
        )
        print(
            "HUMAN HANDOFF REQUIRED"
        )
        print(
            "================================="
        )

        print(
            f"\nReason: {reason}"
        )

        print(
            f"Current URL: {observation.url}"
        )

        print(
            "\nAutomation is paused."
        )

        print(
            "The existing browser session "
            "remains open."
        )

        if self.human_callback is not None:

            self.human_callback(
                surface,
                request,
            )

        elif self.interactive:

            input(
                "\nComplete the required action "
                "in the browser, then press "
                "ENTER here to resume automation..."
            )

        else:

            raise RuntimeError(
                "Human handoff was requested, "
                "but no interactive operator or "
                "human callback is available."
            )

        self.mode = SessionMode.AUTOMATION

        print(
            "\nHuman handoff complete."
        )

        print(
            "Automation is resuming..."
        )

        return request