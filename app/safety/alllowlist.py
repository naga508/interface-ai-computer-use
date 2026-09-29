from urllib.parse import urlparse

from pydantic import BaseModel

from app.surface.base import Action


class SafetyDecision(BaseModel):
    allowed: bool
    reason: str


class SafetyPolicy(BaseModel):
    allowed_hosts: set[str] = {
        "127.0.0.1",
        "localhost",
    }

    allowed_actions: set[str] = {
        "navigate",
        "click",
        "type",
        "read",
        "wait_for",
    }

    def check(
        self,
        action: Action,
        current_url: str,
    ) -> SafetyDecision:

        # First: is this action type allowed?
        if action.action not in self.allowed_actions:
            return SafetyDecision(
                allowed=False,
                reason=(
                    f"Action '{action.action}' "
                    "is not permitted."
                ),
            )

        # For navigation, check the destination URL.
        if action.action == "navigate":
            if not action.value:
                return SafetyDecision(
                    allowed=False,
                    reason="Navigation URL is missing.",
                )

            url_to_check = action.value

        else:
            # For every other action, make sure
            # the current page itself is allowed.
            url_to_check = current_url

        parsed = urlparse(url_to_check)

        host = parsed.hostname

        if host not in self.allowed_hosts:
            return SafetyDecision(
                allowed=False,
                reason=(
                    f"Host '{host}' is not "
                    "in the allowlist."
                ),
            )

        return SafetyDecision(
            allowed=True,
            reason="Action permitted.",
        )