# 🚀 Hybrid Deployment Guide: Vercel + AWS
## Domain: smileartistsdentalstudio.com

This guide provides a high-performance, cost-effective hybrid setup:
*   **Frontend**: Hosted on **Vercel** (Fastest, easiest, auto-HTTPS, global CDN).
*   **Backend**: Hosted on **AWS EC2** (Complete control, persistent connection for AI/WebSockets).
*   **Database**: Hosted on **AWS RDS** (Reliable managed storage).

---

## 📋 Table of Contents
1. [Step 1: Domain Configuration (DNS)](#step-1-domain-configuration-dns)
2. [Step 2: Deploy Backend to AWS](#step-2-deploy-backend-to-aws)
3. [Step 3: Deploy Frontend to Vercel](#step-3-deploy-frontend-to-vercel)
4. [Step 4: Final Connection & Testing](#step-4-final-connection--testing)

---

## 🏗️ Step 1: Domain Configuration (DNS)

Since you own **smileartistsdentalstudio.com**, we will split traffic:
- **`smileartistsdentalstudio.com`** (Frontend) -> Points to Vercel.
- **`api.smileartistsdentalstudio.com`** (Backend) -> Points to AWS.

### 1.1 Managing DNS
Where did you buy the domain?
- **AWS Route 53**: Go to Route 53 → Hosted Zones.
- **GoDaddy/Namecheap**: Go to your DNS Management dashboard.

You will add records in the steps below after setting up the servers.

---

## ☁️ Step 2: Deploy Backend to AWS (EC2 + RDS)

### 2.1 Database (RDS PostgreSQL)
1. Log in to AWS Console → **RDS** → **Create database**.
2. Select **PostgreSQL** → **Free Tier** template.
3. **Settings:**
   - DB Instance ID: `smileartists-db`
   - Master username: `flossy_admin`
   - Password: `(Create a strong password)`
4. **Connectivity:**
   - Public access: **Yes**.
   - Create new Security Group: `flossy-db-sg`.
5. **Create**. Copy the **Endpoint** (URL) once created.

### 2.2 Backend Server (EC2)
1. Go to **EC2** → **Launch Instance**.
2. **Name:** `SmileArtists-Backend`.
3. **OS:** Ubuntu Server 24.04 LTS (or 22.04).
4. **Instance Type:** `t3.small`.
5. **Key Pair:** Create/Download `smileartists-key.pem`.
6. **Network:** Allow SSH, HTTP, HTTPS.
7. **Launch**.
8. **Get Static IP**: Go to **Elastic IPs** → Allocate → Associate with your instance.
   - **Copy this IP** (e.g., `54.123.45.67`).

### 2.3 Connect Domain to Backend (DNS)
Go to your DNS Manager (Route 53 / GoDaddy):
1. Create a **A Record**.
2. **Name:** `api` (Result: `api.smileartistsdentalstudio.com`)
3. **Value:** `54.123.45.67` (Your EC2 IP)
4. **TTL:** 60 seconds (or default).

### 2.4 Auto-Deploy Backend (GitHub Actions)
Create `.github/workflows/deploy-backend.yml`:

```yaml
name: Deploy Backend (AWS)
on:
  push:
    branches: [main]
    paths: ['flossy_backend/**', '.github/workflows/deploy-backend.yml']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to EC2
        uses: appleboy/ssh-action@v0.1.6
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ubuntu
          key: ${{ secrets.EC2_KEY }}
          script: |
            # 1. Setup Code
            [ ! -d "/home/ubuntu/Flossy" ] && git clone https://github.com/YOUR_USERNAME/Flossy.git /home/ubuntu/Flossy
            cd /home/ubuntu/Flossy
            git pull origin main
            
            # 2. Setup Environment
            cd flossy_backend
            sudo apt update && sudo apt install -y python3-venv python3-pip
            python3 -m venv venv
            source venv/bin/activate
            pip install -r requirements.txt
            
            # 3. Write Secrets (Safe way)
            echo "DATABASE_URL=${{ secrets.DATABASE_URL }}" > .env
            echo "CLERK_SECRET_KEY=${{ secrets.CLERK_SECRET_KEY }}" >> .env
            echo "CLERK_PUBLISHABLE_KEY=${{ secrets.VITE_CLERK_PUBLISHABLE_KEY }}" >> .env
            echo "GOOGLE_API_KEY=${{ secrets.GOOGLE_API_KEY }}" >> .env
            # IMPORTANT: Whitelist Vercel Frontend
            echo "FRONTEND_ORIGINS=https://smileartistsdentalstudio.com,https://www.smileartistsdentalstudio.com" >> .env
            
            # 4. Restart Service
            sudo systemctl restart flossy-backend || echo "Service not ready"
```
*Don't forget to add your secrets (EC2_HOST, EC2_KEY, DATABASE_URL, etc.) in GitHub Settings!*

---

## ▲ Step 3: Deploy Frontend to Vercel

Vercel is much easier than S3+CloudFront and offers simpler CI/CD.

1. **Push your code** to GitHub.
2. Go to [Vercel.com](https://vercel.com) → **Add New** → **Project**.
3. Import your **Flossy** repository.
4. **Configure Project:**
   - **Framework Preset:** Vite
   - **Root Directory:** Edit → Select `flossy-ui` folder.
5. **Environment Variables:**
   Add these before clicking Deploy:
   
   | Name | Value |
   |------|-------|
   | `VITE_API_BASE_URL` | `https://api.smileartistsdentalstudio.com` |
   | `VITE_CLERK_PUBLISHABLE_KEY` | (Your Clerk Key) |

6. Click **Deploy**.

### 3.1 Connect Domain to Vercel
1. Once deployed, go to your Vercel Project Dashboard → **Settings** → **Domains**.
2. Enter `smileartistsdentalstudio.com`.
3. Vercel will give you DNS records to add.
    - If using Route 53 or GoDaddy, add the **A Record** (76.76.21.21) and **CNAME** provided by Vercel.
    - Since you already set up `api` subdomain for AWS, this will NOT conflict!

---

## ✅ Step 4: Final Connection & Testing

1. **Wait for DNS Propagation**: It might take 15-30 mins for `api.smileartistsdentalstudio.com` to resolve globally.
2. **Verify Backend**:
   - Visit `https://api.smileartistsdentalstudio.com/docs` (if FastAPI docs are enabled) or `https://api.smileartistsdentalstudio.com/health`.
   - Ensure it loads (You might need to setup Nginx with Certbot on EC2 for HTTPS. *See Note Below*).
3. **Verify Frontend**:
   - Visit `https://smileartistsdentalstudio.com`.
   - Try logging in.
   - Try booking an appointment.

### 🔒 Critical Note on SSL (HTTPS) for AWS Backend
Vercel (Frontend) runs on **HTTPS**. It **cannot** talk to an insecure HTTP backend (`http://54.123...`).
You **MUST** enable HTTPS on your EC2 backend.

**Quick HTTPS Setup on EC2:**
1. SSH into EC2.
2. Install Nginx & Certbot:
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx
   ```
3. Configure Nginx Proxy (`/etc/nginx/sites-available/default`):
   ```nginx
   server {
       server_name api.smileartistsdentalstudio.com;
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```
4. Get Free SSL Certificate:
   ```bash
   sudo certbot --nginx -d api.smileartistsdentalstudio.com
   ```

**🎉 Done! Your Hybrid Vercel + AWS architecture is live!**
