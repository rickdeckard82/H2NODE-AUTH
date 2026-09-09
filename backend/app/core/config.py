import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Variáveis que aceitam a convenção <NOME>_FILE (Docker secrets). Se o arquivo
# existir e a variável direta não estiver definida, o conteúdo do arquivo é usado.
_FILE_BACKED = (
    "JWT_SECRET",
    "FERNET_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "MYSQL_BACKEND_PASSWORD",
    "BOOTSTRAP_ADMIN_PASSWORD",
)


def _load_file_secrets() -> None:
    for name in _FILE_BACKED:
        path = os.environ.get(f"{name}_FILE")
        if path and not os.environ.get(name):
            p = Path(path)
            if p.is_file():
                os.environ[name] = p.read_text(encoding="utf-8").strip()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Banco
    database_url: str = Field(
        default="mysql+pymysql://backend_svc:backend@db:3306/radius",
        alias="DATABASE_URL",
    )

    # Segurança
    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = Field(default=15, alias="ACCESS_TOKEN_TTL_MINUTES")
    refresh_token_ttl_days: int = Field(default=7, alias="REFRESH_TOKEN_TTL_DAYS")
    # "Lembrar deste dispositivo" no 2FA: janela deslizante (renovada a cada
    # login) em que o navegador pula a 2ª etapa.
    mfa_trusted_device_ttl_days: int = Field(
        default=30, alias="MFA_TRUSTED_DEVICE_TTL_DAYS"
    )
    fernet_key: str = Field(alias="FERNET_KEY")

    # Storage do rate-limit. Vazio => memória (por worker). Redis => compartilhado.
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    # Usuário MySQL do FreeRADIUS — usado pela migração 0004 para grant mínimo.
    radius_db_user: str = Field(default="radius_svc", alias="RADIUS_DB_USER")

    # HTTP
    frontend_origin: str = Field(default="https://localhost", alias="FRONTEND_ORIGIN")
    cookie_secure: bool = Field(default=True, alias="COOKIE_SECURE")
    cookie_domain: str | None = Field(default=None, alias="COOKIE_DOMAIN")
    api_prefix: str = "/api"

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    # Arquivo de config gerado para o tac_plus-ng (hosts + profiles + ruleset).
    # Vazio => sync do TACACS+ vira no-op (dev/tests sem o container tacacs).
    tacacs_hosts_path: str | None = Field(default=None, alias="TACACS_HOSTS_PATH")
    # Expor /api/docs e /api/openapi.json. Desligado por padrão (produção).
    enable_docs: bool = Field(default=False, alias="ENABLE_DOCS")

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_strength(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET deve ter no mínimo 32 caracteres (use: openssl rand -hex 32)")
        return v

    # Bootstrap do primeiro admin (usado pelo seed)
    bootstrap_admin_username: str = Field(default="admin", alias="BOOTSTRAP_ADMIN_USERNAME")
    bootstrap_admin_email: str = Field(default="admin@example.com", alias="BOOTSTRAP_ADMIN_EMAIL")
    bootstrap_admin_password: str = Field(default="", alias="BOOTSTRAP_ADMIN_PASSWORD")

    @property
    def access_cookie_name(self) -> str:
        return "pr_access"

    @property
    def refresh_cookie_name(self) -> str:
        return "pr_refresh"

    @property
    def csrf_cookie_name(self) -> str:
        return "pr_csrf"

    @property
    def mfa_device_cookie_name(self) -> str:
        return "pr_td"


@lru_cache
def get_settings() -> Settings:
    _load_file_secrets()
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
