# Vercel Deployment Guide

## ✅ Files Created/Updated

### 1. `vercel.json` (Root Directory)
Configuration file that tells Vercel how to build and route your application.

**What it does:**
- Builds your Python backend (`backend_code/app.py`) as a serverless function
- Builds your Next.js frontend (`package.json`)
- Routes all `/api/*` requests to the Python backend
- Routes all other requests to Next.js frontend

### 2. `backend_code/requirements.txt`
Lists all Python dependencies needed for your backend.

**Includes:**
- Flask==3.0.0
- flask-cors==4.0.0
- requests==2.31.0
- pymongo==4.6.1
- python-dotenv==1.0.0
- pandas==2.1.4
- Werkzeug==3.0.1

### 3. `src/api/hooks.ts` (Updated)
All API endpoints now have the `/api` prefix for consistent routing.

## 📋 Pre-Deployment Checklist

### Step 1: Environment Variables
You need to set these in the Vercel Dashboard (Project Settings → Environment Variables):

**Backend Variables:**
- `MONGO_URL` - Your MongoDB connection string
- `DATABASE_NAME` - Your database name
- `CLIENT_ID` - Microsoft OAuth client ID
- `CLIENT_SECRET` - Microsoft OAuth client secret
- `TENANT_ID` - Microsoft tenant ID
- `SECRET_KEY` - Flask secret key
- `BASE_URL` - Your Vercel deployment URL (e.g., `https://your-app.vercel.app`)
- `FRONTEND_URL` - Same as BASE_URL

**Frontend Variables:**
- `NEXT_PUBLIC_API_URL` - Leave **EMPTY** or set to empty string `""`
  - This is important! Frontend and backend are on the same domain
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - Your Clerk publishable key
- `CLERK_SECRET_KEY` - Your Clerk secret key

### Step 2: MongoDB Configuration
Make sure your MongoDB allows connections from Vercel:
1. Go to MongoDB Atlas → Network Access
2. Add IP Address: `0.0.0.0/0` (allow from anywhere)
   - Or add Vercel's specific IP ranges if you prefer

### Step 3: Microsoft OAuth Configuration
Update your Microsoft App Registration:
1. Go to Azure Portal → App Registrations
2. Add redirect URI: `https://your-app.vercel.app/callback`
3. Add redirect URI: `https://your-app.vercel.app/add-account-callback`

## 🚀 Deployment Steps

### Option 1: Deploy via Vercel CLI

1. **Install Vercel CLI** (if not already installed):
   ```bash
   npm i -g vercel
   ```

2. **Login to Vercel**:
   ```bash
   vercel login
   ```

3. **Deploy**:
   ```bash
   vercel
   ```
   - Follow the prompts
   - Select your project or create a new one
   - Vercel will automatically detect the configuration

4. **Deploy to Production**:
   ```bash
   vercel --prod
   ```

### Option 2: Deploy via GitHub

1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Ready for Vercel deployment"
   git push origin main
   ```

2. **Connect to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Click "Add New Project"
   - Import your GitHub repository
   - Vercel will auto-detect the configuration

3. **Add Environment Variables**:
   - In Vercel dashboard, go to Project Settings → Environment Variables
   - Add all the variables listed above

4. **Deploy**:
   - Click "Deploy"
   - Vercel will build and deploy your app

## 🔍 How It Works

### Request Flow:

1. **Frontend Request**: User visits `https://your-app.vercel.app`
   - Served by Next.js

2. **API Request**: Frontend calls `/api/email-accounts`
   - Routed to Python backend (`backend_code/app.py`)
   - Python processes the request
   - Returns JSON response

3. **Static Files**: Images, CSS, JS
   - Served by Next.js/Vercel CDN

### Architecture:
```
┌─────────────────────────────────────────┐
│     https://your-app.vercel.app         │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
   ┌────▼────┐         ┌────▼────┐
   │ Next.js │         │ Python  │
   │Frontend │         │ Backend │
   │  (/)    │         │ (/api/*) │
   └─────────┘         └─────────┘
```

## ⚠️ Important Considerations

### 1. Serverless Limitations
- **Execution Time**: 10 seconds (Hobby) / 60 seconds (Pro)
- **Cold Starts**: First request may be slow
- **No Persistent Connections**: Each request is independent

### 2. Background Tasks
Your background email sending might not work as expected because:
- Serverless functions timeout after 10-60 seconds
- Background threads are killed when function completes

**Solution**: Consider using:
- Vercel Cron Jobs for scheduled tasks
- External service like Celery + Redis
- Queue service like AWS SQS or Google Cloud Tasks

### 3. File Uploads
If you're uploading CSV files:
- Files are stored in `/tmp` (temporary)
- `/tmp` is cleared between invocations
- Consider using cloud storage (S3, Google Cloud Storage)

## 🐛 Troubleshooting

### Issue: API calls return 404
**Solution**: Make sure all API endpoints have `/api` prefix

### Issue: CORS errors
**Solution**: Check that `FRONTEND_URL` environment variable is set correctly

### Issue: Database connection fails
**Solution**: 
1. Check MongoDB allows connections from `0.0.0.0/0`
2. Verify `MONGO_URL` is correct in Vercel environment variables

### Issue: OAuth redirect fails
**Solution**: Update Microsoft App Registration with Vercel URL

### Issue: Environment variables not working
**Solution**: 
1. Make sure they're set in Vercel dashboard
2. Redeploy after adding variables
3. Check variable names match exactly (case-sensitive)

## 📊 Monitoring

After deployment, monitor your app:
1. **Vercel Dashboard**: View logs, analytics, and errors
2. **Function Logs**: Check serverless function execution
3. **MongoDB Atlas**: Monitor database connections and queries

## 🎉 Post-Deployment

1. **Test all features**:
   - User authentication (Clerk)
   - Email account connection (Microsoft OAuth)
   - Campaign creation
   - Email sending
   - Analytics dashboard

2. **Set up custom domain** (optional):
   - Vercel Dashboard → Domains
   - Add your custom domain
   - Update environment variables with new domain

3. **Enable monitoring**:
   - Set up error tracking (Sentry, LogRocket)
   - Monitor performance
   - Set up alerts

## 📝 Notes

- Your app is now a **hybrid application**: Next.js frontend + Python backend
- Both run on the same domain, no CORS issues
- All API calls use relative paths (`/api/*`)
- Vercel handles SSL certificates automatically
- Automatic HTTPS redirect

## 🔗 Useful Links

- [Vercel Documentation](https://vercel.com/docs)
- [Vercel Python Runtime](https://vercel.com/docs/runtimes#official-runtimes/python)
- [Next.js on Vercel](https://vercel.com/docs/frameworks/nextjs)
- [Environment Variables](https://vercel.com/docs/projects/environment-variables)
