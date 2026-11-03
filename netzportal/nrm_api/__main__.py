import os
import uvicorn
from .config import Settings


def main() -> None:
    Settings.from_env()  # Fail clearly before starting if credentials/key are missing.
    uvicorn.run(
        "nrm_api.app:app",
        host=os.environ.get("NRM_HOST", "127.0.0.1"),
        port=int(os.environ.get("NRM_PORT", "8080")),
        access_log=False,  # Do not log request URLs/parameters containing customer data.
    )


if __name__ == "__main__":
    main()
