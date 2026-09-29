from app.artifact.schema import (
    Capability,
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
            # -------------------------------------------------
            # STEP 1: OPEN MOCKCORE
            # -------------------------------------------------
            Step(
                index=1,
                intent=(
                    "Open the MockCore "
                    "member search page."
                ),
                action="navigate",
                value="http://127.0.0.1:5000",
            ),

            # -------------------------------------------------
            # STEP 2: ENTER MEMBER ID
            # -------------------------------------------------
            Step(
                index=2,
                intent=(
                    "Enter the requested member ID."
                ),
                action="type",

                target=ElementTarget(
                    description=(
                        "Member ID input field."
                    ),

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

            # -------------------------------------------------
            # STEP 3: SEARCH
            # -------------------------------------------------
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
                        "The accessible button role "
                        "and name provide a stable "
                        "locator."
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

                # What should appear when search succeeds.
                checkpoint=Checkpoint(
                    type="text_present",
                    spec={
                        "text": "Member Details"
                    },
                ),

                # Runtime states that may appear instead.
                on_error=[
                    # -----------------------------------------
                    # RECOVERABLE: TEMPORARY SLOW LOAD
                    # -----------------------------------------
                    ErrorRule(
                        match=Checkpoint(
                            type="text_present",
                            spec={
                                "text": "Loading member"
                            },
                        ),
                        classify="recoverable",
                        recovery="retry",
                    ),

                    # -----------------------------------------
                    # EXPECTED BUSINESS OUTCOME
                    # -----------------------------------------
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
                    ),
                ],

                # Retry when a recoverable condition appears.
                retry=RetryPolicy(
                    max_attempts=5,
                    backoff_ms=500,
                ),
            ),

            # -------------------------------------------------
            # STEP 4: READ SAVINGS BALANCE
            # -------------------------------------------------
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
                        "Visible Savings Balance "
                        "text identifies the "
                        "required value."
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

        # Overall replay success condition.
        success_condition=Checkpoint(
            type="text_present",
            spec={
                "text": "Member Details"
            },
        ),

        approval_state="draft",
    )