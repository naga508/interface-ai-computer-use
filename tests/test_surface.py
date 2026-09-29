from app.surface.base import Action, Target
from app.surface.web import WebSurface


def test_web_surface_member_lookup():

    surface = WebSurface(
        headless=False
    )

    try:

        # Step 1: Navigate to MockCore
        result = surface.act(
            Action(
                action="navigate",
                value="http://127.0.0.1:5000",
            )
        )

        assert result.success

        # Observe the search page
        observation = surface.perceive()

        print("\n--- INITIAL OBSERVATION ---")
        print(observation.url)
        print(observation.title)
        print(
            observation.accessibility_snapshot
        )

        # Step 2: Enter member ID
        result = surface.act(
            Action(
                action="type",
                target=Target(
                    strategy="label",
                    value="Member ID",
                ),
                value="12345",
            )
        )

        assert result.success

        # Step 3: Click Search
        result = surface.act(
            Action(
                action="click",
                target=Target(
                    strategy="role",
                    role="button",
                    value="Search",
                ),
            )
        )

        assert result.success

        # Step 4: Wait for result page
        result = surface.act(
            Action(
                action="wait_for",
                target=Target(
                    strategy="text",
                    value="Member Details",
                ),
            )
        )

        assert result.success

        # Step 5: Read savings balance
        result = surface.act(
            Action(
                action="read",
                target=Target(
                    strategy="text",
                    value="Savings Balance",
                ),
            )
        )

        assert result.success

        print("\n--- RESULT ---")
        print(result.data)

        assert "$8420.37" in result.data

        # Observe final state
        observation = surface.perceive()

        print("\n--- FINAL OBSERVATION ---")
        print(observation.url)
        print(
            observation.accessibility_snapshot
        )

    finally:
        surface.close()