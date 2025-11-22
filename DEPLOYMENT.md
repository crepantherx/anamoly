# Anomaly Detection - Microservice Deployment Guide

## Architecture

This application is split into two microservices:

1. **Web Service** (Vercel) - Lightweight FastAPI app with UI templates
   - Uses `requirements-web.txt` (~50 MB)
   - Handles all HTTP requests, WebSocket connections, and UI rendering
   - Makes API calls to ML Service for predictions

2. **ML Service** (Railway/Render/AWS) - Full ML prediction service
   - Uses `requirements-ml.txt` (~400 MB with scikit-learn, scipy, shap)
   - Handles all machine learning operations
   - Exposes REST API for predictions, retraining, and drift calculation

## Local Development

### Option 1: Run Both Services Locally

#### Terminal 1: Start ML Service
```bash
# Install ML dependencies
pip install -r requirements-ml.txt

# Start ML service on port 8001
cd ml_service
python ml_service.py
# OR: uvicorn ml_service.ml_service:app --port 8001 --reload
```

#### Terminal 2: Start Web Service
```bash
# Install web dependencies
pip install -r requirements-web.txt

# Set ML service URL
export ML_SERVICE_URL=http://localhost:8001

# Start web service
uvicorn app.main:app --port 8000 --reload
```

Visit `http://localhost:8000` to access the dashboard.

### Option 2: Docker Compose (Coming Soon)

```bash
docker-compose up
```

## Production Deployment

### Step 1: Deploy ML Service

#### Option A: Railway.app (Recommended)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Create new project
railway init

# Deploy ML service
railway up

# Get ML service URL
railway status
```

Set environment variables in Railway dashboard:
- No special env vars needed for ML service

#### Option B: Render.com

**Step 1: Deploy ML Service**

1. Push code to GitHub
2. Go to [Render.com](https://render.com) and create new "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `anomaly-ml-service`
   - **Root Directory**: Leave empty (use repo root)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements-ml.txt`
   - **Start Command**: `uvicorn ml_service.ml_service:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free tier
5. Click "Create Web Service"
6. Wait for deployment to complete
7. Copy the service URL (e.g., `https://anomaly-ml-service.onrender.com`)

**Step 2: Deploy Web Service (if not using Vercel)**

1. Create another "Web Service" on Render
2. Configure:
   - **Name**: `anomaly-web-service`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements-web.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Set environment variables:
   - `ML_SERVICE_URL`: Your ML service URL from Step 1
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase API key
4. Deploy

> **Note**: Render's free tier has cold starts (services sleep after 15 min of inactivity). First request may be slow.

**If deployment times out:**

1. **Use Docker instead** (recommended):
   - In Render dashboard, set "Docker" as environment
   - Use `Dockerfile.ml` 
   - Render will build from Dockerfile (faster + more reliable)

2. **Split the build**:
   - Build timeout? Contact Render support to increase build time
   - Or use Railway instead (more generous timeouts)

#### Option C: Docker on Any Platform

```bash
# Build ML service image
docker build -f Dockerfile.ml -t anomaly-ml-service .

# Run locally
docker run -p 8001:8001 anomaly-ml-service

# Deploy to your preferred container platform
# (AWS ECS, Google Cloud Run, Azure Container Instances, etc.)
```

### Step 2: Deploy Web Service to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Set environment variable for ML service
# Replace with your ML service URL from Step 1
vercel env add ML_SERVICE_URL

# Enter the ML service URL (e.g., https://your-ml-service.railway.app)

# Deploy to production
vercel --prod
```

Or deploy via Vercel Dashboard:
1. Import your GitHub repository
2. Set environment variable `ML_SERVICE_URL` to your ML service URL
3. Deploy

## Environment Variables

### Web Service (Vercel)
- `ML_SERVICE_URL` - URL of the ML service (required)
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase API key

### ML Service
- No environment variables required (stateless prediction service)

## Testing the Deployment

### Test ML Service Health

```bash
curl https://your-ml-service-url.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "ml-prediction",
  "models_fitted": false
}
```

### Test ML Prediction Endpoint

```bash
curl -X POST https://your-ml-service-url.railway.app/api/ml/predict \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000,
    "user_avg": 100,
    "location": "NY",
    "timestamp": "2024-01-01T12:00:00"
  }'
```

### Test Web Service

Visit your Vercel URL and:
1. Check that the dashboard loads
2. Start emulation
3. Verify transactions appear
4. Check anomaly detection works
5. Test metrics page

## Troubleshooting

### Deployment Timeout on Render

**Error**: Build or startup timeout when installing ML dependencies

**Solutions**:

1. **Use Docker** (Recommended - Faster & More Reliable):
   ```bash
   # In Render dashboard:
   # - Environment: Docker
   # - Dockerfile Path: Dockerfile.ml
   ```

2. **Use Railway instead**:
   ```bash
   railway up
   ```
   Railway has more generous build timeouts and better handles ML dependencies.

3. **Lazy Model Initialization** (Already implemented):
   - Models now fit on first prediction request, not during startup
   - This speeds up deployment significantly

4. **Check Build Logs**:
   - Look for which package takes longest to install
   - Often: `scikit-learn`, `scipy`, `numpy`
   - These are necessary for ML functionality

### Railway Deployment (Alternative to Render)

If Render keeps timing out:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy ML service
railway up

# Get service URL
railway status
```

Railway is more ML-friendly and handles heavy dependencies better.

**Error**: `RuntimeError: Directory 'app/static' does not exist`

**Solution**: The code now handles this automatically. Make sure you've:
1. Committed the `app/static/` directory to git
2. Pushed latest changes: `git add . && git commit -m "Add static directory" && git push`
3. Redeployed on Render

The app will now start even if the static directory is missing (with a warning).

### ML Service Connection Issues

If the web service can't connect to ML service:
1. Check `ML_SERVICE_URL` environment variable is set correctly
2. Verify ML service is running: `curl https://your-ml-service/health`
3. Check CORS is enabled on ML service (already configured)
4. Check ML service logs for errors

### Vercel Deployment Size Issues

If deployment still exceeds 250 MB:
1. Verify you're using `requirements-web.txt` not `requirements-ml.txt`
2. Check `vercel.json` is properly configured
3. Run `pip install -r requirements-web.txt` locally and check size:
   ```bash
   du -sh venv/lib/python*/site-packages
   ```

### Performance Considerations

- ML service calls add ~100-500ms latency per prediction
- Consider caching frequently requested predictions
- For high traffic, scale ML service horizontally
- Monitor ML service response times

## Cost Estimates

- **Vercel**: Free tier (hobby projects) or $20/month (pro)
- **Railway.app**: Free tier (500 hours/month) or $5-20/month
- **Render.com**: Free tier or $7/month for always-on service

Total estimated cost: **$0-40/month** depending on traffic
