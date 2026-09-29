from typing import Any, Literal

from pydantic import BaseModel, Field

from app.artifact.schema import (
    Capability,
    Checkpoint,
    ElementTarget,
    Locator,
    ParamRef,
    Step,
)
from app.surface.base import (
    Action,
    ActionResult,
    Surface,
    Target,
)


ReplayStatus = Literal[
    "SUCCESS",
    "BUSINESS_OUTCOME",
    "FAILURE",
]


class ReplayResult(BaseModel):
    status: ReplayStatus

    outputs: dict[str, Any] = Field(
        default_factory=dict
    )

    outcome_code: str | None = None

    detail: str | None = None

    step_index: int | None = None

    expected: str | None = None

    observed: str | None = None


class ReplayExecutor:
    def __init__(
        self,
        surface: Surface,
    ):
        self.surface = surface

    # -----------------------------------------------------
    # PUBLIC ENTRY POINT
    # -----------------------------------------------------

    def replay(
        self,
        capability: Capability,
        params: dict[str, Any],
    ) -> ReplayResult:

        validation_error = self._validate_params(
            capability=capability,
            params=params,
        )

        if validation_error:
            return ReplayResult(
                status="FAILURE",
                detail=validation_error,
            )

        outputs: dict[str, Any] = {}

        for step in capability.steps:

            result = self._execute_step(
                step=step,
                params=params,
            )

            if not result.success:
                return ReplayResult(
                    status="FAILURE",
                    step_index=step.index,
                    detail=result.error,
                )

            if (
                step.action == "read"
                and step.output_name
            ):
                outputs[
                    step.output_name
                ] = result.data

            if step.checkpoint:
                checkpoint_ok = (
                    self._check_checkpoint(
                        step.checkpoint
                    )
                )

                if not checkpoint_ok:

                    error_result = (
                        self._handle_error_rules(
                            step=step
                        )
                    )

                    if error_result:
                        return error_result

                    observation = (
                        self.surface.perceive()
                    )

                    return ReplayResult(
                        status="FAILURE",
                        step_index=step.index,
                        expected=(
                            str(step.checkpoint)
                        ),
                        observed=(
                            observation
                            .accessibility_snapshot
                        ),
                        detail=(
                            "Step checkpoint failed."
                        ),
                    )

        final_success = self._check_checkpoint(
            capability.success_condition
        )

        if not final_success:

            observation = (
                self.surface.perceive()
            )

            return ReplayResult(
                status="FAILURE",
                expected=str(
                    capability.success_condition
                ),
                observed=(
                    observation
                    .accessibility_snapshot
                ),
                detail=(
                    "Final success condition "
                    "was not satisfied."
                ),
            )

        return ReplayResult(
            status="SUCCESS",
            outputs=outputs,
        )

    # -----------------------------------------------------
    # PARAMETER VALIDATION
    # -----------------------------------------------------

    def _validate_params(
        self,
        capability: Capability,
        params: dict[str, Any],
    ) -> str | None:

        for param_spec in (
            capability.input_parameters
        ):

            if (
                param_spec.required
                and param_spec.name
                not in params
            ):
                return (
                    "Missing required parameter: "
                    f"{param_spec.name}"
                )

        return None

    # -----------------------------------------------------
    # STEP EXECUTION
    # -----------------------------------------------------

    def _execute_step(
        self,
        step: Step,
        params: dict[str, Any],
    ) -> ActionResult:

        value = self._resolve_value(
            value=step.value,
            params=params,
        )

        if step.action == "navigate":

            return self.surface.act(
                Action(
                    action="navigate",
                    value=str(value),
                )
            )

        if step.action not in {
            "click",
            "type",
            "read",
            "wait_for",
        }:
            return ActionResult(
                success=False,
                error=(
                    "Replay does not currently "
                    f"support action '{step.action}'."
                ),
            )

        if step.target is None:
            return ActionResult(
                success=False,
                error=(
                    f"Step {step.index} requires "
                    "a target."
                ),
            )

        return self._execute_with_locators(
            step=step,
            value=value,
        )

    # -----------------------------------------------------
    # PARAMETER RESOLUTION
    # -----------------------------------------------------

    def _resolve_value(
        self,
        value: Any,
        params: dict[str, Any],
    ) -> Any:

        if isinstance(
            value,
            ParamRef,
        ):
            if value.param not in params:
                raise ValueError(
                    "Parameter not provided: "
                    f"{value.param}"
                )

            return params[
                value.param
            ]

        return value

    # -----------------------------------------------------
    # LOCATOR RESOLUTION
    # -----------------------------------------------------

    def _execute_with_locators(
        self,
        step: Step,
        value: Any,
    ) -> ActionResult:

        assert step.target is not None

        locator_candidates = [
            step.target.primary,
            *step.target.fallbacks,
        ]

        errors: list[str] = []

        for locator in locator_candidates:

            target = (
                self._locator_to_surface_target(
                    locator
                )
            )

            if target is None:
                errors.append(
                    "Unsupported locator "
                    f"strategy: "
                    f"{locator.strategy}"
                )
                continue

            action = Action(
                action=step.action,
                target=target,
                value=(
                    str(value)
                    if value is not None
                    else None
                ),
            )

            result = self.surface.act(
                action
            )

            if result.success:
                return result

            if result.error:
                errors.append(
                    result.error
                )

        return ActionResult(
            success=False,
            error=(
                "All locator strategies "
                "failed. "
                + " | ".join(errors)
            ),
        )

    def _locator_to_surface_target(
        self,
        locator: Locator,
    ) -> Target | None:

        if (
            locator.strategy
            == "a11y_role_name"
        ):
            role = locator.value.get(
                "role"
            )

            name = locator.value.get(
                "name"
            )

            if not role or not name:
                return None

            return Target(
                strategy="role",
                role=role,
                value=name,
            )

        if locator.strategy == "text":

            text = locator.value.get(
                "text"
            )

            if not text:
                return None

            return Target(
                strategy="text",
                value=text,
            )

        # Other strategies such as attr,
        # css, xpath, relative and visual
        # will be added later.
        return None

    # -----------------------------------------------------
    # CHECKPOINTS
    # -----------------------------------------------------

    def _check_checkpoint(
        self,
        checkpoint: Checkpoint,
    ) -> bool:

        observation = (
            self.surface.perceive()
        )

        if (
            checkpoint.type
            == "text_present"
        ):
            expected_text = (
                checkpoint.spec.get(
                    "text"
                )
            )

            if not expected_text:
                return False

            return (
                expected_text
                in observation
                .accessibility_snapshot
            )

        if (
            checkpoint.type
            == "url_matches"
        ):
            expected_url = (
                checkpoint.spec.get(
                    "pattern"
                )
                or checkpoint.spec.get(
                    "url"
                )
            )

            if not expected_url:
                return False

            return (
                expected_url
                in observation.url
            )

        if (
            checkpoint.type
            == "element_present"
        ):
            expected = (
                checkpoint.spec.get(
                    "text"
                )
                or checkpoint.spec.get(
                    "name"
                )
            )

            if not expected:
                return False

            return (
                expected
                in observation
                .accessibility_snapshot
            )

        return False

    # -----------------------------------------------------
    # ERROR RULES
    # -----------------------------------------------------

    def _handle_error_rules(
        self,
        step: Step,
    ) -> ReplayResult | None:

        for rule in step.on_error:

            matched = (
                self._check_checkpoint(
                    rule.match
                )
            )

            if not matched:
                continue

            if (
                rule.classify
                == "business_outcome"
            ):
                return ReplayResult(
                    status=(
                        "BUSINESS_OUTCOME"
                    ),
                    outcome_code=(
                        rule.outcome_code
                    ),
                    step_index=step.index,
                    detail=(
                        "Expected business "
                        "outcome detected."
                    ),
                )

            if (
                rule.classify
                == "hard_failure"
            ):
                return ReplayResult(
                    status="FAILURE",
                    step_index=step.index,
                    detail=(
                        rule.outcome_code
                        or
                        "Hard failure detected."
                    ),
                )

        return None