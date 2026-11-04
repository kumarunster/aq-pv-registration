from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    username: str = field(repr=False)
    password: str = field(repr=False)
    api_key: str = field(repr=False)
    timeout_seconds: float = 30
    draft_directory: str = field(default="", repr=False)
    enm_username: str = field(default="", repr=False)
    enm_password: str = field(default="", repr=False)
    mainzer_username: str = field(default="", repr=False)
    mainzer_password: str = field(default="", repr=False)
    enetz_username: str = field(default="", repr=False)
    enetz_password: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        pairs = [(self.username, self.password), (self.enm_username, self.enm_password),
                 (self.mainzer_username, self.mainzer_password), (self.enetz_username, self.enetz_password)]
        if any(bool(u) != bool(p) for u, p in pairs):
            raise ValueError("Each configured provider requires both username and password")
        if not any(u and p for u, p in pairs):
            raise ValueError("Configure credentials for at least one provider")
        if len(self.api_key) < 32:
            raise ValueError("NRM_API_KEY must contain at least 32 characters")
        if not 1 <= self.timeout_seconds <= 120:
            raise ValueError("NRM_TIMEOUT_SECONDS must be between 1 and 120")

    @classmethod
    def from_env(cls) -> "Settings":
        # Read the project-local secret file even when invoked from another directory.
        # Deployment environment variables take precedence over the file.
        load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
        return cls(
            username=os.environ.get("NRM_USERNAME", ""),
            password=os.environ.get("NRM_PASSWORD", ""),
            api_key=os.environ.get("NRM_API_KEY", ""),
            timeout_seconds=float(os.environ.get("NRM_TIMEOUT_SECONDS", "30")),
            draft_directory=os.environ.get("PV_DATA_DIR", ""),
            enm_username=os.environ.get("ENM_USERNAME", ""),
            enm_password=os.environ.get("ENM_PASSWORD", ""),
            mainzer_username=os.environ.get("MAINZER_USERNAME", ""),
            mainzer_password=os.environ.get("MAINZER_PASSWORD", ""),
            enetz_username=os.environ.get("ENETZ_USERNAME", ""),
            enetz_password=os.environ.get("ENETZ_PASSWORD", ""),
        )
