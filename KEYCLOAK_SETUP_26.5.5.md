# Keycloak 26.5.5 Configuration Guide

Complete step-by-step setup guide for **Keycloak 26.5.5** (updated UI).

## Prerequisites

- Docker installed
- Keycloak 26.5.5 running on `http://127.0.0.1:8080`
- Admin credentials: `admin / admin` (default)

---

## Quick Start: Start Keycloak 26.5.5

### Docker Run (Recommended)

```bash
docker run --name keycloak-26 -d \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  -p 8080:8080 \
  quay.io/keycloak/keycloak:26.5.5 \
  start-dev
```

Wait ~10 seconds for startup, then access: `http://127.0.0.1:8080/admin`

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  keycloak:
    image: quay.io/keycloak/keycloak:26.5.5
    environment:
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

---

## Step-by-Step Configuration

### Step 1: Login to Admin Console

1. Open `http://127.0.0.1:8080/admin`
2. Username: `admin`
3. Password: `admin`

You'll see the new Keycloak 26.5.5 dashboard with:
- Left sidebar with navigation
- Top search bar
- Dark theme (default)

### Step 2: Create a New Realm

**In the sidebar:**

1. Click **"Realm dropdown"** (top-left, shows "master" currently)
2. Click **"Create Realm"** button (or **"+"** button next to realm name)
3. **Realm name**: `agent`
4. Leave **Enabled** toggle ON
5. Click **"Create"**

You're now in the `agent` realm.

**Verify**: The page header should show "agent" realm.

---

### Step 3: Create OpenID Connect Client

Navigate to **Clients** (left sidebar under "Manage"):

1. Click **"Clients"**
2. Click **"Create client"** button (top-right)

#### General Settings
- **Client type**: `OpenID Connect` (default)
- **Client ID**: `a2a-agent-frontend`
- **Name**: `A2A Agent Frontend` (optional)
- Click **"Next"**

#### Capability Config
- **Client authentication**: Toggle **OFF** (for public/browser client)
- **Authentication flow**: Keep defaults
  - ✅ Standard flow enabled
  - ✅ Implicit flow enabled
  - ❌ Direct access grants disabled
  - ✅ Service account roles disabled
- Click **"Next"**

#### Login Settings
- **Root URL**: `http://localhost:5173`
- **Home URL**: `http://localhost:5173` (optional)
- **Valid redirect URIs**: Click **"Add URI"**
  - `http://localhost:5173`
  - `http://localhost:5173/chat`
  - `http://localhost:5173/*`
- **Valid post logout redirect URIs**: Click **"Add URI"**
  - `http://localhost:5173`
- **Web origins**: Click **"Add"**
  - `http://localhost:5173`
  - `http://localhost:*`
- Click **"Save"**

**Verify**: Client "a2a-agent-frontend" appear in Clients list.

---

### Step 4: Create Test User

Navigate to **Users** (left sidebar):

1. Click **"Users"**
2. Click **"Add user"** button (top-right)

#### User Details
- **Username**: `testuser`
- **Email**: `testuser@example.com`
- **Email verified**: Toggle ON
- **Enabled**: Toggle ON
- Click **"Create"**

#### Set Password
After user creation, you'll see tabs. Click **"Credentials"** tab:

1. Click **"Set password"** button
2. **Password**: `test123`
3. **Password confirmation**: `test123`
4. **Temporary**: Toggle OFF (make permanent)
5. Click **"Set password"**

**Verify**: User created successfully without requiring password change.

---

### Step 5: Assign Role to User

#### Create Role First (if not exists)

Navigate to **Roles** (left sidebar under "Manage"):

1. Click **"Roles"**
2. Click **"Create role"** button (top-right)
3. **Role name**: `agent-user`
4. **Description**: `User role for agent access` (optional)
5. Click **"Create"**

#### Assign Role to User

Navigate back to **Users**:

1. Click **"Users"**
2. Click on **"testuser"**
3. Click **"Role mapping"** tab
4. Click **"Assign role"** button
5. Filter for `agent-user` role
6. Click checkbox next to `agent-user`
7. Click **"Assign"**

**Verify**: Under "Effective roles", you see "agent-user" listed.

---

### Step 6: Get Realm Configuration

#### OpenID Connect Configuration URL

You can verify your realm is accessible at:

```
http://127.0.0.1:8080/realms/agent/.well-known/openid-configuration
```

This returns JSON with:
- `issuer`
- `token_endpoint`
- `jwks_uri`
- `userinfo_endpoint`

#### Get Public Keys

For JWT validation, fetch public keys from:

```
http://127.0.0.1:8080/realms/agent/protocol/openid-connect/certs
```

This returns RSA public keys in JWK format.

---

### Step 7: Get Test JWT Token

#### Method 1: Using curl

```bash
curl -X POST \
  http://127.0.0.1:8080/realms/agent/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=a2a-agent-frontend" \
  -d "username=testuser" \
  -d "password=test123" \
  -d "grant_type=password" \
  -d "scope=openid profile email"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR...",
  "expires_in": 300,
  "refresh_expires_in": 1800,
  "token_type": "Bearer",
  "id_token": "eyJhbGciOiJSUzI1NiIsInR..."
}
```

Copy the `access_token` value (starts with `eyJ...`).

#### Method 2: Via Frontend (Easier)

1. Open `http://localhost:5173` in browser
2. Click "Login with Keycloak"
3. Login with `testuser / test123`
4. You'll be redirected to chat
5. Token is automatically stored in browser session

#### Verify Token Content

Paste token at `https://jwt.io`:

You should see claims:
```json
{
  "sub": "user_uuid",
  "email": "testuser@example.com",
  "preferred_username": "testuser",
  "name": "testuser",
  "realm_access": {
    "roles": ["default-roles-agent", "agent-user"]
  }
}
```

---

## Configuration Files

### Frontend .env.local

Save as `wrapper/frontend/.env.local`:

```env
VITE_KEYCLOAK_URL=http://127.0.0.1:8080
VITE_KEYCLOAK_REALM=agent
VITE_KEYCLOAK_CLIENT_ID=a2a-agent-frontend
VITE_API_BASE_URL=http://localhost:8000
```

### Backend .env

Save as `wrapper/backend/.env`:

```env
KEYCLOAK_URL=http://127.0.0.1:8080
KEYCLOAK_REALM=agent
AGENT_URL=http://localhost:10000
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

### Agent .env (Optional - for Langfuse)

```env
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

Leave empty if not using Langfuse observability.

---

## Testing the Setup

### 1. Test Keycloak is Running

```bash
curl http://127.0.0.1:8080/admin/realms
```

Should return realm list (HTTP 200).

### 2. Test Realm Exists

```bash
curl http://127.0.0.1:8080/realms/agent/.well-known/openid-configuration
```

Should return OpenID config (HTTP 200).

### 3. Test Get Token

```bash
curl -X POST \
  http://127.0.0.1:8080/realms/agent/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=a2a-agent-frontend&username=testuser&password=test123&grant_type=password"
```

Should return token with `access_token` field.

### 4. Test JWT Validation (Backend)

First get a token, then:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  http://localhost:8000/health
```

Should return 200 with agent URL.

### 5. Full End-to-End Test

1. Start Keycloak: `docker run ... keycloak:26.5.5 ...`
2. Start Agent: `python __main__.py`
3. Start Backend: `pip install -r wrapper/backend/requirements.txt && uvicorn wrapper.backend.main:app`
4. Start Frontend: `cd wrapper/frontend && npm run dev`
5. Open `http://localhost:5173`
6. Login with `testuser / test123`
7. Send a chat message
8. Should see response from agent

---

## Keycloak 26.5.5 New Features / UI Changes

### Changed from Earlier Versions:

| Feature | Keycloak 23 | Keycloak 26.5.5 |
|---------|-------------|-----------------|
| **Admin Console** | Legacy UI | New React-based UI |
| **Realm Creation** | Dialog box | "Create Realm" button |
| **Client Type Selection** | After creation | During creation (OpenID Connect vs SAML) |
| **Client Authentication** | Toggle in client | "Capability config" tab |
| **Roles** | Separate tab | Under Manage → Roles |
| **User Role Assignment** | Realm roles tab | "Assign role" button in user details |
| **Red Hat Branding** | Minimal | More prominent in UI |
| **Theme** | Light default | Dark theme default (Keycloak redesign) |

### New in 26.5.5:

- ✨ Revamped admin UI with better UX
- ✨ Improved client configuration flow
- ✨ Better role management
- ✨ Enhanced search functionality
- ✨ Updated OpenID Connect compliance

---

## URL Reference Table

| Component | URL |
|-----------|-----|
| **Admin Console** | `http://127.0.0.1:8080/admin` |
| **Keycloak Home** | `http://127.0.0.1:8080` |
| **Realm Config** | `http://127.0.0.1:8080/realms/agent/.well-known/openid-configuration` |
| **Public Keys (JWKS)** | `http://127.0.0.1:8080/realms/agent/protocol/openid-connect/certs` |
| **Token Endpoint** | `http://127.0.0.1:8080/realms/agent/protocol/openid-connect/token` |
| **Userinfo Endpoint** | `http://127.0.0.1:8080/realms/agent/protocol/openid-connect/userinfo` |
| **Logout Endpoint** | `http://127.0.0.1:8080/realms/agent/protocol/openid-connect/logout` |

---

## Troubleshooting

### Issue: "Cannot connect to Keycloak on port 8080"

**Solution:**
```bash
# Check Keycloak is running
docker ps | grep keycloak

# If not running, start it
docker run --name keycloak-26 -d \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  -p 8080:8080 \
  quay.io/keycloak/keycloak:26.5.5 \
  start-dev

# Wait 15 seconds and try again
```

### Issue: "Client not found" or "Invalid client_id"

**Solution:**
- Verify client name is exactly `a2a-agent-frontend` (case-sensitive)
- Ensure you're in the **agent** realm (not master)
- Try refreshing browser cache

### Issue: "Invalid redirect URI"

**Solution:**
- Frontend URL must match exactly in Keycloak client config
- Valid redirect URIs must include:
  - `http://localhost:5173`
  - `http://localhost:5173/chat`
  - `http://localhost:5173/*`

### Issue: "User credentials invalid"

**Solution:**
- Verify user is **enabled** (toggle ON)
- Verify password was set (not temporary)
- Try: `curl` to token endpoint to test

### Issue: "Invalid signature" error in backend

**Solution:**
- Backend is trying to validate with wrong public key
- Verify `KEYCLOAK_URL=http://127.0.0.1:8080` (no trailing slash)
- Verify `KEYCLOAK_REALM=agent` (exact realm name)
- Clear backend cache: delete `.keycloak_cache` file
- Restart backend

### Issue: "User lacks 'agent-user' role"

**Solution:**
- Verify role exists: Roles → agent-user
- Verify testuser has role assigned: Users → testuser → Role mapping
- Verify role appears in "Effective roles"
- JWT should contain: `"realm_access": {"roles": ["agent-user", ...]}`

### Issue: Frontend redirects to login loop

**Solution:**
```env
# Verify .env.local has correct URLs
VITE_KEYCLOAK_URL=http://127.0.0.1:8080  # No trailing slash
VITE_KEYCLOAK_REALM=agent
VITE_KEYCLOAK_CLIENT_ID=a2a-agent-frontend
VITE_API_BASE_URL=http://localhost:8000
```

- Check browser console for CORS errors
- Verify backend CORS allows frontend origin
- Check Keycloak client has correct redirect URIs

---

## Production Considerations

### 1. Security

- ❌ **Never use** default credentials (`admin/admin`) in production
- ❌ **Never enable** password grant flow in production (use Authorization Code flow)
- ✅ **Use HTTPS** for all URLs (`https://` instead of `http://`)
- ✅ **Use strong passwords** for admin and test users
- ✅ **Enable CSRF protection** in Keycloak settings

### 2. Database

- ❌ **Don't use** embedded H2 database (dev-only)
- ✅ **Use PostgreSQL or MySQL** in production
- ✅ **Enable automatic backups**
- ✅ **Use SSL/TLS for database connection**

### 3. Scaling

- ✅ **Use separate Keycloak instance** (not dev mode)
- ✅ **Configure load balancing** for multiple instances
- ✅ **Use shared cache** (Infinispan Redis)
- ✅ **Monitor the instance** (Prometheus, Grafana)

### 4. Configuration

- ✅ Use environment variables for all config
- ✅ Keep credentials in `.env` (not in `docker-compose.yml`)
- ✅ Enable audit logging
- ✅ Configure token expiration properly (5-10 min for access, 1-7 days for refresh)

---

## Next Steps

1. ✅ Keycloak 26.5.5 configured and running
2. ✅ Test user created with `agent-user` role
3. 👉 **Next**: Start your A2A Agent
   ```bash
   python __main__.py
   ```
4. 👉 **Then**: Start backend wrapper
   ```bash
   cd wrapper/backend
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```
5. 👉 **Finally**: Start frontend
   ```bash
   cd wrapper/frontend
   npm install
   npm run dev
   ```
6. Open `http://localhost:5173` and login with `testuser / test123`

---

## Support

- **Keycloak Docs**: https://www.keycloak.org/documentation
- **Keycloak Admin Guide**: https://www.keycloak.org/docs/latest/server_admin/
- **OpenID Connect**: https://openid.net/connect/
- **JWT.io**: https://jwt.io (for token validation)

