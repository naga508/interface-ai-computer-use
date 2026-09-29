from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel


class Target(BaseModel):
    strategy: Literal["label", "role", "text"]
    value: str
    role: str | None = None


class Action(BaseModel):
    action: Literal[
        "navigate",
        "click",
        "type",
        "read",
        "wait_for",
    ]

    target: Target | None = None
    value: str | None = None


class Observation(BaseModel):
    url: str
    title: str
    accessibility_snapshot: str
    screenshot_path: str | None = None


class ActionResult(BaseModel):
    success: bool
    data: str | None = None
    error: str | None = None


class Surface(ABC):

    @abstractmethod
    def perceive(self) -> Observation:
        """Observe the current state of the application."""
        pass

    @abstractmethod
    def act(self, action: Action) -> ActionResult:
        """Perform an action on the application."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the surface and release resources."""
        pass