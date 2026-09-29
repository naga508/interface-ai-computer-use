from app.artifact.schema import (
    Capability,
    Checkpoint,
    ElementTarget,
    Locator,
    OutputSpec,
    ParamRef,
    ParamSpec,
    Step,
    TargetSpec,
)


def test_lookup_member_balance_capability():

    capability = Capability(
        capability_id="lookup-member-balance-v1",
        name="lookup_member_balance",
        description=(
            "Look up a member by ID and "
            "return the current savings balance."
        ),
        target=TargetSpec(
            vendor_app_id="mockcore",
            version_range="1.x",
            base_url_pattern=(
                "http://127.0.0.1:5000"
            ),
        ),
        input_parameters=[
            ParamSpec(
                name="member_id",
                type="string",
                required=True,
                description=(
                    "Member identifier used "
                    "for account lookup."
                ),
                example="12345",
                sensitive=True,
            )
        ],
        outputs=[
            OutputSpec(
                name="savings_balance",
                type="string",
                description=(
                    "Current savings balance."
                ),
            )
        ],
        steps=[
            Step(
                index=1,
                intent="Open MockCore.",
                action="navigate",
                value=(
                    "http://127.0.0.1:5000"
                ),
            ),
            Step(
                index=2,
                intent=(
                    "Enter the member ID."
                ),
                action="type",
                target=ElementTarget(
                    description=(
                        "Member ID input field."
                    ),
                    reasoning=(
                        "Accessibility label "
                        "is the preferred locator."
                    ),
                    primary=Locator(
                        strategy=(
                            "a11y_role_name"
                        ),
                        value={
                            "role": "textbox",
                            "name": "Member ID",
                        },
                    ),
                    fallbacks=[
                        Locator(
                            strategy="text",
                            value={
                                "text": "Member ID"
                            },
                        )
                    ],
                ),
                value=ParamRef(
                    param="member_id"
                ),
            ),
            Step(
                index=3,
                intent=(
                    "Submit the member search."
                ),
                action="click",
                target=ElementTarget(
                    description=(
                        "Search button."
                    ),
                    reasoning=(
                        "The button role and "
                        "accessible name are stable."
                    ),
                    primary=Locator(
                        strategy=(
                            "a11y_role_name"
                        ),
                        value={
                            "role": "button",
                            "name": "Search",
                        },
                    ),
                ),
                checkpoint=Checkpoint(
                    type="text_present",
                    spec={
                        "text": "Member Details"
                    },
                ),
            ),
            Step(
                index=4,
                intent=(
                    "Read the member's "
                    "savings balance."
                ),
                action="read",
                target=ElementTarget(
                    description=(
                        "Savings Balance value."
                    ),
                    reasoning=(
                        "Visible text identifies "
                        "the balance."
                    ),
                    primary=Locator(
                        strategy="text",
                        value={
                            "text": (
                                "Savings Balance"
                            )
                        },
                    ),
                ),
            ),
        ],
        success_condition=Checkpoint(
            type="text_present",
            spec={
                "text": "Member Details"
            },
        ),
    )

    assert (
        capability.name
        == "lookup_member_balance"
    )

    assert (
        capability.input_parameters[0].name
        == "member_id"
    )

    assert (
        capability.steps[1].value.param
        == "member_id"
    )

    assert (
        capability.approval_state
        == "draft"
    )


def test_capability_can_be_serialized():

    capability = Capability(
        capability_id="test-capability",
        name="test",
        description="Serialization test.",
        target=TargetSpec(
            vendor_app_id="mockcore",
            version_range="1.x",
            base_url_pattern=(
                "http://127.0.0.1:5000"
            ),
        ),
        input_parameters=[],
        outputs=[],
        steps=[],
        success_condition=Checkpoint(
            type="text_present",
            spec={
                "text": "MockCore"
            },
        ),
    )

    json_data = capability.model_dump_json()

    restored = (
        Capability.model_validate_json(
            json_data
        )
    )

    assert (
        restored.capability_id
        == capability.capability_id
    )

    assert (
        restored.schema_version
        == "1.0"
    )