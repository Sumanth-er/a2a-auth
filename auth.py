import os
import httpx
import jwt
import logging
from datetime import datetime
from dataclasses import dataclass
from functools import lru_cache

from a2a.auth.user import UnauthenticatedUser
from a2a.auth.user import User as A2AUser
from a2a.extensions.common import HTTP_EXTENSION_HEADER, get_requested_extensions
from a2a.server.apps.jsonrpc.jsonrpc_app import CallContextBuilder
from a2a.server.context import ServerCallContext

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BearerUser(A2AUser):
    name: str
    user_id: str = ""  # Store Keycloak user ID
    email: str = ""    # Store Keycloak email

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def user_name(self) -> str:
        return self.name


class KeycloakJWTAuth:
    """Validate Keycloak JWT tokens"""
    
    def __init__(self, keycloak_url: str, realm: str):
        self.keycloak_url = keycloak_url
        self.realm = realm
        self.certs_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/certs"
        self.public_keys = {}
        self._refresh_public_keys()
    
    def _refresh_public_keys(self):
        """Fetch Keycloak public keys"""
        try:
            with httpx.Client() as client:
                response = client.get(self.certs_url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                for key in data.get('keys', []):
                    kid = key.get('kid')
                    if kid:
                        self.public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(
                            str(key)
                        )
                        logger.info(f"Loaded public key: {kid}")
        except Exception as e:
            logger.error(f"Failed to fetch Keycloak public keys: {e}")
            raise
    
    def validate_token(self, token: str) -> dict | None:
        """Validate JWT and return claims"""
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            if not kid or kid not in self.public_keys:
                self._refresh_public_keys()
            
            public_key = self.public_keys.get(kid)
            if not public_key:
                logger.warning(f"Key not found: {kid}")
                return None
            
            claims = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                options={"verify_aud": False}
            )
            
            if claims.get('exp', 0) < datetime.utcnow().timestamp():
                logger.warning("Token expired")
                return None
            
            logger.info(f"JWT validated for: {claims.get('email')}")
            return claims
        
        except Exception as e:
            logger.error(f"JWT validation failed: {e}")
            return None


class KeycloakJWTCallContextBuilder(CallContextBuilder):
    """Validate Keycloak JWT tokens instead of opaque tokens"""
    
    def __init__(self, keycloak_url: str, realm: str):
        self.keycloak_auth = KeycloakJWTAuth(keycloak_url, realm)
    
    @classmethod
    def from_env(cls) -> 'KeycloakJWTCallContextBuilder':
        """Create from environment variables"""
        keycloak_url = os.getenv('KEYCLOAK_URL', 'http://127.0.0.1:8080')
        realm = os.getenv('KEYCLOAK_REALM', 'agent')
        return cls(keycloak_url, realm)
    
    def build(self, request) -> ServerCallContext:
        auth_header = request.headers.get('authorization', '')
        token = self._extract_bearer_token(auth_header)
        
        # ⭐ Validate JWT signature
        claims = None
        if token:
            claims = self.keycloak_auth.validate_token(token)
        
        # Create user object
        if claims:
            user = BearerUser(
                name=claims.get('name', 'Keycloak User'),
                user_id=claims.get('sub', ''),
                email=claims.get('email', ''),
            )
            state = {
                'headers': dict(request.headers),
                'auth_token_valid': True,
                'jwt_claims': claims,  # Store claims for executor
            }
        else:
            user = UnauthenticatedUser()
            state = {
                'headers': dict(request.headers),
                'auth_token_valid': False,
            }
        
        return ServerCallContext(
            user=user,
            state=state,
            requested_extensions=get_requested_extensions(
                request.headers.getlist(HTTP_EXTENSION_HEADER)
            ),
        )
    
    @staticmethod
    def _extract_bearer_token(auth_header: str) -> str | None:
        if not auth_header:
            return None
        scheme, _, token = auth_header.partition(' ')
        if scheme.lower() != 'bearer' or not token:
            return None
        return token.strip()
