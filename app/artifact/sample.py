from app.artifact.schema import (
    Capability,
    Checkpoint,
    ElementTarget,
    ErrorRule,
    Locator,
    OutputSpec,
    ParamRef,
    ParamSpec,
    Step,
    TargetSpec,
)


def build_lookup_member_balance_capability() -> Capability:

    return Capability(
        capability_id="lookup-member-balance-v1",
        name="lookup_member_balance",
        description=(
            "Look up a member by ID in MockCore "
            "and return their current savings balance."
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
                    "Current savings balance "
                    "shown on the member details page."
                ),
            )
        ],

        steps=[
            Step(
                index=1,
                intent="Open the MockCore member search page.",
                action="navigate",
                value="http://127.0.0.1:5000",
            ),

            Step(
                index=2,
                intent="Enter the requested member ID.",
                action="type",

                target=ElementTarget(
                    description="Member ID input field.",

                    reasoning=(
                        "Accessible textbox name is "
                        "preferred because it is more "
                        "stable than DOM position."
                    ),

                    primary=Locator(
                        strategy="a11y_role_name",
                        value={
                            "role": "textbox",
                            "name": "Member ID",
                        },
                    ),

                    fallbacks=[
                        Locator(
                            strategy="attr",
                            value={
                                "name": "member_id"
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
                intent="Submit the member search.",
                action="click",

                target=ElementTarget(
                    description="Search button.",

                    reasoning=(
                        "The accessible button role "
                        "and name identify this control."
                    ),

                    primary=Locator(
                        strategy="a11y_role_name",
                        value={
                            "role": "button",
                            "name": "Search",
                        },
                    ),

                    fallbacks=[
                        Locator(
                            strategy="text",
                            value={
                                "text": "Search"
                            },
                        )
                    ],
                ),

                checkpoint=Checkpoint(
                    type="text_present",
                    spec={
                        "text": "Member Details"
                    },
                ),

                on_error=[
                    ErrorRule(
                        match=Checkpoint(
                            type="text_present",
                            spec={
                                "text": (
                                    "No member found"
                                )
                            },
                        ),
                        classify=(
                            "business_outcome"
                        ),
                        outcome_code=(
                            "MEMBER_NOT_FOUND"
                        ),
                    )
                ],
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
                        "Savings Balance row."
                    ),

                    reasoning=(
                        "The visible Savings Balance "
                        "text identifies the value."
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

                output_name="savings_balance",
            ),
        ],

        success_condition=Checkpoint(
            type="text_present",
            spec={
                "text": "Member Details"
            },
        ),

        approval_state="draft",
    )