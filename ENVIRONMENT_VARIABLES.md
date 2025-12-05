# Environment Variables Configuration

This document describes all required environment variables for the application.

## Backend Environment Variables

Create a `.env` file in the `backend_code` directory with the following variables:

### Required Variables

```bash
# MongoDB Connection
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority

# Database Name
DATABASE_NAME=email_tracking

# Flask Configuration
SECRET_KEY=your-secret-key-here
PORT=5000

# Microsoft Azure AD / Office 365 OAuth
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret
TENANT_ID=your-tenant-id
REDIRECT_URI=http://localhost:5000/api/callback

# Application URLs (REQUIRED - no hardcoded fallbacks)
BASE_URL=http://localhost:5000
FRONTEND_URL=http://localhost:3000

# Email Rate Limiting
MIN_DELAY_BETWEEN_EMAILS=60
MAX_DELAY_BETWEEN_EMAILS=100
```

### Important Notes

- **BASE_URL**: The backend server URL (used for tracking URLs and API endpoints)
- **FRONTEND_URL**: The frontend application URL (used for CORS configuration and OAuth redirects)
- Both URLs are **required** and will not use hardcoded fallbacks

## Frontend Environment Variables

Create a `.env.local` file in the root directory with the following variables:

### Required Variables

```bash
# Backend API URL (REQUIRED - no hardcoded fallbacks)
NEXT_PUBLIC_API_URL=http://localhost:5000

# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your-clerk-publishable-key
CLERK_SECRET_KEY=your-clerk-secret-key
```

### Important Notes

- **NEXT_PUBLIC_API_URL**: The backend API URL (required)
- All `NEXT_PUBLIC_*` variables are exposed to the browser
- The application will show errors if required environment variables are not set

## Production Configuration

For production, update the URLs to your production domains:

```bash
# Backend .env
BASE_URL=https://api.yourdomain.com
FRONTEND_URL=https://yourdomain.com

# Frontend .env.local
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

## Testing

The `test_api.py` script will use the `API_URL` or `BASE_URL` environment variable if set, otherwise it will default to `http://localhost:5000` for convenience during testing.

