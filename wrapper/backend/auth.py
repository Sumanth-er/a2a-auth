import httpx
import jwt
from typing import Optional, Dict
from datetime import datetime
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class KeycloakAuth:
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
                
                # Build key map: kid -> public_key
                for key in data.get('keys', []):
                    kid = key.get('kid')
                    if kid:
                        self.public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(
                            str(key)
                        )
                logger.info(f"Loaded {len(self.public_keys)} public keys from Keycloak")
        except Exception as e:
            logger.error(f"Failed to fetch Keycloak public keys: {e}")
            raise
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validate JWT token and return claims if valid
        Returns None if invalid or expired
        """
        try:
            # Decode header to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            if not kid or kid not in self.public_keys:
                logger.warning(f"Unknown key ID: {kid}")
                if not self.public_keys or kid not in self.public_keys:
                    self._refresh_public_keys()
            
            # Verify and decode
            public_key = self.public_keys.get(kid)
            if not public_key:
                logger.error(f"Public key not found for kid: {kid}")
                return None
            
            claims = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=None  # Keycloak JWTs may not have audience
            )
            
            # Check expiry manually
            if claims.get('exp', 0) < datetime.utcnow().timestamp():
                logger.warning("Token expired")
                return None
            
            logger.info(f"Token validated for user: {claims.get('email')}")
            return claims
        
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None


@lru_cache(maxsize=1)
def get_keycloak_auth(keycloak_url: str, realm: str) -> KeycloakAuth:
    return KeycloakAuth(keycloak_url, realm)
