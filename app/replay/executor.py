import time
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.artifact.schema import (
    Capability,
    Checkpoint,
    Locator,
    ParamRef,
    Step,
)
from app.escalation.session import (
    SessionController,
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
        session_controller: SessionController | None = None,
    ):
        self.surface = surface
        self.session_controller = session_controller

    # -----------------------------------------------------
    # MAIN REPLAY ENTRY POINT
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

            # Capture declared outputs.
            if (
                step.action == "read"
                and step.output_name
            ):
                outputs[
                    step.output_name
                ] = result.data

            # Verify step checkpoint.
            if step.checkpoint:

                checkpoint_ok = (
                    self._check_checkpoint(
                        step.checkpoint
                    )
                )

                if not checkpoint_ok:

                    error_result = (
                        self._handle_checkpoint_failure(
                            step
                        )
                    )

                    # None means:
                    # recovery or human handoff succeeded,
                    # so replay can continue.
                    if error_result is not None:
                        return error_result

        # -------------------------------------------------
        # FINAL CAPABILITY SUCCESS CHECK
        # -------------------------------------------------

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
    # EXECUTE ONE STEP
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

        # ---------------------------------------------
        # NAVIGATE
        # ---------------------------------------------

        if step.action == "navigate":

            return self.surface.act(
                Action(
                    action="navigate",
                    value=str(value),
                )
            )

        # ---------------------------------------------
        # SUPPORTED ACTIONS
        # ---------------------------------------------

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
    # PARAMETER SUBSTITUTION
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
    # LOCATOR EXECUTION
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
                    f"strategy: {locator.strategy}"
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
                "All locator strategies failed. "
                + " | ".join(errors)
            ),
        )

    # -----------------------------------------------------
    # ARTIFACT LOCATOR -> SURFACE TARGET
    # -----------------------------------------------------

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

        # attr/css/xpath/relative/visual
        # can be implemented later.
        return None

    # -----------------------------------------------------
    # CHECKPOINT EVALUATION
    # -----------------------------------------------------

    def _check_checkpoint(
        self,
        checkpoint: Checkpoint,
    ) -> bool:

        observation = (
            self.surface.perceive()
        )

        # ---------------------------------------------
        # TEXT PRESENT
        # ---------------------------------------------

        if checkpoint.type == "text_present":

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

        # ---------------------------------------------
        # URL MATCH
        # ---------------------------------------------

        if checkpoint.type == "url_matches":

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

        # ---------------------------------------------
        # ELEMENT PRESENT
        # ---------------------------------------------

        if checkpoint.type == "element_present":

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
    # CHECKPOINT FAILURE HANDLING
    # -----------------------------------------------------

    def _handle_checkpoint_failure(
        self,
        step: Step,
    ) -> ReplayResult | None:

        # -------------------------------------------------
        # FIRST: CHECK DECLARED ERROR RULES
        # -------------------------------------------------

        for rule in step.on_error:

            matched = (
                self._check_checkpoint(
                    rule.match
                )
            )

            if not matched:
                continue

            # ---------------------------------------------
            # EXPECTED BUSINESS OUTCOME
            # ---------------------------------------------

            if (
                rule.classify
                == "business_outcome"
            ):

                return ReplayResult(
                    status="BUSINESS_OUTCOME",
                    outcome_code=(
                        rule.outcome_code
                    ),
                    step_index=step.index,
                    detail=(
                        "Expected business "
                        "outcome detected."
                    ),
                )

            # ---------------------------------------------
            # RECOVERABLE CONDITION
            # ---------------------------------------------

            if (
                rule.classify
                == "recoverable"
            ):

                if rule.recovery == "retry":

                    for _ in range(
                        step.retry.max_attempts
                    ):

                        if (
                            step.retry.backoff_ms
                            > 0
                        ):
                            time.sleep(
                                step.retry.backoff_ms
                                / 1000
                            )

                        if (
                            step.checkpoint
                            and self._check_checkpoint(
                                step.checkpoint
                            )
                        ):
                            # Recovery succeeded.
                            return None

                    return ReplayResult(
                        status="FAILURE",
                        step_index=step.index,
                        detail=(
                            "Recoverable condition "
                            "exceeded retry limit."
                        ),
                    )

                return ReplayResult(
                    status="FAILURE",
                    step_index=step.index,
                    detail=(
                        "Unsupported recovery action: "
                        f"{rule.recovery}"
                    ),
                )

            # ---------------------------------------------
            # DECLARED HARD FAILURE
            # ---------------------------------------------

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

        # -------------------------------------------------
        # NO DECLARED RULE MATCHED
        #
        # IF A HUMAN SESSION CONTROLLER EXISTS,
        # ESCALATE IN THE SAME LIVE BROWSER SESSION.
        # -------------------------------------------------

        if self.session_controller is not None:

            self.session_controller.handoff(
                surface=self.surface,
                reason=(
                    "Automation reached an "
                    "unexpected UI state and "
                    "cannot safely continue "
                    "automatically."
                ),
                step_index=step.index,
            )

            # After the human completes the
            # required action in the SAME browser
            # session, check whether the expected
            # state now exists.
            if (
                step.checkpoint
                and self._check_checkpoint(
                    step.checkpoint
                )
            ):
                return None

        # -------------------------------------------------
        # HARD FAILURE
        # -------------------------------------------------

        observation = (
            self.surface.perceive()
        )

        return ReplayResult(
            status="FAILURE",
            step_index=step.index,
            expected=str(
                step.checkpoint
            ),
            observed=(
                observation
                .accessibility_snapshot
            ),
            detail=(
                "Step checkpoint failed."
            ),
        )