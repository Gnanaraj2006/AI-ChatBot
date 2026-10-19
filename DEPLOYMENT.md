# Cloud Deployment Guide: StudySphere AI

This guide walks you through deploying **StudySphere AI** to production cloud infrastructure using **Docker** and **Docker Compose**.

---

## 1. Local Testing with Docker

### Step 1: Clone and Configure Environment
```bash
git clone <your-repository-url>
cd "AI ChatBot"

# Copy and edit environment variables
cp .env.example .env
```
Ensure you have set your `GEMINI_API_KEY` (or `OPENAI_API_KEY`) in `.env`.

### Step 2: Build and Run with Docker Compose
```bash
docker compose up -d --build
```

### Step 3: Verify Container Health
```bash
docker compose ps
curl http://localhost/health
```
Open **`http://localhost`** in your browser. Nginx reverse proxies traffic directly to the FastAPI container with gzip compression and static caching.

To stop the containers:
```bash
docker compose down
```

---

## 2. Google Cloud Deployment

### Option A: Serverless via Google Cloud Run (Recommended - Fastest & Cost Effective)
Google Cloud Run automatically scales containers from 0 to N and handles HTTPS SSL certificates automatically.

```bash
# 1. Authenticate with Google Cloud
gcloud auth login
gcloud config set project <YOUR_GCP_PROJECT_ID>

# 2. Build and Deploy directly to Cloud Run
gcloud run deploy studysphere-ai \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8000 \
    --set-env-vars="DEFAULT_MODEL_PROVIDER=gemini,GEMINI_API_KEY=your_key_here,APP_ENV=production"
```
Cloud Run will return your live HTTPS URL (e.g., `https://studysphere-ai-xyz-uc.a.run.app`).

---

## 3. AWS Deployment

### Option A: AWS EC2 (Docker Compose on Ubuntu)
1. Launch an **EC2 Instance** (`t3.small` or `t3.medium`, Ubuntu 22.04 LTS).
2. Attach a Security Group opening ports **80 (HTTP)**, **443 (HTTPS)**, and **22 (SSH)**.
3. SSH into the instance:
   ```bash
   ssh -i your-key.pem ubuntu@<your-ec2-ip>
   ```
4. Install Docker & Docker Compose:
   ```bash
   sudo apt-get update
   sudo apt-get install -y ca-certificates curl gnupg
   sudo install -m 0755 -d /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
     $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
     sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   ```
5. Clone your repository:
   ```bash
   git clone <your-repo>
   cd "AI ChatBot"
   cp .env.example .env
   nano .env # Paste your API key
   sudo docker compose up -d --build
   ```

### Option B: AWS ECS / Fargate
1. Build and push image to AWS ECR:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com
   docker build -t studysphere-ai .
   docker tag studysphere-ai:latest <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/studysphere-ai:latest
   docker push <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/studysphere-ai:latest
   ```
2. Create an ECS Task Definition mapping container port `8000` to Application Load Balancer.

---

## 4. Microsoft Azure Deployment

### Azure Container Apps
```bash
# 1. Create Resource Group
az group create --name studysphere-rg --location eastus

# 2. Deploy Container App
az containerapp up \
  --name studysphere-ai \
  --resource-group studysphere-rg \
  --location eastus \
  --source . \
  --target-port 8000 \
  --ingress external \
  --env-vars GEMINI_API_KEY="your_key" DEFAULT_MODEL_PROVIDER="gemini"
```

---

## 5. DigitalOcean / Render / Railway

### Render.com
1. Create a New **Web Service** on Render.
2. Connect your GitHub repository.
3. Choose **Docker** as Runtime.
4. Set Environment Variables:
   - `GEMINI_API_KEY` = your API key
   - `PORT` = `8000`
5. Click **Deploy**.

---

## 6. SSL / TLS Setup with Certbot & Let's Encrypt (EC2 / VM)

To attach a custom domain with free automatic SSL:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourstudyapp.com -d www.yourstudyapp.com
```

---

## 7. Container Security & Health Monitoring
- **Non-root user execution**: Docker container runs as `appuser` (UID 1001) for strict least-privilege security.
- **Health Check Endpoint**: `GET /health` monitored by Docker engine every 20s.
- **Reverse Proxy**: Nginx limits upload body size (`35M`), sets `nosniff`, `SAMEORIGIN`, and mitigates slowloris/DoS attacks.
