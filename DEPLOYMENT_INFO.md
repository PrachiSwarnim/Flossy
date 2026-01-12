# Flossy Project Deployment Documentation

This document contains all the necessary details to generate a CI/CD pipeline and deployment instructions for the "Flossy" project using GitHub Actions. Provide this context to ChatGPT to get a tailored solution.

## 1. Project Architecture
The project is a monorepo containing three distinct services:
1.  **Frontend (`flossy-ui`)**: A React application (Vite).
2.  **Backend (`flossy_backend`)**: A FastAPI Python application.
3.  **ML Service (`flossy-ml-service`)**: A Python-based machine learning service (likely for analytics or specialized processing).

## 2. Service Details

### A. Frontend (`flossy-ui`)
*   **Path**: `./flossy-ui`
*   **Framework**: React + Vite
*   **Packet Manager**: npm
*   **Build Command**: `npm run build`
*   **Output Directory**: `dist` (standard for Vite)
*   **Deployment Target**: Static Site Host (e.g., Vercel, Netlify, Render Static Site, or AWS S3+CloudFront).

### B. Backend (`flossy_backend`)
*   **Path**: `./flossy_backend`
*   **Framework**: FastAPI
*   **Language**: Python 3.x
*   **Dependency Management**: `requirements.txt`
*   **Entry Point**: `main:app` (defined in `Procfile` as `uvicorn main:app --host 0.0.0.0 --port $PORT`)
*   **Database**:
    *   Development: SQLite (`flossy_db.db`)
    *   Production: PostgreSQL (Dependencies `psycopg2-binary` and `sqlalchemy` are present).
*   **Key Dependencies**: `fastapi`, `livekit-agents` (Voice AI), `clerk-backend-api` (Auth), `firebase-admin`, `twilio`, `fpdf2`.
*   **Missing Config**: ostensibly missing a `Dockerfile` in the root of `flossy_backend`, though `render.yaml` references one.
*   **Deployment Target**: Containerized Service (Docker) or Buildpack (Python).

### C. ML Service (`flossy-ml-service`)
*   **Path**: `./flossy-ml-service`
*   **Type**: Python Microservice
*   **Configuration**: Has an existing `dockerfile`.
*   **Entry Point**: `main_ml.py`.

## 3. Environment Variables
The following environment variables are critical for the application:
*   `DATABASE_URL`: Connection string for PostgreSQL (Production) or SQLite (Dev).
*   `CLERK_SECRET_KEY` & `CLERK_PUBLISHABLE_KEY`: For authentication.
*   `LIVEKIT_API_KEY` & `LIVEKIT_API_SECRET` & `LIVEKIT_URL`: For Voice AI features.
*   `OPENAI_API_KEY`: For LLM features.
*   `FIREBASE_CREDENTIALS`: JSON string or path for Firebase.
*   `TWILIO_ACCOUNT_SID` & `TWILIO_AUTH_TOKEN`: For SMS/Calls.

## 4. Suggested Dockerfile for Backend
Since `flossy_backend/Dockerfile` is missing, use this reference:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies (needed for psycopg2, fpdf2, etc)
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port (default 8000 for FastAPI)
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 5. Deployment strategy for ChatGPT
Ask ChatGPT to create a **GitHub Action** that:
1.  **Frontend**:
    *   Installs dependencies (`npm ci`).
    *   Runs lint/test (if scripts exist).
    *   Builds the app (`npm run build`).
    *   (Optional) Deploys to a target like Vercel or Render.
2.  **Backend**:
    *   Sets up Python.
    *   Installs dependencies from `requirements.txt`.
    *   Runs tests (e.g., `pytest`).
    *   Builds a Docker image.
    *   Pushes to a container registry (GHCR or Docker Hub).
    *   Deploys to a provider (e.g., Render, Railway, AWS App Runner).

## 6. Prompt for ChatGPT
*Copy and paste this section to ChatGPT:*

> "I have a monorepo project called Flossy with a React/Vite frontend (`flossy-ui`), a FastAPI backend (`flossy_backend`), and a Python ML service (`flossy-ml-service`).
>
> **The Frontend** is a standard Vite app.
> **The Backend** uses FastAPI, SQLAlchemy (PostgreSQL), and LiveKit agents. It has a `requirements.txt` and a `Procfile` but currently lacks a root Dockerfile.
> **The ML Service** has a Dockerfile.
>
> Please generate:
> 1. A `Dockerfile` for the `flossy_backend`.
> 2. A comprehensive **GitHub Action workflow** (`.github/workflows/deploy.yml`) that:
>    - Checks out the code.
>    - Builds and tests the Frontend.
>    - Builds the Backend Docker image.
>    - (Optional) Pushes the image to GitHub Container Registry.
> 3. A list of **Repository Secrets** I need to add to GitHub for this to work (e.g., API keys, Credentials).
>
> Assume I want to deploy the Backend as a Docker container."
