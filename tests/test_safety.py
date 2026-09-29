from app.safety.allowlist import SafetyPolicy
from app.surface.base import Action


def test_localhost_navigation_is_allowed():
    policy = SafetyPolicy()

    action = Action(
        action="navigate",
        value="http://127.0.0.1:5000",
    )

    decision = policy.check(
        action=action,
        current_url="about:blank",
    )

    assert decision.allowed is True


def test_external_navigation_is_blocked():
    policy = SafetyPolicy()

    action = Action(
        action="navigate",
        value="https://example.com",
    )

    decision = policy.check(
        action=action,
        current_url="about:blank",
    )

    assert decision.allowed is False
    assert "allowlist" in decision.reason.lower()


def test_localhost_action_is_allowed():
    policy = SafetyPolicy()

    action = Action(
        action="click",
    )

    decision = policy.check(
        action=action,
        current_url="http://127.0.0.1:5000",
    )

    assert decision.allowed is True