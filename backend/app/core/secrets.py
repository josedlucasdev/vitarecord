"""Cliente de Vault/KMS (plan/plan.md seccion 2.B.10).

En produccion, VAULT_TOKEN se inyecta por el orquestador y las llaves reales
(KEK, credenciales de terceros) nunca viven en el repositorio ni en un .env
versionado. En desarrollo local, este mismo cliente habla con el contenedor
Vault en modo dev (paridad de API, sin datos reales).
"""

import hvac

from app.core.config import settings

_client: hvac.Client | None = None


def get_vault_client() -> hvac.Client:
    global _client
    if _client is None:
        _client = hvac.Client(url=settings.VAULT_ADDR, token=settings.VAULT_TOKEN)
    return _client


def read_secret(path: str) -> dict:
    client = get_vault_client()
    response = client.secrets.kv.v2.read_secret_version(path=path)
    return response["data"]["data"]


def write_secret(path: str, data: dict) -> None:
    client = get_vault_client()
    client.secrets.kv.v2.create_or_update_secret(path=path, secret=data)
