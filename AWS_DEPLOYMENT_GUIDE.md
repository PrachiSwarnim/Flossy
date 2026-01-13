# Flossy AWS Deployment Guide
## Complete Guide for Deploying on AWS with Custom Domain

---

## 📋 Table of Contents
1. [AWS Architecture Overview](#aws-architecture-overview)
2. [Prerequisites & Estimated Costs](#prerequisites--estimated-costs)
3. [Step 1: AWS Account Setup](#step-1-aws-account-setup)
4. [Step 2: Domain Setup (Route 53)](#step-2-domain-setup-route-53)
5. [Step 3: Database Setup (RDS PostgreSQL)](#step-3-database-setup-rds-postgresql)
6. [Step 4: Backend Deployment (EC2 or Elastic Beanstalk)](#step-4-backend-deployment)
7. [Step 5: Frontend Deployment (S3 + CloudFront)](#step-5-frontend-deployment-s3--cloudfront)
8. [Step 6: SSL Certificate (ACM)](#step-6-ssl-certificate-acm)
9. [Step 7: GitHub Actions CI/CD](#step-7-github-actions-cicd)
10. [Step 8: Final Configuration](#step-8-final-configuration)
11. [Monitoring & Maintenance](#monitoring--maintenance)
12. [Cost Optimization](#cost-optimization)

---

## 🏗️ AWS Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS CLOUD                                       │
│                                                                              │
│  ┌─────────────────┐     ┌─────────────────────────────────────────────┐    │
│  │   Route 53      │     │              CloudFront CDN                  │    │
│  │  (DNS + Domain) │────►│   (Global Edge Locations + SSL)              │    │
│  │                 │     │                                              │    │
│  │ smileartists.com│     │  ┌────────────┐    ┌────────────────────┐   │    │
│  └─────────────────┘     │  │ S3 Bucket  │    │  EC2 / Elastic     │   │    │
│                          │  │ (Frontend) │    │  Beanstalk (API)   │   │    │
│                          │  │            │    │                    │   │    │
│                          │  │ React App  │    │  FastAPI Backend   │   │    │
│                          │  └────────────┘    └─────────┬──────────┘   │    │
│                          └──────────────────────────────┼──────────────┘    │
│                                                         │                    │
│                                                         ▼                    │
│                                            ┌────────────────────────┐        │
│                                            │   RDS PostgreSQL       │        │
│                                            │   (Database)           │        │
│                                            └────────────────────────┘        │
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐      │
│  │   ACM           │    │   IAM           │    │   CloudWatch        │      │
│  │ (SSL Certs)     │    │ (Permissions)   │    │ (Monitoring/Logs)   │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 💰 Prerequisites & Estimated Costs

### Required
- [ ] AWS Account with billing enabled
- [ ] Domain name (purchase via Route 53 or external registrar)
- [ ] Credit/Debit card for AWS billing
- [ ] Git and AWS CLI installed

### Estimated Monthly Costs (USD)

| Service | Configuration | Est. Cost/Month |
|---------|--------------|-----------------|
| Route 53 | Domain + Hosted Zone | $0.50 + $12/year |
| EC2 | t3.small (2GB RAM) | $15-20 |
| RDS PostgreSQL | db.t3.micro (Free Tier) | $0-15 |
| S3 | Frontend hosting | $1-3 |
| CloudFront | CDN + SSL | $1-5 |
| ACM | SSL Certificate | FREE |
| **Total** | | **~$20-45/month** |

### Free Tier (First 12 months)
- EC2: 750 hours/month t2.micro
- RDS: 750 hours/month db.t3.micro
- S3: 5GB storage
- CloudFront: 1TB data transfer

---

## 📝 Step 1: AWS Account Setup

### 1.1 Create AWS Account
1. Go to https://aws.amazon.com
2. Click "Create an AWS Account"
3. Enter email, password, account name
4. Add payment method
5. Verify phone number
6. Select Support Plan (Basic - Free)

### 1.2 Secure Root Account
```bash
# Enable MFA for root account
# AWS Console → IAM → Security credentials → MFA
```

### 1.3 Create IAM User for Deployment
```bash
# AWS Console → IAM → Users → Create user
# Username: flossy-deployer
# Access: Programmatic access + Console access
```

**Attach these policies:**
- `AmazonEC2FullAccess`
- `AmazonRDSFullAccess`
- `AmazonS3FullAccess`
- `CloudFrontFullAccess`
- `AmazonRoute53FullAccess`
- `AWSCertificateManagerFullAccess`
- `ElasticBeanstalkFullAccess`

### 1.4 Install & Configure AWS CLI
```bash
# Install AWS CLI
# Windows (PowerShell as Admin):
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# macOS:
brew install awscli

# Linux:
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure CLI
aws configure
# Enter: Access Key ID, Secret Access Key, Region (ap-south-1 for Mumbai), Output format (json)
```

---

## 🌐 Step 2: Domain Setup (Route 53)

### Option A: Purchase Domain via Route 53

```bash
# AWS Console → Route 53 → Registered domains → Register domain
# Search for your domain (e.g., smileartists.com)
# Complete purchase (~$12-15/year for .com)
```

### Option B: Use Existing Domain (External Registrar)

1. **Create Hosted Zone in Route 53:**
```bash
aws route53 create-hosted-zone --name smileartists.com --caller-reference $(date +%s)
```

2. **Get Name Servers:**
```bash
aws route53 get-hosted-zone --id <HOSTED_ZONE_ID>
# Note the 4 NS records
```

3. **Update Nameservers at Registrar:**
   - GoDaddy/Namecheap → My Domains → DNS → Custom Nameservers
   - Enter the 4 AWS nameservers

### Save Your Hosted Zone ID
```bash
# You'll need this later
export HOSTED_ZONE_ID="Z1234567890ABC"
```

---

## 🗄️ Step 3: Database Setup (RDS PostgreSQL)

### 3.1 Create RDS Instance

**Via AWS Console:**
1. Go to RDS → Create database
2. Choose "Standard create"
3. Engine: PostgreSQL
4. Version: 15.x
5. Template: Free tier (or Production)
6. Settings:
   - DB Instance identifier: `flossy-db`
   - Master username: `flossy_admin`
   - Master password: `<strong-password>`
7. Instance configuration: `db.t3.micro`
8. Storage: 20 GB (Enable autoscaling)
9. Connectivity:
   - VPC: Default VPC
   - Public access: Yes (for initial setup, disable later)
   - Security group: Create new → `flossy-db-sg`
10. Database name: `flossy_db`

**Via CLI:**
```bash
aws rds create-db-instance \
    --db-instance-identifier flossy-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15 \
    --master-username flossy_admin \
    --master-user-password "<YOUR-STRONG-PASSWORD>" \
    --allocated-storage 20 \
    --db-name flossy_db \
    --publicly-accessible \
    --backup-retention-period 7
```

### 3.2 Configure Security Group

```bash
# Get RDS security group ID
aws rds describe-db-instances --db-instance-identifier flossy-db --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId'

# Allow PostgreSQL access from EC2 (later add EC2 SG)
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxx \
    --protocol tcp \
    --port 5432 \
    --cidr 0.0.0.0/0  # Restrict this to EC2 IP in production
```

### 3.3 Get Database Endpoint

```bash
aws rds describe-db-instances --db-instance-identifier flossy-db --query 'DBInstances[0].Endpoint.Address' --output text

# Example output: flossy-db.xxxxxxxxx.ap-south-1.rds.amazonaws.com
```

### 3.4 Your DATABASE_URL

```
postgresql://flossy_admin:<password>@flossy-db.xxxxxxxxx.ap-south-1.rds.amazonaws.com:5432/flossy_db
```

---

## 🖥️ Step 4: Backend Deployment

### Option A: EC2 (More Control) - Recommended

#### 4.1 Launch EC2 Instance

```bash
# Create key pair
aws ec2 create-key-pair --key-name flossy-key --query 'KeyMaterial' --output text > flossy-key.pem
chmod 400 flossy-key.pem

# Launch instance
aws ec2 run-instances \
    --image-id ami-0f5ee92e2d63afc18 \  # Ubuntu 22.04 in ap-south-1
    --instance-type t3.small \
    --key-name flossy-key \
    --security-group-ids sg-xxxxxxxx \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=flossy-backend}]' \
    --user-data file://ec2-user-data.sh
```

#### 4.2 Create `ec2-user-data.sh`:
```bash
#!/bin/bash
# Update system
apt-get update && apt-get upgrade -y

# Install Python 3.11
apt-get install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.11 python3.11-venv python3.11-dev

# Install pip
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Install Nginx
apt-get install -y nginx

# Install Git
apt-get install -y git

# Create app directory
mkdir -p /opt/flossy
chown ubuntu:ubuntu /opt/flossy
```

#### 4.3 Configure Security Group for EC2

```bash
# Create security group
aws ec2 create-security-group \
    --group-name flossy-ec2-sg \
    --description "Security group for Flossy backend"

# Allow SSH (22), HTTP (80), HTTPS (443), API (8000)
aws ec2 authorize-security-group-ingress --group-name flossy-ec2-sg --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-name flossy-ec2-sg --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-name flossy-ec2-sg --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-name flossy-ec2-sg --protocol tcp --port 8000 --cidr 0.0.0.0/0
```

#### 4.4 SSH into EC2 and Deploy

```bash
# Get public IP
aws ec2 describe-instances --filters "Name=tag:Name,Values=flossy-backend" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text

# SSH into instance
ssh -i flossy-key.pem ubuntu@<EC2-PUBLIC-IP>

# Clone repository
cd /opt/flossy
git clone https://github.com/YOUR_USERNAME/Flossy.git
cd Flossy/flossy_backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
nano .env
```

#### 4.5 Create Backend `.env`:
```env
# Database
DATABASE_URL=postgresql://flossy_admin:<password>@flossy-db.xxxxxxxxx.ap-south-1.rds.amazonaws.com:5432/flossy_db

# App Config
APP_PORT=8000
SECRET_KEY=your-super-secret-key-min-32-characters-long

# Clerk Authentication
CLERK_SECRET_KEY=sk_live_xxxxx
CLERK_PUBLISHABLE_KEY=pk_live_xxxxx
CLERK_JWKS_URL=https://your-clerk.clerk.accounts.dev/.well-known/jwks.json

# AI Services
GOOGLE_API_KEY=AIzaSy-xxxxxx
GEMINI_API_KEY=AIzaSy-xxxxxx
GROQ_API_KEY=gsk_xxxxxx

# LiveKit
LIVEKIT_API_KEY=APIxxxxxx
LIVEKIT_API_SECRET=xxxxxx
LIVEKIT_URL=wss://your-app.livekit.cloud

# Clinic Info
CLINIC_NAME=Smile Artists Dental Studio
CLINIC_ADDRESS=Your Address
CLINIC_PHONE=+91 XXXXXXXXXX
CLINIC_EMAIL=contact@smileartists.com
```

#### 4.6 Configure Nginx as Reverse Proxy

```bash
sudo nano /etc/nginx/sites-available/flossy
```

```nginx
server {
    listen 80;
    server_name api.smileartists.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/flossy /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 4.7 Create Systemd Service

```bash
sudo nano /etc/systemd/system/flossy.service
```

```ini
[Unit]
Description=Flossy FastAPI Backend
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/flossy/Flossy/flossy_backend
Environment="PATH=/opt/flossy/Flossy/flossy_backend/venv/bin"
EnvironmentFile=/opt/flossy/Flossy/flossy_backend/.env
ExecStart=/opt/flossy/Flossy/flossy_backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable flossy
sudo systemctl start flossy
sudo systemctl status flossy
```

#### 4.8 Allocate Elastic IP (Static IP)

```bash
# Allocate Elastic IP
aws ec2 allocate-address --domain vpc

# Associate with instance
aws ec2 associate-address --instance-id i-xxxxxxxxx --allocation-id eipalloc-xxxxxxxxx
```

### Option B: Elastic Beanstalk (Easier but less control)

```bash
# Install EB CLI
pip install awsebcli

# Initialize
cd flossy_backend
eb init -p python-3.11 flossy-backend --region ap-south-1

# Create environment
eb create flossy-prod --single --instance-type t3.small

# Set environment variables
eb setenv DATABASE_URL=... CLERK_SECRET_KEY=... GOOGLE_API_KEY=...

# Deploy
eb deploy
```

---

## 🌐 Step 5: Frontend Deployment (S3 + CloudFront)

### 5.1 Build Frontend

```bash
cd flossy-ui

# Create production .env
cat > .env.production << EOF
VITE_API_URL=https://api.smileartists.com
VITE_CLERK_PUBLISHABLE_KEY=pk_live_xxxxx
VITE_LIVEKIT_URL=wss://your-app.livekit.cloud
EOF

# Build
npm run build
```

### 5.2 Create S3 Bucket

```bash
# Create bucket
aws s3 mb s3://smileartists-frontend --region ap-south-1

# Enable static website hosting
aws s3 website s3://smileartists-frontend --index-document index.html --error-document index.html

# Set bucket policy for public access
cat > bucket-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::smileartists-frontend/*"
        }
    ]
}
EOF

aws s3api put-bucket-policy --bucket smileartists-frontend --policy file://bucket-policy.json

# Disable block public access
aws s3api put-public-access-block \
    --bucket smileartists-frontend \
    --public-access-block-configuration "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"
```

### 5.3 Upload Build Files

```bash
# Sync build folder to S3
aws s3 sync dist/ s3://smileartists-frontend --delete

# Set correct content types
aws s3 cp s3://smileartists-frontend s3://smileartists-frontend --recursive --metadata-directive REPLACE --content-type "text/html" --exclude "*" --include "*.html"
aws s3 cp s3://smileartists-frontend s3://smileartists-frontend --recursive --metadata-directive REPLACE --content-type "application/javascript" --exclude "*" --include "*.js"
aws s3 cp s3://smileartists-frontend s3://smileartists-frontend --recursive --metadata-directive REPLACE --content-type "text/css" --exclude "*" --include "*.css"
```

### 5.4 Create CloudFront Distribution

```bash
# Create distribution config
cat > cloudfront-config.json << EOF
{
    "CallerReference": "flossy-$(date +%s)",
    "Origins": {
        "Quantity": 1,
        "Items": [
            {
                "Id": "S3-smileartists-frontend",
                "DomainName": "smileartists-frontend.s3.ap-south-1.amazonaws.com",
                "S3OriginConfig": {
                    "OriginAccessIdentity": ""
                }
            }
        ]
    },
    "DefaultCacheBehavior": {
        "TargetOriginId": "S3-smileartists-frontend",
        "ViewerProtocolPolicy": "redirect-to-https",
        "AllowedMethods": {
            "Quantity": 2,
            "Items": ["HEAD", "GET"]
        },
        "ForwardedValues": {
            "QueryString": false,
            "Cookies": {"Forward": "none"}
        },
        "MinTTL": 0,
        "DefaultTTL": 86400
    },
    "DefaultRootObject": "index.html",
    "CustomErrorResponses": {
        "Quantity": 1,
        "Items": [
            {
                "ErrorCode": 404,
                "ResponsePagePath": "/index.html",
                "ResponseCode": "200",
                "ErrorCachingMinTTL": 300
            }
        ]
    },
    "Enabled": true,
    "Comment": "Flossy Frontend"
}
EOF

# Create distribution
aws cloudfront create-distribution --distribution-config file://cloudfront-config.json
```

**Note CloudFront Distribution ID and Domain (e.g., d1234567890.cloudfront.net)**

---

## 🔒 Step 6: SSL Certificate (ACM)

### 6.1 Request Certificate

```bash
# Request certificate (must be in us-east-1 for CloudFront)
aws acm request-certificate \
    --domain-name smileartists.com \
    --subject-alternative-names "*.smileartists.com" \
    --validation-method DNS \
    --region us-east-1
```

### 6.2 Validate Certificate

1. Go to AWS Console → Certificate Manager (us-east-1)
2. Click on your certificate
3. Click "Create records in Route 53" for DNS validation
4. Wait 5-30 minutes for validation

### 6.3 Update CloudFront with Certificate

```bash
# Update distribution to use ACM certificate and custom domain
# AWS Console → CloudFront → Distribution → Edit
# - Alternate domain names: smileartists.com, www.smileartists.com
# - Custom SSL certificate: Select your ACM certificate
# - Save changes
```

### 6.4 Install SSL on EC2 (for API subdomain)

```bash
# SSH into EC2
ssh -i flossy-key.pem ubuntu@<EC2-IP>

# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d api.smileartists.com

# Auto-renewal (already configured by certbot)
sudo systemctl status certbot.timer
```

---

## 🔄 Step 7: GitHub Actions CI/CD

### 7.1 Create `.github/workflows/aws-deploy.yml`:

```yaml
name: Deploy Flossy to AWS

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  AWS_REGION: ap-south-1

jobs:
  # ========================================
  # DEPLOY FRONTEND TO S3 + CLOUDFRONT
  # ========================================
  deploy-frontend:
    name: Deploy Frontend
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./flossy-ui

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: './flossy-ui/package-lock.json'

      - name: Install dependencies
        run: npm ci

      - name: Build app
        run: npm run build
        env:
          VITE_API_URL: ${{ secrets.VITE_API_URL }}
          VITE_CLERK_PUBLISHABLE_KEY: ${{ secrets.VITE_CLERK_PUBLISHABLE_KEY }}
          VITE_LIVEKIT_URL: ${{ secrets.VITE_LIVEKIT_URL }}

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Deploy to S3
        run: aws s3 sync dist/ s3://${{ secrets.S3_BUCKET_NAME }} --delete

      - name: Invalidate CloudFront cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"

  # ========================================
  # DEPLOY BACKEND TO EC2
  # ========================================
  deploy-backend:
    name: Deploy Backend
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Deploy to EC2 via SSH
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ubuntu
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd /opt/flossy/Flossy
            git pull origin main
            cd flossy_backend
            source venv/bin/activate
            pip install -r requirements.txt
            sudo systemctl restart flossy
            echo "Backend deployed successfully!"

  # ========================================
  # NOTIFY ON COMPLETION
  # ========================================
  notify:
    name: Deployment Complete
    runs-on: ubuntu-latest
    needs: [deploy-frontend, deploy-backend]
    if: always()

    steps:
      - name: Success notification
        if: ${{ needs.deploy-frontend.result == 'success' && needs.deploy-backend.result == 'success' }}
        run: echo "✅ Deployment to AWS completed successfully!"

      - name: Failure notification
        if: ${{ needs.deploy-frontend.result == 'failure' || needs.deploy-backend.result == 'failure' }}
        run: |
          echo "❌ Deployment failed!"
          exit 1
```

### 7.2 Add GitHub Secrets

Go to Repository → Settings → Secrets and variables → Actions → New repository secret

| Secret Name | Value |
|-------------|-------|
| `AWS_ACCESS_KEY_ID` | Your IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | Your IAM user secret key |
| `S3_BUCKET_NAME` | `smileartists-frontend` |
| `CLOUDFRONT_DISTRIBUTION_ID` | `E1234567890` |
| `EC2_HOST` | `13.233.xxx.xxx` (Elastic IP) |
| `EC2_SSH_KEY` | Contents of `flossy-key.pem` |
| `VITE_API_URL` | `https://api.smileartists.com` |
| `VITE_CLERK_PUBLISHABLE_KEY` | `pk_live_xxxxx` |
| `VITE_LIVEKIT_URL` | `wss://your-app.livekit.cloud` |

---

## 🎯 Step 8: Final Configuration

### 8.1 Create Route 53 DNS Records

```bash
# Get Hosted Zone ID
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='smileartists.com.'].Id" --output text | cut -d'/' -f3)

# Create records
cat > dns-records.json << EOF
{
    "Changes": [
        {
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "smileartists.com",
                "Type": "A",
                "AliasTarget": {
                    "HostedZoneId": "Z2FDTNDATAQYW2",
                    "DNSName": "d1234567890.cloudfront.net",
                    "EvaluateTargetHealth": false
                }
            }
        },
        {
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "www.smileartists.com",
                "Type": "CNAME",
                "TTL": 300,
                "ResourceRecords": [{"Value": "smileartists.com"}]
            }
        },
        {
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "api.smileartists.com",
                "Type": "A",
                "TTL": 300,
                "ResourceRecords": [{"Value": "YOUR_ELASTIC_IP"}]
            }
        }
    ]
}
EOF

aws route53 change-resource-record-sets --hosted-zone-id $HOSTED_ZONE_ID --change-batch file://dns-records.json
```

### 8.2 Update Clerk Settings

1. Go to Clerk Dashboard → Domains
2. Add production domain: `smileartists.com`
3. Update JWKS URL in backend `.env`

### 8.3 Update CORS in Backend

In `flossy_backend/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://smileartists.com",
        "https://www.smileartists.com",
        "http://localhost:5173"  # Keep for local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📊 Monitoring & Maintenance

### CloudWatch Alarms

```bash
# CPU Alarm for EC2
aws cloudwatch put-metric-alarm \
    --alarm-name "flossy-ec2-high-cpu" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=InstanceId,Value=i-xxxxxxxxx \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:ap-south-1:123456789:my-alerts
```

### Useful Commands

```bash
# Check EC2 logs
ssh -i flossy-key.pem ubuntu@<EC2-IP>
sudo journalctl -u flossy -f

# Check Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Restart services
sudo systemctl restart flossy
sudo systemctl restart nginx
```

---

## 💡 Cost Optimization

### Recommendations

1. **Use Reserved Instances** - Save up to 72% on EC2
2. **RDS Reserved Instances** - Save on database costs
3. **S3 Intelligent-Tiering** - Automatic cost optimization
4. **CloudFront Caching** - Reduce origin requests
5. **Right-size instances** - Monitor usage and adjust

### Free Tier Maximization

```bash
# Use t2.micro/t3.micro for first 12 months
# Use db.t3.micro for RDS free tier
# Stay within 750 hours/month limit
```

---

## ✅ Deployment Checklist

- [ ] AWS account created and secured
- [ ] Domain registered and configured in Route 53
- [ ] RDS PostgreSQL database created
- [ ] EC2 instance launched and configured
- [ ] Backend deployed and running
- [ ] S3 bucket created for frontend
- [ ] CloudFront distribution created
- [ ] ACM SSL certificates issued
- [ ] DNS records configured
- [ ] GitHub Actions secrets added
- [ ] CI/CD pipeline tested
- [ ] SSL working on all endpoints
- [ ] Application fully tested in production

---

## 🆘 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| 502 Bad Gateway | Check if backend service is running: `sudo systemctl status flossy` |
| Database connection failed | Verify security group allows EC2 → RDS on port 5432 |
| SSL certificate pending | Complete DNS validation in ACM |
| S3 access denied | Check bucket policy and public access settings |
| CloudFront showing old content | Invalidate cache: `aws cloudfront create-invalidation` |

---

*Documentation for: Flossy Dental Clinic Management System*
*AWS Deployment Guide - Last Updated: January 2026*
