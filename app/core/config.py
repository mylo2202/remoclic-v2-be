from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "REMOCLIC v2"
    DATA_BASE_URL: str = "http://hpc.meteo.edu.vn/~tanpv/For_Me/562_VNU/PDF_Ope"
    DATA_FILE_NAME: str = "Dr_Prob.nc"


settings = Settings()
