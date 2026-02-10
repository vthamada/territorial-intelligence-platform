from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "territorial-intelligence-platform"
    app_env: str = "local"
    log_level: str = "INFO"
    api_version_prefix: str = "/v1"
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/territorial_intelligence"
    municipality_ibge_code: str = "3121605"
    crs_epsg: int = 4674

    data_root: Path = Field(default_factory=lambda: Path("data"))
    orchestrator_name: str = "prefect"
    pipeline_version: str = "0.1.0"

    request_timeout_seconds: int = 30
    http_max_retries: int = 3
    http_backoff_seconds: float = 1.5
    bronze_retention_days: int = 3650

    ibge_api_base_url: str = "https://servicodados.ibge.gov.br/api/v1/localidades"
    tse_ckan_base_url: str = "https://dadosabertos.tse.jus.br/api/3/action"
    mte_ftp_host: str = "ftp.mtps.gov.br"
    mte_ftp_port: int = 21
    mte_ftp_root_candidates: str = "/pdet/microdados/NOVO CAGED,/pdet/microdados/NOVO_CAGED"
    mte_ftp_max_depth: int = 4
    mte_ftp_max_dirs: int = 300

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def bronze_root(self) -> Path:
        return self.data_root / "bronze"

    @property
    def manifests_root(self) -> Path:
        return self.data_root / "manifests"

    @property
    def silver_root(self) -> Path:
        return self.data_root / "silver"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
