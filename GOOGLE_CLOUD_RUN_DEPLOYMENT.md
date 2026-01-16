# Deploying Flossy to Google Cloud Run: Instructions for ChatGPT

Copy and paste the entire content of this document into ChatGPT to get a step-by-step deployment execution plan for Google Cloud Run.

---

## 🚀 Context for AI (Deployment Task)

I have a full-stack dental clinic application called **Flossy**. I want to deploy it to **Google Cloud Run**.

### Project Structure:
- `/flossy_backend`: FastAPI (Python 3.12) backend.
- `/flossy-ui`: React + Vite (Node.js) frontend.

### Tech Stack Details:
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, Gemini AI, Groq AI, Clerk Auth.
- **Frontend**: React, Vite, Clerk SDK.
- **Database**: PostgreSQL (GCP Cloud SQL recommended).

---

## 🛠 Required Documentation Files

Please use the following templates and steps to guide me through the deployment using `gcloud` CLI or GitHub Actions.

### 1. Backend Dockerfile (`flossy_backend/Dockerfile`)
Ensure the backend has this Dockerfile in its root:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for psycopg2 and other tools
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run expects the app to listen on the $PORT env var
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 2. Frontend Dockerfile (`flossy-ui/Dockerfile`)
We will serve the static React build using Nginx on Cloud Run:

```dockerfile
# Stage 1: Build
FROM node:18-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# You must ensure VITE_API_BASE_URL is set during build for Cloud Run
ARG VITE_API_BASE_URL
RUN VITE_API_BASE_URL=$VITE_API_BASE_URL npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Custom nginx config to handle SPA routing
RUN echo 'server { \
    listen 8080; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
```

---

## 📋 Deployment Execution Plan (Step-by-Step)

ChatGPT, please provide specific `gcloud` commands for the following steps:

### Phase 1: Resource Provisioning
1.  **Project Setup**: Enable Cloud Run, Artifact Registry, and Cloud SQL APIs.
2.  **Artifact Registry**: Create a repository for the Docker images.
3.  **Cloud SQL**: Create a PostgreSQL instance (Public IP with "Authorized networks" or Private Service Access).
4.  **Secret Manager**: Store sensitive keys (Clerk, Gemini, Groq) in GCP Secret Manager.

### Phase 2: Backend Deployment
1.  **Build & Push**: Build the backend image and push to Artifact Registry.
2.  **Deploy to Cloud Run**:
    *   Set `$PORT` to 8080.
    *   Connect to the Cloud SQL instance using `/cloudsql/` connection string.
    *   Map environment variables from Secret Manager.

### Phase 3: Frontend Deployment
1.  **Build & Push**: Build the frontend image, passing the Backend URL as a build argument (`--build-arg VITE_API_BASE_URL=...`).
2.  **Deploy to Cloud Run**: Deploy the Nginx container as a public service.

### Phase 4: Final Configuration
1.  **CORS**: Update the backend `CORS_ORIGINS` to allow the newly deployed frontend URL.
2.  **Custom Domains**: (Optional) Configure domain mapping for both services.

---

## 🔐 Environment Variables Needed

| Variable Name | Source |
| :--- | :--- |
| `DATABASE_URL` | `postgresql+psycopg2://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE` |
| `CLERK_SECRET_KEY` | Secret Manager |
| `GEMINI_API_KEY` | Secret Manager |
| `GROQ_API_KEY` | Secret Manager |
| `CORS_ORIGINS` | Deployed Frontend URL |

---

## 🎯 Task for ChatGPT
1. Generate the exact `gcloud` commands I need to run in my terminal.
2. Explain how to link a Google Cloud SQL instance to the Cloud Run service using the socket path.
3. Provide a GitHub Actions YAML file that automates this entire process on every push to `main`.

---
