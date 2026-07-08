from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    PROJECT_NAME: str = "REMOCLIC v2"
    DROUGHT_DATA_URL: str = "http://hpc.meteo.edu.vn/~tanpv/For_Me/562_VNU/PDF_Ope"
    DROUGHT_DATA_FILE_NAME: str = "Dr_Prob.nc"
    PR_T2_DATA_URL: str = "http://hpc.meteo.edu.vn/~tanpv/For_Me/562_VNU/PDF_Ope"
    PR_T2_DATA_FILE_NAME: str = "Forecast_Ope_Pr_T2_and_Anomaly.nc"
    MONTHLY_CLIM_DATA_URL: str = "http://hpc.meteo.edu.vn/~tanpv/For_Me/Dr_VN_Ope/DATA/Cli_Out"
    MONTHLY_CLIM_DATA_FILE_NAME: str = "Monthly_Clim.nc"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/remoclic"

    BACKEND_CORS_ORIGINS: list[str] | str = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        elif isinstance(v, str) and v.startswith("["):
            import json
            return json.loads(v)
        return v


settings = Settings()
