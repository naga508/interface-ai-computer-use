import base64
import json
import os
from pathlib import Path

from google import genai

from app.agent.discovery import AgentDecision
from app.surface.base import Observation


SYSTEM_PROMPT = """
You are the decision component of a computer-use discovery agent.

You control a mock banking web application through a restricted
Surface API.

Your job is to inspect the current UI and choose exactly ONE next
action that moves toward the user's goal.

AVAILABLE ACTIONS:
- navigate
- click
- type
- read
- wait_for

AVAILABLE TARGET STRATEGIES:
- label
- role
- text

RULES:

1. Choose exactly one action per response.

2. Base the decision only on:
   - the user's goal,
   - the current accessibility observation,
   - the current screenshot,
   - and recent action history.

3. Prefer robust semantic targets.

Preferred order:
   - accessible role and name
   - form label
   - visible text

4. Never invent a UI element that is not visible in the
   accessibility observation or screenshot.

5. Role target example:

   strategy = "role"
   value = "Search"
   role = "button"

6. Label target example:

   strategy = "label"
   value = "Member ID"
   role = null

7. Text target example:

   strategy = "text"
   value = "Savings Balance"
   role = null

8. For navigation:

   action = "navigate"
   target = null
   value = URL

9. For typing:

   action = "type"
   target = input element
   value = text to enter

10. For click, read, and wait_for:

   value should normally be null.

11. IMPORTANT: If the user's goal asks you to return a value from
    the UI, seeing that value in the accessibility observation or
    screenshot is NOT sufficient to complete the goal.

    You MUST perform a "read" action targeting the UI element that
    contains the requested value.

12. Only set goal_complete=true after a previous successful "read"
    action appears in RECENT ACTION HISTORY and its action_result.data
    contains the requested information.

13. If the requested value is visible now but has not yet been read:

    goal_complete = false
    action = "read"
    target = the element containing the requested value
    result = null

14. After that read action succeeds, on the NEXT decision:

    goal_complete = true
    action = null
    result = the value returned by the successful read action.

15. Do not perform unrelated or irreversible actions.
"""


class GeminiDecisionProvider:
    def __init__(
        self,
        model: str | None = None,
    ):
        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. "
                "Add it to your .env file."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model = (
            model
            or os.getenv(
                "GEMINI_MODEL",
                "gemini-3.5-flash-lite",
            )
        )

    def decide(
        self,
        goal: str,
        observation: Observation,
        history: list[dict],
    ) -> AgentDecision:

        # Only send the most recent history
        # so prompts remain compact.
        recent_history = history[-5:]

        prompt = f"""
USER GOAL:
{goal}

CURRENT URL:
{observation.url}

CURRENT PAGE TITLE:
{observation.title}

CURRENT ACCESSIBILITY OBSERVATION:
{observation.accessibility_snapshot}

RECENT ACTION HISTORY:
{json.dumps(recent_history, indent=2)}

Choose exactly one next action.

IMPORTANT:

If the requested value is visible in the current UI but no successful
read action in RECENT ACTION HISTORY has retrieved it yet, choose a
read action now.

Only mark goal_complete=true when RECENT ACTION HISTORY contains a
successful read action whose action_result.data contains the requested
information.
"""

        # Start with the textual UI observation.
        interaction_input = [
            {
                "type": "text",
                "text": prompt,
            }
        ]

        # Add screenshot when available.
        if observation.screenshot_path:

            screenshot_path = Path(
                observation.screenshot_path
            )

            if screenshot_path.exists():

                screenshot_bytes = (
                    screenshot_path.read_bytes()
                )

                screenshot_base64 = (
                    base64.b64encode(
                        screenshot_bytes
                    ).decode("utf-8")
                )

                interaction_input.append(
                    {
                        "type": "image",
                        "data": screenshot_base64,
                        "mime_type": "image/png",
                    }
                )

        interaction = (
            self.client.interactions.create(
                model=self.model,

                system_instruction=(
                    SYSTEM_PROMPT
                ),

                input=interaction_input,

                response_format={
                    "type": "text",
                    "mime_type": (
                        "application/json"
                    ),
                    "schema": (
                        AgentDecision
                        .model_json_schema()
                    ),
                },
            )
        )

        if not interaction.output_text:
            raise RuntimeError(
                "Gemini returned an empty "
                "decision."
            )

        try:
            decision = (
                AgentDecision
                .model_validate_json(
                    interaction.output_text
                )
            )

        except Exception as exc:
            raise RuntimeError(
                "Gemini returned an invalid "
                "AgentDecision.\n\n"
                "Raw response:\n"
                f"{interaction.output_text}"
            ) from exc

        return decision