# Deploy ML Service to Both Railway and Render

## Current Setup

**Railway**: ✅ Configured (railway.json pushed)
- Will deploy ML service using Dockerfile.ml
- URL: https://api-for-anomaly-production.up.railway.app

**Render**: ⏳ Needs configuration
- Currently not configured or deploying wrong service

## Configure Render.com for ML Service

### Step 1: Create New Web Service on Render

1. Go to https://render.com/dashboard
2. Click "New +" → "Web Service"
3. Connect your GitHub repository

### Step 2: Configure Service Settings

**Basic Settings:**
- **Name**: `anomaly-ml-service`
- **Region**: Choose closest to you
- **Branch**: `main`
- **Root Directory**: Leave blank

**Build & Deploy:**
- **Environment**: `Docker`
- **Dockerfile Path**: `Dockerfile.ml`
- **Docker Context**: `.` (root directory)

**OR if using Python (not Docker):**
- **Build Command**: `pip install -r requirements-ml.txt` 
- **Start Command**: `uvicorn ml_service.ml_service:app --host 0.0.0.0 --port $PORT`

**Plan:**
- Select "Free" tier

### Step 3: Deploy

Click "Create Web Service" and wait ~5-10 minutes for deployment.

### Step 4: Get Service URL

After deployment completes, copy the URL (e.g., `https://anomaly-ml-service.onrender.com`)

## Test Both ML Services

After both are deployed:

### Test Railway ML Service
```bash
curl https://api-for-anomaly-production.up.railway.app/health
curl https://api-for-anomaly-production.up.railway.app/api/ml/debug
```

### Test Render ML Service
```bash
curl https://anomaly-ml-service.onrender.com/health
curl https://anomaly-ml-service.onrender.com/api/ml/debug
```

Both should return:
```json
{
  "status": "healthy",
  "service": "ml-prediction",
  "models_fitted": false
}
```

## Choose Primary ML Service

Update your web service (https://project-anomaly.sudhir-singh.com/) environment variable:

**Option A: Use Railway (Recommended - Always Active)**
```
ML_SERVICE_URL=https://api-for-anomaly-production.up.railway.app
```

**Option B: Use Render (Free tier but has cold starts)**
```
ML_SERVICE_URL=https://anomaly-ml-service.onrender.com
```

**Option C: Failover Configuration (Advanced)**
Configure your web service to try Railway first, fall back to Render if unavailable.

## Comparison

| Feature | Railway | Render |
|---------|---------|--------|
| Free tier | 500 hrs/month | Yes (cold starts) |
| Cold starts | No | Yes (15 min inactivity) |
| Build speed | Faster | Slower |
| Reliability | Better | Good |
| **Recommendation** | **Primary** | Backup |

## Current Status

✅ **Railway**: Configured via railway.json (redeploying now)  
⏳ **Render**: Follow steps above to configure

After both are deployed, choose Railway as primary ML service URL.
