import os
from functools import lru_cache


class Settings:
    # Keycloak
    KEYCLOAK_URL: str = os.getenv('KEYCLOAK_URL', 'http://127.0.0.1:8080')
    KEYCLOAK_REALM: str = os.getenv('KEYCLOAK_REALM', 'agent')
    
    # Agent
    AGENT_URL: str = os.getenv('AGENT_URL', 'http://localhost:10000')
    
    # Langfuse (optional)
    LANGFUSE_PUBLIC_KEY: str = os.getenv('LANGFUSE_PUBLIC_KEY', '')
    LANGFUSE_SECRET_KEY: str = os.getenv('LANGFUSE_SECRET_KEY', '')
    LANGFUSE_HOST: str = os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
    
    @property
    def keycloak_certs_url(self) -> str:
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/certs"


@lru_cache()
def get_settings():
    return Settings()
