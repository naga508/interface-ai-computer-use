import os
from pathlib import Path

from dotenv import load_dotenv

from app.agent.discovery import (
    DiscoveryResult,
)
from app.artifact.recorder import (
    CapabilityRecorder,
    RecorderConfig,
)
from app.artifact.store import (
    ArtifactStore,
)


def main():

    load_dotenv()

    evidence_path = Path(
        "evidence/live_discovery_run.json"
    )

    if not evidence_path.exists():
        raise FileNotFoundError(
            "Live discovery evidence not found: "
            f"{evidence_path}"
        )

    discovery = (
        DiscoveryResult.model_validate_json(
            evidence_path.read_text(
                encoding="utf-8"
            )
        )
    )

    config = RecorderConfig(
        capability_id=(
            "lookup-member-balance-v1"
        ),

        capability_name=(
            "lookup_member_balance"
        ),

        description=(
            "Look up a member by ID in "
            "MockCore and return their "
            "current savings balance."
        ),

        vendor_app_id="mockcore",

        version_range="1.x",

        base_url_pattern=(
            "http://127.0.0.1:5000"
        ),

        input_name="member_id",

        input_description=(
            "Member identifier used "
            "for account lookup."
        ),

        input_example="12345",

        input_sensitive=True,

        output_name="savings_balance",

        output_description=(
            "Current savings balance "
            "shown on the member details page."
        ),

        success_text="Member Details",

        output_target_text=(
            "Savings Balance"
        ),

        recoverable_text=(
            "Loading member"
        ),

        business_outcome_text=(
            "No member found"
        ),

        business_outcome_code=(
            "MEMBER_NOT_FOUND"
        ),

        retry_max_attempts=5,

        retry_backoff_ms=500,

        model_used=os.getenv(
            "GEMINI_MODEL",
            "gemini-3.5-flash-lite",
        ),

        discovery_run_id=(
            "live-discovery-001"
        ),
    )

    recorder = CapabilityRecorder()

    capability = recorder.record(
        discovery=discovery,
        config=config,
    )

    store = ArtifactStore()

    artifact_path = store.save(
        capability
    )

    print(
        "\nRecorded capability:"
    )

    print(
        capability.model_dump_json(
            indent=2
        )
    )

    print(
        "\nArtifact saved to:"
    )

    print(
        artifact_path
    )


if __name__ == "__main__":
    main()