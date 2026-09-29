from pathlib import Path

from app.artifact.schema import Capability


class ArtifactStore:
    def __init__(
        self,
        directory: str | Path = "artifacts",
    ):
        self.directory = Path(directory)

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        capability: Capability,
    ) -> Path:
        file_path = (
            self.directory
            / f"{capability.name}.json"
        )

        file_path.write_text(
            capability.model_dump_json(
                indent=2
            ),
            encoding="utf-8",
        )

        return file_path

    def load(
        self,
        artifact_name: str,
    ) -> Capability:
        file_path = (
            self.directory
            / artifact_name
        )

        if not file_path.exists():
            raise FileNotFoundError(
                f"Artifact not found: {file_path}"
            )

        json_data = file_path.read_text(
            encoding="utf-8"
        )

        return Capability.model_validate_json(
            json_data
        )