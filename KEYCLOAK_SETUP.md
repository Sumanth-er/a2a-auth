# Keycloak Configuration Guide

This guide provides step-by-step instructions to set up Keycloak for the A2A Agent Keycloak wrapper.

## Prerequisites

- Docker and Docker Compose installed
- Keycloak running on `http://127.0.0.1:8080`
- Keycloak admin credentials: `admin / admin` (default)

---

## Step 1: Start Keycloak with Docker

### Option 1: Using Docker Run (Quickstart)

```bash
docker run --name keycloak -d \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  -p 8080:8080 \
  quay.io/keycloak/keycloak:latest \
  start-dev
```

Access Keycloak admin console at: `http://127.0.0.1:8080/admin`

### Option 2: Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  keycloak:
    image: quay.io/keycloak/keycloak:latest
    const:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin
    ports:
      - "8080:8080"
    command: start-dev
```

Run:
```bash
docker-compose up -d keycloak
```

Wait 20-30 seconds for Keycloak to start.

---

## Step 2: Create Realm "agent"

1. **Login to Keycloak Admin Console**
   - URL: `http://127.0.0.1:8080/admin`
   - Username: `admin`
   - Password: `admin`

2. **Create Realm**
   - Click the dropdown next to "Master" (top-left corner)
   - Click "Create Realm"
   - **Realm name**: `agent`
   - **Enabled**: Toggle ON
   - Click "Create"

3. **Verify Realm Created**
   - You should now see "agent" in the realm dropdown

---

## Step 3: Create Client "a2a-agent-frontend"

1. **In Realm "agent", Go to Clients**
   - Left sidebar: Clients → "Create client"

2. **Client Configuration**
   - **Client ID**: `a2a-agent-frontend`
   - **Client type**: Select "Public" (browser-based)
   - Click "Next"

3. **Capability Config**
   - Leave defaults, click "Next"

4. **Login Settings**
   - **Root URL**: `http://localhost:5173`
   - **Home URL**: `http://localhost:5173`
   - **Valid redirect URIs**: 
     ```
     http://localhost:5173
     http://localhost:5173/*
     ```
   - **Web origins**: `http://localhost:5173`
   - **Access type**: Public (should be set)
   - Click "Save"

5. **Additional Settings** (if prompted)
   - **Standard Flow Enabled**: ON
   - **Implicit Flow Enabled**: OFF
   - **Direct Access Grants Enabled**: ON (for testing)

---

## Step 4: Create Test User

1. **Go to Users**
   - Left sidebar: Users → "Create new user"

2. **User Details**
   - **Username**: `testuser`
   - **Email**: `test@example.com`
   - **First name**: `Test`
   - **Last name**: `User`
   - **Email verified**: ON
   - **Enabled**: ON
   - Click "Create"

3. **Set Password**
   - Click on the user "testuser"
   - Go to "Credentials" tab
   - Click "Set password"
   - **Password**: `test123`
   - **Temporary**: OFF (unchecked)
   - Click "Set Password"

4. **Add Roles (Optional)**
   - Go to "Role mapping" tab
   - Under "Available roles", select role to assign
   - Click "Assign"

---

## Step 5: Create Test Role (Optional but Recommended)

1. **Go to Roles**
   - Left sidebar: Roles → "Create role"

2. **Role Configuration**
   - **Role name**: `user`
   - Click "Save"

3. **Assign Role to User**
   - Go to Users → testuser
   - "Role mapping" tab
   - Find "user" role in "Available roles"
   - Click "Assign"

---

## Step 6: Get Keycloak Configuration

1. **Get Realm Configuration**
   - URL: `http://127.0.0.1:8080/realms/agent/.well-known/openid-configuration`
   - This contains all metadata (token endpoint, public key endpoint, etc.)

2. **Get Public Keys**
   - URL: `http://127.0.0.1:8080/realms/agent/protocol/openid-connect/certs`
   - This is where backend fetches RSA public keys to validate JWT signatures

3. **Get Token (for testing)**
   ```bash
   curl -X POST http://127.0.0.1:8080/realms/agent/protocol/openid-connect/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "client_id=a2a-agent-frontend&username=testuser&password=test123&grant_type=password"
   ```
   Response will include `access_token` (JWT).

---

## Step 7: Verify JWT Token

1. **Decode JWT Token** (from curl response above)
   - Use [jwt.io](https://jwt.io) to decode
   - Look for:
     - `sub` (user ID)
     - `email` (user email)
     - `name` (user name)
     - `preferred_username` (username)
     - `realm_access.roles` (user roles)
     - `exp` (expiration timestamp)

2. **Example JWT Claims**
   ```json
   {
     "sub": "user-uuid-123",
     "email": "test@example.com",
     "name": "Test User",
     "preferred_username": "testuser",
     "realm_access": {
       "roles": ["user", "default-roles-agent"]
     },
     "exp": 1713012345,
     "iss": "http://127.0.0.1:8080/realms/agent"
   }
   ```

---

## Step 8: Frontend Configuration

Update `wrapper/frontend/.env.local`:

```
VITE_KEYCLOAK_URL=http://127.0.0.1:8080
VITE_KEYCLOAK_REALM=agent
VITE_KEYCLOAK_CLIENT_ID=a2a-agent-frontend
VITE_API_BASE_URL=http://localhost:8000
```

---

## Step 9: Backend Configuration

Update `wrapper/backend/.env`:

```
KEYCLOAK_URL=http://127.0.0.1:8080
KEYCLOAK_REALM=agent
AGENT_URL=http://localhost:10000

# Optional: Langfuse
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

---

## Step 10: Agent Configuration

Set environment variables for the agent:

```bash
export KEYCLOAK_URL=http://127.0.0.1:8080
export KEYCLOAK_REALM=agent
```

The agent now validates JWT tokens directly (no env token list needed).

---

## Testing

### 1. Test Keycloak Login Flow

```bash
# Get token for testuser
curl -X POST http://127.0.0.1:8080/realms/agent/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=a2a-agent-frontend&username=testuser&password=test123&grant_type=password"
```

Save the `access_token` (JWT).

### 2. Test Backend JWT Validation

```bash
KEYCLOAK_JWT="<your-jwt-from-step-1>"

# Call backend health check
curl -X GET http://localhost:8000/health

# Call chat endpoint with JWT
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer $KEYCLOAK_JWT" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 2+2?", "contextId": "test-conv"}'
```

### 3. Test Agent Receives JWT

Start agent with modified auth:
```bash
cd a2a_langchain_agent_advanced
export KEYCLOAK_URL=http://127.0.0.1:8080
export KEYCLOAK_REALM=agent
python -m __main__ --host localhost --port 10000
```

Check logs for:
```
Token validated for user: test@example.com
```

### 4. Test Frontend

```bash
cd wrapper/frontend
npm install
npm run dev
```

Open `http://localhost:5173` in browser:
- Should redirect to Keycloak login
- Login with testuser/test123
- Can chat with agent

---

## Keycloak URLs Reference

| Endpoint | URL |
|----------|-----|
| **Admin Console** | http://127.0.0.1:8080/admin |
| **Realm Metadata** | http://127.0.0.1:8080/realms/agent/.well-known/openid-configuration |
| **Public Keys** | http://127.0.0.1:8080/realms/agent/protocol/openid-connect/certs |
| **Token Endpoint** | http://127.0.0.1:8080/realms/agent/protocol/openid-connect/token |
| **Logout Endpoint** | http://127.0.0.1:8080/realms/agent/protocol/openid-connect/logout |

---

## Troubleshooting

### Issue: "Connection refused" to Keycloak

**Solution**: Ensure Keycloak is running
```bash
docker ps | grep keycloak
# If not running:
docker-compose up -d keycloak
```

### Issue: "Invalid token signature"

**Solution**: Verify public key endpoint is accessible
```bash
curl http://127.0.0.1:8080/realms/agent/protocol/openid-connect/certs
# Should return JSON with "keys" array
```

### Issue: Frontend redirects to blank login page

**Solution**: Check `VITE_KEYCLOAK_*` env vars in `.env.local` match Keycloak config

### Issue: Token expired immediately

**Solution**: Check server time is synchronized
```bash
# Verify token exp claim with current time
date +%s  # Current Unix timestamp
```

---

## Production Considerations

1. **Use HTTPS** for all endpoints (Keycloak, backend, frontend)
2. **Update CORS origins** to match production URLs
3. **Use strong admin password** (not "admin")
4. **Configure persistent database** for Keycloak (instead of H2)
5. **Set token lifetime** based on security requirements
6. **Use Redis** for backend token validation in multi-instance setup
7. **Enable PKCE flow** for enhanced security
8. **Implement refresh token rotation**

---

## Next Steps

1. ✅ Keycloak configured
2. Start backend: `cd wrapper/backend && pip install -r requirements.txt && python -m main`
3. Start agent: `cd a2a_langchain_agent_advanced && python -m __main__`
4. Start frontend: `cd wrapper/frontend && npm install && npm run dev`
5. Open http://localhost:5173 and login with testuser/test123
