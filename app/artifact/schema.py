from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------
# INPUT / OUTPUT DEFINITIONS
# ---------------------------------------------------------

ParameterType = Literal[
    "string",
    "int",
    "float",
    "bool",
    "enum",
]


class ParamSpec(BaseModel):
    name: str
    type: ParameterType
    required: bool = True
    description: str
    example: str | None = None
    sensitive: bool = False


class OutputSpec(BaseModel):
    name: str
    type: ParameterType
    description: str


class ParamRef(BaseModel):
    """
    Reference to an input parameter.

    Example:
        ParamRef(param="member_id")

    This prevents us from hard-coding a real member ID
    into a reusable capability.
    """

    param: str


# ---------------------------------------------------------
# TARGET / LOCATOR DEFINITIONS
# ---------------------------------------------------------

LocatorStrategy = Literal[
    "a11y_role_name",
    "attr",
    "text",
    "css",
    "xpath",
    "relative",
    "visual",
]


class Locator(BaseModel):
    strategy: LocatorStrategy
    value: dict[str, Any]


class ElementTarget(BaseModel):
    description: str
    reasoning: str

    primary: Locator

    fallbacks: list[Locator] = Field(
        default_factory=list
    )


# ---------------------------------------------------------
# CHECKPOINTS
# ---------------------------------------------------------

CheckpointType = Literal[
    "url_matches",
    "element_present",
    "text_present",
    "value_equals",
]


class Checkpoint(BaseModel):
    type: CheckpointType
    spec: dict[str, Any]


# ---------------------------------------------------------
# ERROR HANDLING
# ---------------------------------------------------------

ErrorClassification = Literal[
    "business_outcome",
    "recoverable",
    "hard_failure",
]


RecoveryAction = Literal[
    "dismiss",
    "retry",
    "reauth",
]


class ErrorRule(BaseModel):
    match: Checkpoint

    classify: ErrorClassification

    outcome_code: str | None = None

    recovery: RecoveryAction | None = None


class RetryPolicy(BaseModel):
    max_attempts: int = 1
    backoff_ms: int = 0


# ---------------------------------------------------------
# CAPABILITY STEP
# ---------------------------------------------------------

StepAction = Literal[
    "navigate",
    "click",
    "type",
    "select",
    "read",
    "wait_for",
    "assert",
]


StepValue = (
    str
    | int
    | float
    | bool
    | ParamRef
    | None
)


class Step(BaseModel):
    index: int

    intent: str

    action: StepAction

    target: ElementTarget | None = None

    value: StepValue = None

    output_name: str | None = None

    checkpoint: Checkpoint | None = None

    on_error: list[ErrorRule] = Field(
        default_factory=list
    )

    timeout_ms: int = 5000

    retry: RetryPolicy = Field(
        default_factory=RetryPolicy
    )


# ---------------------------------------------------------
# TARGET APPLICATION
# ---------------------------------------------------------

class TargetSpec(BaseModel):
    vendor_app_id: str

    version_range: str

    base_url_pattern: str


# ---------------------------------------------------------
# SAFETY POLICY REFERENCE
# ---------------------------------------------------------

class PolicyRef(BaseModel):
    profile: str = "default"

    allow_irreversible: bool = False


# ---------------------------------------------------------
# METADATA
# ---------------------------------------------------------

class CapabilityMetadata(BaseModel):
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    model_used: str | None = None

    discovery_run_id: str | None = None

    stability_score: float | None = None


# ---------------------------------------------------------
# COMPLETE CAPABILITY
# ---------------------------------------------------------

ApprovalState = Literal[
    "draft",
    "approved",
]


class Capability(BaseModel):
    schema_version: str = "1.0"

    capability_id: str

    name: str

    description: str

    target: TargetSpec

    input_parameters: list[ParamSpec]

    outputs: list[OutputSpec]

    steps: list[Step]

    success_condition: Checkpoint

    policy: PolicyRef = Field(
        default_factory=PolicyRef
    )

    approval_state: ApprovalState = "draft"

    metadata: CapabilityMetadata = Field(
        default_factory=CapabilityMetadata
    )