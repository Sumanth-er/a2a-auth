from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging
from typing import Optional

from config import Settings, get_settings
from auth import get_keycloak_auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="A2A Keycloak Wrapper")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_keycloak_jwt(request: Request) -> str:
    """Extract JWT from Authorization header"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    return auth_header[7:]  # Remove "Bearer "


@app.get("/health")
async def health(settings: Settings = Depends(get_settings)):
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent_url": settings.AGENT_URL,
        "keycloak_url": settings.KEYCLOAK_URL,
    }


@app.post("/api/chat")
async def chat(
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """
    Chat endpoint - proxies to A2A agent with JWT token
    
    Flow:
    1. Extract Keycloak JWT from Authorization header
    2. Validate JWT signature using Keycloak public key
    3. Forward request to agent with same JWT
    """
    # Extract JWT from request
    try:
        keycloak_jwt = extract_keycloak_jwt(request)
    except HTTPException as e:
        raise e
    
    # Validate JWT
    keycloak_auth = get_keycloak_auth(
        settings.KEYCLOAK_URL,
        settings.KEYCLOAK_REALM
    )
    
    jwt_claims = keycloak_auth.validate_token(keycloak_jwt)
    if not jwt_claims:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Role-based access control
    required_role = 'agent-user'
    user_roles = jwt_claims.get('realm_access', {}).get('roles', [])
    user_email = jwt_claims.get('email', 'unknown')
    
    if required_role not in user_roles:
        logger.warning(f"Access denied for {user_email}: lacks '{required_role}' role. Has roles: {user_roles}")
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. You must have '{required_role}' role to use this agent."
        )
    
    # Parse request body
    try:
        body = await request.json()
        message = body.get('message')
        context_id = body.get('contextId', '')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request body: {e}")
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    logger.info(f"Chat request from {jwt_claims.get('email')} with context {context_id}")
    
    # Forward to agent with JWT
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            agent_response = await client.post(
                f"{settings.AGENT_URL}/",
                json={"message": message},
                headers={
                    "Authorization": f"Bearer {keycloak_jwt}",
                    "Content-Type": "application/json",
                }
            )
            agent_response.raise_for_status()
            return agent_response.json()
    
    except httpx.HTTPError as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=502, detail="Agent error")


@app.get("/api/user-info")
async def user_info(
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """Get authenticated user info"""
    try:
        keycloak_jwt = extract_keycloak_jwt(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    keycloak_auth = get_keycloak_auth(
        settings.KEYCLOAK_URL,
        settings.KEYCLOAK_REALM
    )
    
    jwt_claims = keycloak_auth.validate_token(keycloak_jwt)
    if not jwt_claims:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "user_id": jwt_claims.get('sub'),
        "email": jwt_claims.get('email'),
        "name": jwt_claims.get('name'),
        "roles": jwt_claims.get('realm_access', {}).get('roles', []),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
