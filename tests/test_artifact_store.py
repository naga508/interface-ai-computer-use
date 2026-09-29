from app.artifact.sample import (
    build_lookup_member_balance_capability,
)
from app.artifact.store import ArtifactStore


def test_artifact_save_and_load(
    tmp_path,
):
    store = ArtifactStore(
        directory=tmp_path
    )

    capability = (
        build_lookup_member_balance_capability()
    )

    file_path = store.save(
        capability
    )

    assert file_path.exists()

    loaded = store.load(
        "lookup_member_balance.json"
    )

    assert (
        loaded.name
        == "lookup_member_balance"
    )

    assert (
        loaded.input_parameters[0].name
        == "member_id"
    )

    assert (
        loaded.outputs[0].name
        == "savings_balance"
    )

    assert (
        loaded.steps[1].value.param
        == "member_id"
    )

    assert (
        loaded.steps[3].output_name
        == "savings_balance"
    )


def test_search_error_rules_exist():

    capability = (
        build_lookup_member_balance_capability()
    )

    search_step = capability.steps[2]

    assert len(
        search_step.on_error
    ) == 2

    recoverable_rule = next(
        rule
        for rule in search_step.on_error
        if rule.classify == "recoverable"
    )

    business_rule = next(
        rule
        for rule in search_step.on_error
        if rule.classify == "business_outcome"
    )

    assert (
        recoverable_rule.recovery
        == "retry"
    )

    assert (
        recoverable_rule.match.spec["text"]
        == "Loading member"
    )

    assert (
        business_rule.outcome_code
        == "MEMBER_NOT_FOUND"
    )

    assert (
        business_rule.match.spec["text"]
        == "No member found"
    )

    assert (
        search_step.retry.max_attempts
        == 5
    )

    assert (
        search_step.retry.backoff_ms
        == 500
    )