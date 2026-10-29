from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    mongo_uri: str = "mongodb://na-mongodb:27017"
    mongo_database: str = "netzanmeldung"
    weasyprint_url: str = "http://na-weasyprint:8012"
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "naadmin"
    minio_secret_key: str = "naadmin"
    minio_bucket: str = "na-docs"

    class Config:
        env_prefix = ""


settings = Settings()
