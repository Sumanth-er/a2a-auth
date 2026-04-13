# Keycloak 26.5.5 Setup - Quick Start Guide

Complete setup guide for **Keycloak 26.5.5** with automated scripts and step-by-step instructions.

## Files Provided

1. **KEYCLOAK_SETUP_26.5.5.md** - Detailed step-by-step configuration guide with UI screenshots/descriptions
2. **keycloak-26.5.5-docker-compose.yml** - Docker Compose configuration file
3. **keycloak-setup.sh** - Automated bash script for Linux/macOS
4. **keycloak-setup.ps1** - Automated PowerShell script for Windows
5. **This README** - Quick reference

---

## Quick Start (3 Steps)

### Step 1: Start Keycloak 26.5.5

Choose your method:

#### Option A: Docker Compose (Recommended)

```bash
docker-compose -f keycloak-26.5.5-docker-compose.yml up -d
```

Wait 15 seconds for startup.

#### Option B: Docker Run

```bash
docker run --name keycloak-26 -d \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  -p 8080:8080 \
  quay.io/keycloak/keycloak:26.5.5 \
  start-dev
```

#### Option C: Manual Configuration

If you prefer manual setup, skip to **Step 3** and follow **KEYCLOAK_SETUP_26.5.5.md**.

---

### Step 2: Automated Configuration

After Keycloak starts, run the setup script:

#### For Linux/macOS:

```bash
chmod +x keycloak-setup.sh
./keycloak-setup.sh
```

#### For Windows (PowerShell):

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\keycloak-setup.ps1
```

Both scripts will:
- ✅ Create realm `agent`
- ✅ Create test user `testuser` with password `test123`
- ✅ Create role `agent-user`
- ✅ Create OpenID Connect client `a2a-agent-frontend`
- ✅ Configure all redirect URIs

---

### Step 3: Verify Setup

Check if everything is configured:

```bash
# Get OpenID Connect configuration
curl http://127.0.0.1:8080/realms/agent/.well-known/openid-configuration

# Get test token
curl -X POST http://127.0.0.1:8080/realms/agent/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=a2a-agent-frontend&username=testuser&password=test123&grant_type=password"

# Should return JWT token starting with "eyJ..."
```

---

## Testing the System

### Terminal 1: Keycloak (Already Running)

```bash
# Already running from Step 1
```

### Terminal 2: Start A2A Agent

```bash
python __main__.py
```

### Terminal 3: Start Backend Wrapper

```bash
cd wrapper/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Terminal 4: Start Frontend

```bash
cd wrapper/frontend
npm install  # Only first time
npm run dev
```

### Open in Browser

```
http://localhost:5173
```

Login with:
- **Username**: `testuser`
- **Password**: `test123`

---

## Manual Configuration

If the automated scripts fail, follow **KEYCLOAK_SETUP_26.5.5.md** for manual step-by-step setup with detailed UI instructions.

### Key Differences in Keycloak 26.5.5 UI:

| Task | How It Changed |
|------|---|
| **Create Realm** | Click "Create Realm" button (top-left) |
| **Create Client** | "Create client" dialog appears directly |
| **Client Config** | Tabs: General → Capability Config → Login Settings |
| **Assign Role** | Users → [user] → "Assign role" button |
| **Admin Console** | New React UI (vs older legacy UI) |

---

## Configuration Files

Create `.env` files as shown below:

### Frontend: `wrapper/frontend/.env.local`

```env
VITE_KEYCLOAK_URL=http://127.0.0.1:8080
VITE_KEYCLOAK_REALM=agent
VITE_KEYCLOAK_CLIENT_ID=a2a-agent-frontend
VITE_API_BASE_URL=http://localhost:8000
```

### Backend: `wrapper/backend/.env`

```env
KEYCLOAK_URL=http://127.0.0.1:8080
KEYCLOAK_REALM=agent
AGENT_URL=http://localhost:10000
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

### Agent: `.env` (Optional - for Langfuse)

```env
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

---

## Troubleshooting

### "Cannot connect to Keycloak on port 8080"

```bash
# Check if container is running
docker ps | grep keycloak

# If not, restart it
docker-compose -f keycloak-26.5.5-docker-compose.yml up -d

# Wait 15 seconds and try again
```

### "Access denied. You must have 'agent-user' role"

Ensure testuser has the `agent-user` role:

1. Login to admin console: `http://127.0.0.1:8080/admin`
2. Go to **Users** → **testuser**
3. Click **"Role mapping"** tab
4. Click **"Assign role"** 
5. Select **agent-user**
6. Click **"Assign"**

### "Invalid redirect URI"

Verify frontend URL in Keycloak client config:
- Must include: `http://localhost:5173`
- Must include: `http://localhost:5173/*`
- Restart frontend if URL changed

### "Invalid signature" error in backend logs

Clear Keycloak key cache:

```bash
# Restart backend
cd wrapper/backend
uvicorn main:app --reload
```

Keycloak keys are cached automatically. If you change Keycloak settings, restart the backend.

---

## Key URLs

| Component | URL |
|-----------|-----|
| **Keycloak Admin** | `http://127.0.0.1:8080/admin` |
| **OpenID Config** | `http://127.0.0.1:8080/realms/agent/.well-known/openid-configuration` |
| **Public Keys** | `http://127.0.0.1:8080/realms/agent/protocol/openid-connect/certs` |
| **Token Endpoint** | `http://127.0.0.1:8080/realms/agent/protocol/openid-connect/token` |
| **Frontend** | `http://localhost:5173` |
| **Backend API** | `http://localhost:8000` |
| **Agent** | `http://localhost:10000` |

---

## Default Credentials

| Component | Username | Password |
|-----------|----------|----------|
| **Keycloak Admin** | admin | admin |
| **Test User** | testuser | test123 |

⚠️ **Change these in production!**

---

## Script Options

### keycloak-setup.sh (Bash)

```bash
# Use default values
./keycloak-setup.sh

# Custom Keycloak URL
./keycloak-setup.sh --keycloak-url http://my-keycloak:8080

# Custom realm
./keycloak-setup.sh --realm my-app
```

### keycloak-setup.ps1 (PowerShell)

```powershell
# Use default values
.\keycloak-setup.ps1

# Custom Keycloak URL
.\keycloak-setup.ps1 -KeycloakUrl http://my-keycloak:8080

# Custom realm
.\keycloak-setup.ps1 -Realm my-app
```

---

## Next Steps

1. ✅ **Keycloak configured** - This document
2. ✅ **Start Agent, Backend, Frontend** - See "Testing the System" above
3. 👉 **Login and test**: Open `http://localhost:5173`
4. 👉 **Send messages** to verify JWT token passing
5. 👉 **Check logs** in all three terminals for JWT user context
6. 👉 **Deploy to production** when ready

---

## Documentation

- **Detailed Setup**: See `KEYCLOAK_SETUP_26.5.5.md` for step-by-step UI instructions
- **Deployment**: See `DEPLOYMENT.md` for production deployment
- **Implementation**: See `IMPLEMENTATION_SUMMARY.md` for architecture overview

---

## Support

- **Keycloak Docs**: https://www.keycloak.org/documentation
- **OpenID Connect**: https://openid.net/connect/
- **JWT Validation**: https://jwt.io

---

## What Happens During Setup

### The `keycloak-setup.sh` Script Performs:

1. **Verifies Keycloak is running** on port 8080
2. **Authenticates as admin** using master realm
3. **Creates realm "agent"** with:
   - Access token lifetime: 5 minutes
   - Refresh token maximum reuse: unlimited
4. **Creates role "agent-user"** for role-based access control
5. **Creates test user "testuser"** with:
   - Email: testuser@example.com
   - Enabled: true
   - Password: test123 (permanent, not temporary)
6. **Creates OpenID Connect client "a2a-agent-frontend"** with:
   - Type: Public (browser-based)
   - Authentication: Disabled (public client)
   - Flows enabled:
     - Standard flow (Authorization Code)
     - Implicit flow (for legacy support)
   - Redirect URIs configured for localhost:5173
   - CORS allowed for localhost

All via REST API - no manual clicking needed!

---

EOF
