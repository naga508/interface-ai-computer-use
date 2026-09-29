from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.safety.allowlist import SafetyPolicy
from app.surface.base import Action, ActionResult, Observation, Surface, Target


class WebSurface(Surface):

    def __init__(self, headless: bool = False, safety_policy: SafetyPolicy | None = None):
        self.safety_policy = safety_policy or SafetyPolicy()

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def _resolve_target(self, target: Target):

        if target.strategy == "label":
            return self.page.get_by_label(target.value)

        if target.strategy == "role":
            if not target.role:
                raise ValueError(
                    "Role must be provided when using role strategy."
                )

            return self.page.get_by_role(
                target.role,
                name=target.value,
            )

        if target.strategy == "text":
            return self.page.get_by_text(
                target.value,
                exact=False,
            )

        raise ValueError(
            f"Unsupported target strategy: {target.strategy}"
        )

    def perceive(self) -> Observation:

        screenshot_directory = Path("evidence/screenshots")

        screenshot_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        screenshot_path = (
            screenshot_directory
            / f"observation_{timestamp}.png"
        )

        self.page.screenshot(
            path=str(screenshot_path),
            full_page=True,
        )

        try:
            accessibility_snapshot = (
                self.page.locator("body").aria_snapshot()
            )

        except Exception:
            accessibility_snapshot = (
                self.page.locator("body").inner_text()
            )

        return Observation(
            url=self.page.url,
            title=self.page.title(),
            accessibility_snapshot=accessibility_snapshot,
            screenshot_path=str(screenshot_path),
        )

    def act(self, action: Action) -> ActionResult:

        try:
            safety_decision = self.safety_policy.check(
                action=action,
                current_url=self.page.url,
            )

            if not safety_decision.allowed:
                return ActionResult(
                    success=False,
                    error=(
                        "SAFETY_BLOCKED: "
                        + safety_decision.reason
                    ),
                )

            if action.action == "navigate":

                if not action.value:
                    raise ValueError(
                        "Navigate action requires a URL."
                    )

                self.page.goto(action.value)

                return ActionResult(
                    success=True
                )

            if action.target is None:
                raise ValueError(
                    f"{action.action} action requires a target."
                )

            locator = self._resolve_target(
                action.target
            )

            if action.action == "type":

                if action.value is None:
                    raise ValueError(
                        "Type action requires a value."
                    )

                locator.fill(action.value)

                return ActionResult(
                    success=True
                )

            if action.action == "click":

                locator.click()

                return ActionResult(
                    success=True
                )

            if action.action == "read":

                text = locator.inner_text()

                return ActionResult(
                    success=True,
                    data=text,
                )

            if action.action == "wait_for":

                locator.wait_for()

                return ActionResult(
                    success=True
                )

            raise ValueError(
                f"Unsupported action: {action.action}"
            )

        except Exception as exc:

            return ActionResult(
                success=False,
                error=str(exc),
            )

    def close(self) -> None:

        self.context.close()
        self.browser.close()
        self.playwright.stop()