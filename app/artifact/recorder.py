from typing import Any

from pydantic import BaseModel

from app.agent.discovery import DiscoveryResult
from app.artifact.schema import (
    Capability,
    CapabilityMetadata,
    Checkpoint,
    ElementTarget,
    ErrorRule,
    Locator,
    OutputSpec,
    ParamRef,
    ParamSpec,
    RetryPolicy,
    Step,
    TargetSpec,
)


class RecorderConfig(BaseModel):
    capability_id: str
    capability_name: str
    description: str

    vendor_app_id: str
    version_range: str
    base_url_pattern: str

    input_name: str
    input_description: str
    input_example: str
    input_sensitive: bool = True

    output_name: str
    output_description: str

    success_text: str

    # Stable text used for the output target.
    output_target_text: str

    # Optional runtime states learned/configured
    # for production replay.
    business_outcome_text: str | None = None
    business_outcome_code: str | None = None

    recoverable_text: str | None = None

    retry_max_attempts: int = 1
    retry_backoff_ms: int = 0

    model_used: str | None = None
    discovery_run_id: str | None = None


class CapabilityRecorder:
    def record(
        self,
        discovery: DiscoveryResult,
        config: RecorderConfig,
    ) -> Capability:

        if not discovery.success:
            raise ValueError(
                "Cannot record capability from "
                "an unsuccessful discovery run."
            )

        recorded_steps: list[Step] = []

        for history_item in discovery.steps:

            decision = history_item.get(
                "decision",
                {}
            )

            action_data = decision.get(
                "action"
            )

            # Final goal-complete decision has
            # no browser action.
            if action_data is None:
                continue

            step = self._record_step(
                step_index=len(recorded_steps) + 1,
                action_data=action_data,
                config=config,
            )

            recorded_steps.append(step)

        if not recorded_steps:
            raise ValueError(
                "Discovery run contained "
                "no executable actions."
            )

        self._add_search_checkpoint_and_errors(
            recorded_steps=recorded_steps,
            config=config,
        )

        return Capability(
            capability_id=(
                config.capability_id
            ),
            name=(
                config.capability_name
            ),
            description=(
                config.description
            ),

            target=TargetSpec(
                vendor_app_id=(
                    config.vendor_app_id
                ),
                version_range=(
                    config.version_range
                ),
                base_url_pattern=(
                    config.base_url_pattern
                ),
            ),

            input_parameters=[
                ParamSpec(
                    name=config.input_name,
                    type="string",
                    required=True,
                    description=(
                        config.input_description
                    ),
                    example=(
                        config.input_example
                    ),
                    sensitive=(
                        config.input_sensitive
                    ),
                )
            ],

            outputs=[
                OutputSpec(
                    name=config.output_name,
                    type="string",
                    description=(
                        config.output_description
                    ),
                )
            ],

            steps=recorded_steps,

            success_condition=Checkpoint(
                type="text_present",
                spec={
                    "text": (
                        config.success_text
                    )
                },
            ),

            approval_state="draft",

            metadata=CapabilityMetadata(
                model_used=(
                    config.model_used
                ),
                discovery_run_id=(
                    config.discovery_run_id
                ),
            ),
        )

    def _record_step(
        self,
        step_index: int,
        action_data: dict[str, Any],
        config: RecorderConfig,
    ) -> Step:

        action_name = action_data[
            "action"
        ]

        value = action_data.get(
            "value"
        )

        target_data = action_data.get(
            "target"
        )

        # -----------------------------------------
        # NAVIGATE
        # -----------------------------------------

        if action_name == "navigate":

            return Step(
                index=step_index,
                intent=(
                    "Open the target application."
                ),
                action="navigate",
                value=value,
            )

        if target_data is None:
            raise ValueError(
                f"Action '{action_name}' "
                "requires a target."
            )

        # -----------------------------------------
        # TYPE
        # -----------------------------------------

        if action_name == "type":

            target = (
                self._convert_target(
                    action_name=action_name,
                    target_data=target_data,
                    config=config,
                )
            )

            # The concrete discovery value becomes
            # a reusable runtime parameter.
            if (
                str(value)
                == config.input_example
            ):
                recorded_value = ParamRef(
                    param=config.input_name
                )
            else:
                recorded_value = value

            return Step(
                index=step_index,
                intent=(
                    f"Enter {config.input_name}."
                ),
                action="type",
                target=target,
                value=recorded_value,
            )

        # -----------------------------------------
        # CLICK
        # -----------------------------------------

        if action_name == "click":

            target = (
                self._convert_target(
                    action_name=action_name,
                    target_data=target_data,
                    config=config,
                )
            )

            return Step(
                index=step_index,
                intent=(
                    "Submit the lookup."
                ),
                action="click",
                target=target,
            )

        # -----------------------------------------
        # READ
        # -----------------------------------------

        if action_name == "read":

            # Important:
            # do NOT preserve the discovered
            # dynamic value such as:
            #
            # Savings Balance: $8420.37
            #
            # Use a stable semantic target instead.
            target = ElementTarget(
                description=(
                    f"{config.output_name} field."
                ),

                reasoning=(
                    "Use stable visible label text "
                    "rather than a discovered "
                    "member-specific value."
                ),

                primary=Locator(
                    strategy="text",
                    value={
                        "text": (
                            config.output_target_text
                        )
                    },
                ),
            )

            return Step(
                index=step_index,
                intent=(
                    f"Read {config.output_name}."
                ),
                action="read",
                target=target,
                output_name=(
                    config.output_name
                ),
            )

        # -----------------------------------------
        # WAIT
        # -----------------------------------------

        if action_name == "wait_for":

            target = (
                self._convert_target(
                    action_name=action_name,
                    target_data=target_data,
                    config=config,
                )
            )

            return Step(
                index=step_index,
                intent=(
                    "Wait for the required "
                    "UI state."
                ),
                action="wait_for",
                target=target,
            )

        raise ValueError(
            "Unsupported discovered action: "
            f"{action_name}"
        )

    def _convert_target(
        self,
        action_name: str,
        target_data: dict[str, Any],
        config: RecorderConfig,
    ) -> ElementTarget:

        strategy = target_data[
            "strategy"
        ]

        value = target_data[
            "value"
        ]

        role = target_data.get(
            "role"
        )

        # -----------------------------------------
        # ROLE
        # -----------------------------------------

        if strategy == "role":

            return ElementTarget(
                description=(
                    f"{role or 'UI'} element "
                    f"named '{value}'."
                ),

                reasoning=(
                    "Accessible role and name "
                    "provide a semantic locator."
                ),

                primary=Locator(
                    strategy="a11y_role_name",
                    value={
                        "role": role,
                        "name": value,
                    },
                ),

                fallbacks=[
                    Locator(
                        strategy="text",
                        value={
                            "text": value
                        },
                    )
                ],
            )

        # -----------------------------------------
        # LABEL
        # -----------------------------------------

        if strategy == "label":

            # In our current discovery vocabulary,
            # a label target used by a type action
            # represents a textbox.
            if action_name == "type":

                return ElementTarget(
                    description=(
                        f"Input labeled '{value}'."
                    ),

                    reasoning=(
                        "The form label is semantic "
                        "and more robust than "
                        "DOM position."
                    ),

                    primary=Locator(
                        strategy=(
                            "a11y_role_name"
                        ),
                        value={
                            "role": "textbox",
                            "name": value,
                        },
                    ),
                )

            return ElementTarget(
                description=(
                    f"Element labeled '{value}'."
                ),

                reasoning=(
                    "Visible label identifies "
                    "the target."
                ),

                primary=Locator(
                    strategy="text",
                    value={
                        "text": value
                    },
                ),
            )

        # -----------------------------------------
        # TEXT
        # -----------------------------------------

        if strategy == "text":

            return ElementTarget(
                description=(
                    f"Element containing "
                    f"'{value}'."
                ),

                reasoning=(
                    "Visible text identifies "
                    "the target."
                ),

                primary=Locator(
                    strategy="text",
                    value={
                        "text": value
                    },
                ),
            )

        raise ValueError(
            "Unsupported target strategy: "
            f"{strategy}"
        )

    def _add_search_checkpoint_and_errors(
        self,
        recorded_steps: list[Step],
        config: RecorderConfig,
    ) -> None:

        # Locate the click that submits the lookup.
        click_step = next(
            (
                step
                for step in recorded_steps
                if step.action == "click"
            ),
            None,
        )

        if click_step is None:
            return

        click_step.checkpoint = Checkpoint(
            type="text_present",
            spec={
                "text": (
                    config.success_text
                )
            },
        )

        error_rules: list[
            ErrorRule
        ] = []

        # Recoverable runtime condition.
        if config.recoverable_text:

            error_rules.append(
                ErrorRule(
                    match=Checkpoint(
                        type="text_present",
                        spec={
                            "text": (
                                config
                                .recoverable_text
                            )
                        },
                    ),
                    classify="recoverable",
                    recovery="retry",
                )
            )

        # Expected business outcome.
        if (
            config.business_outcome_text
            and
            config.business_outcome_code
        ):

            error_rules.append(
                ErrorRule(
                    match=Checkpoint(
                        type="text_present",
                        spec={
                            "text": (
                                config
                                .business_outcome_text
                            )
                        },
                    ),
                    classify=(
                        "business_outcome"
                    ),
                    outcome_code=(
                        config
                        .business_outcome_code
                    ),
                )
            )

        click_step.on_error = error_rules

        click_step.retry = RetryPolicy(
            max_attempts=(
                config.retry_max_attempts
            ),
            backoff_ms=(
                config.retry_backoff_ms
            ),
        )