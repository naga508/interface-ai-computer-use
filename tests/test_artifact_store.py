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


def test_member_not_found_rule_exists():

    capability = (
        build_lookup_member_balance_capability()
    )

    search_step = capability.steps[2]

    assert len(
        search_step.on_error
    ) == 1

    error_rule = (
        search_step.on_error[0]
    )

    assert (
        error_rule.classify
        == "business_outcome"
    )

    assert (
        error_rule.outcome_code
        == "MEMBER_NOT_FOUND"
    )