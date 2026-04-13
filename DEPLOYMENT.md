# A2A Agent Keycloak Wrapper - Deployment Guide

Complete setup guide to run all components: Agent, Backend Wrapper, Frontend, and Keycloak.

---

## System Architecture

```
User Browser (http://localhost:5173)
    ↓ (Redirect to Keycloak login)
Keycloak (http://127.0.0.1:8080)
    ↓ (Return JWT)
React Frontend (http://localhost:5173)
    ↓ (Send JWT to backend)
FastAPI Backend (http://localhost:8000)
    ├─ Validate JWT signature
    └─ Forward to agent
A2A Agent (http://localhost:10000)
    ├─ Validate JWT from Keycloak
    ├─ Extract user info
    └─ Process with Langfuse observability
```

---

## Prerequisites

- **OS**: Windows 10/11, macOS, or Linux
- **Python**: 3.12+
- **Node.js**: 18+
- **Docker**: Latest version (for Keycloak)
- **Git**: For cloning repositories

---

## Quick Start (All Components)

### Step 0: Prepare Environment

```bash
# Clone or navigate to project
cd c:\Users\suman\Desktop\A2A_Chat_Bot-main\a2a_langchain_agent_advanced

# Create main .env for agent
cat > .env << 'EOF'
model_source=ollama
KEYCLOAK_URL=http://127.0.0.1:8080
KEYCLOAK_REALM=agent
EOF
```

### Step 1: Start Keycloak (Terminal 1)

```bash
# Using Docker
docker run --name keycloak -d \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  -p 8080:8080 \
  quay.io/keycloak/keycloak:latest \
  start-dev

# Wait 30 seconds for Keycloak to start
# Then configure using KEYCLOAK_SETUP.md
```

**Expected Output**:
```
Keycloak 23.0.0 started on http://127.0.0.1:8080
```

### Step 2: Configure Keycloak

Follow [KEYCLOAK_SETUP.md](./KEYCLOAK_SETUP.md) steps 2-9:
- Create realm "agent"
- Create client "a2a-agent-frontend"
- Create test user testuser/test123
- Verify JWT endpoint

### Step 3: Start A2A Agent (Terminal 2)

```bash
# Install dependencies (if not already done)
pip install -e .

# Start agent on port 10000
python -m __main__ --host localhost --port 10000
```

**Expected Output**:
```
2026-04-13 10:00:00 - INFO - Keycloak initialized successfully
2026-04-13 10:00:01 - INFO - Agent server running on http://localhost:10000
```

### Step 4: Start Backend Wrapper (Terminal 3)

```bash
cd wrapper/backend

# Install dependencies
pip install -r requirements.txt

# Create .env if not exists
cat > .env << 'EOF'
KEYCLOAK_URL=http://127.0.0.1:8080
KEYCLOAK_REALM=agent
AGENT_URL=http://localhost:10000
EOF

# Start backend
python -m main
```

**Expected Output**:
```
INFO:     Started server process
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 5: Start Frontend (Terminal 4)

```bash
cd wrapper/frontend

# Install dependencies
npm install

# Create .env.local if not exists
cat > .env.local << 'EOF'
VITE_KEYCLOAK_URL=http://127.0.0.1:8080
VITE_KEYCLOAK_REALM=agent
VITE_KEYCLOAK_CLIENT_ID=a2a-agent-frontend
VITE_API_BASE_URL=http://localhost:8000
EOF

# Start dev server
npm run dev
```

**Expected Output**:
```
  VITE v5.0.0  ready in 234 ms

  ➜  Local:   http://127.0.0.1:5173/
  ➜  Ready!
```

### Step 6: Test the Application

1. Open browser: `http://localhost:5173`
2. Should redirect to Keycloak login
3. Login with credentials:
   - Username: `testuser`
   - Password: `test123`
4. After login, redirects to chat interface
5. Try asking: "What is 2 + 2?"
6. Agent should respond with calculation

---

## Component Details

### A2A Agent (Port 10000)

**Purpose**: LLM-powered calculator agent with Keycloak JWT validation

**Files Modified**:
- `auth.py` - Validates Keycloak JWT instead of opaque tokens
- `agent.py` - Accepts JWT token, decodes claims, logs with Langfuse
- `agent_executor.py` - Extracts JWT from request, passes to agent
- `pyproject.toml` - Added pyjwt, cryptography, httpx, langfuse

**Environment Variables**:
```
KEYCLOAK_URL=http://127.0.0.1:8080
KEYCLOAK_REALM=agent
LANGFUSE_PUBLIC_KEY=<optional>
LANGFUSE_SECRET_KEY=<optional>
```

**Testing the Agent Directly**:
```bash
# Get JWT from Keycloak
JWT=$(curl -s -X POST http://127.0.0.1:8080/realms/agent/protocol/openid-connect/token \
  -d "client_id=a2a-agent-frontend&username=testuser&password=test123&grant_type=password" \
  | jq -r '.access_token')

# Call agent
curl -X POST http://localhost:10000/ \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 5 * 3?"}'
```

### Backend Wrapper (Port 8000)

**Purpose**: Validates Keycloak JWT, proxies to agent, extracts user info

**Files Created**:
- `wrapper/backend/main.py` - FastAPI app with /api/chat endpoint
- `wrapper/backend/auth.py` - Keycloak JWT validation
- `wrapper/backend/config.py` - Configuration management

**Endpoints**:
- `GET /health` - Health check
- `POST /api/chat` - Send message to agent
- `GET /api/user-info` - Get authenticated user info

**Testing the Backend**:
```bash
# Get JWT (from step above)
JWT=<your-jwt>

# Health check
curl http://localhost:8000/health

# Send message
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 10 + 5?", "contextId": "conv-1"}'

# Get user info
curl http://localhost:8000/api/user-info \
  -H "Authorization: Bearer $JWT"
```

### Frontend (Port 5173)

**Purpose**: React UI with Keycloak login, chat interface

**Files Created**:
- `wrapper/frontend/src/context/AuthContext.jsx` - Keycloak auth state
- `wrapper/frontend/src/pages/Login.jsx` - Login redirect
- `wrapper/frontend/src/pages/Chat.jsx` - Chat interface
- `wrapper/frontend/src/main.jsx` - App routing

**Features**:
- Automatic redirect to Keycloak login
- JWT-based API auth
- Real-time chat messages
- User info display
- Logout functionality

### Keycloak (Port 8080)

**Purpose**: Auth server providing JWT tokens

**Config**:
- Realm: `agent`
- Client: `a2a-agent-frontend` (public)
- Test User: `testuser/test123`

---

## Running with Docker Compose (Optional)

Create `docker-compose.yml` in project root:

```yaml
version: '3.8'

services:
  keycloak:
    image: quay.io/keycloak/keycloak:latest
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin
    ports:
      - "8080:8080"
    command: start-dev

  backend:
    build:
      context: .
      dockerfile: wrapper/backend/Dockerfile
    ports:
      - "8000:8000"
    environment:
      KEYCLOAK_URL: http://keycloak:8080
      KEYCLOAK_REALM: agent
      AGENT_URL: http://agent:10000
    depends_on:
      - keycloak

  agent:
    build:
      context: .
    ports:
      - "10000:10000"
    environment:
      KEYCLOAK_URL: http://keycloak:8080
      KEYCLOAK_REALM: agent
    depends_on:
      - keycloak
```

With Docker Compose:
```bash
docker-compose up -d
# Wait 30 seconds
# Then configure Keycloak at http://127.0.0.1:8080/admin
```

---

## Troubleshooting

### Frontend doesn't redirect to Keycloak

```bash
# Check .env.local
cat wrapper/frontend/.env.local

# Ensure Keycloak is running
curl http://127.0.0.1:8080/auth

# Clear browser cache and try again
```

### Backend can't validate JWT

```bash
# Check Keycloak public keys are accessible
curl http://127.0.0.1:8080/realms/agent/protocol/openid-connect/certs

# Check backend logs for JWT validation errors
# Look in backend terminal for error messages
```

### Agent doesn't accept JWT

```bash
# Check agent is using KeycloakJWTCallContextBuilder
grep -n "KeycloakJWT" a2a_langchain_agent_advanced/__main__.py

# Ensure KEYCLOAK_URL env var is set
echo $KEYCLOAK_URL
```

### "Connection refused" errors

```bash
# Check all ports are available
netstat -an | grep LISTEN  # Windows: netstat -ano

# Free ports:
# 8080 - Keycloak
# 10000 - Agent
# 8000 - Backend
# 5173 - Frontend
```

---

## Logs and Debugging

### View Agent Logs

Agent logs show:
- JWT validation: `Token validated for user: test@example.com`
- Langfuse events: `Agent invoked by test@example.com`
- Tool calls: `Invoking add tool`

### View Backend Logs

Backend logs show:
- JWT validation: `Token validated for user`
- Chat requests: `Chat request from test@example.com`
- Proxy calls: `Agent error` (if agent down)

### View Frontend Logs

Browser console (F12 → Console):
- Auth state: `Keycloak authenticated`
- API errors: `Failed to get response`
- Routing: `Navigate to /chat`

---

## Performance Tuning

### Backend Caching

Backend caches Keycloak public keys for 1 hour. To refresh:
```python
# In wrapper/backend/auth.py
# Modify: @lru_cache(maxsize=1) to clear cache periodically
```

### Agent Memory

Agent stores conversation history in memory. For large conversations:
```bash
# Increase Python memory limit
python -m __main__ --timeout 120  # 120 second timeout
```

### Frontend Build Optimization

```bash
cd wrapper/frontend
npm run build
# Creates optimized production build in dist/
```

---

## Security Checklist

- [ ] Use HTTPS in production (not HTTP)
- [ ] Update Keycloak admin password
- [ ] Set strong JWT secret in Keycloak
- [ ] Restrict CORS origins to production URL
- [ ] Enable PKCE flow in Keycloak client
- [ ] Use Redis instead of in-memory token store
- [ ] Rotate Keycloak signing keys periodically
- [ ] Monitor token usage and expiration
- [ ] Implement rate limiting on backend
- [ ] Enable HTTPS redirect in production

---

## Next Steps After Setup

1. ✅ All components running
2. Customize agent capabilities in `agent.py`
3. Add more Keycloak users/roles in admin console
4. Deploy frontend to production (Vercel, Netlify, etc.)
5. Set up Langfuse observability (if using licenses)
6. Configure CI/CD pipeline
7. Switch to production Keycloak database
8. Set up monitoring and alerting

---

## Support

For issues:
1. Check logs in each terminal
2. Review Keycloak configuration in admin console
3. Test endpoints manually with curl
4. Check browser console for frontend errors
