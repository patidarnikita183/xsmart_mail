# Environment Variables for Vercel

## Backend Environment Variables
```
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/
DATABASE_NAME=your_database_name
CLIENT_ID=your_microsoft_client_id
CLIENT_SECRET=your_microsoft_client_secret
TENANT_ID=your_microsoft_tenant_id
SECRET_KEY=your_flask_secret_key_here
BASE_URL=https://your-app.vercel.app
FRONTEND_URL=https://your-app.vercel.app
```

## Frontend Environment Variables
```
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
CLERK_SECRET_KEY=sk_test_xxxxx
```

## Important Notes:

1. **NEXT_PUBLIC_API_URL** should be **EMPTY** (leave blank or set to empty string)
   - Frontend and backend are on the same domain
   - API calls use relative paths like `/api/email-accounts`

2. **BASE_URL and FRONTEND_URL** should be your Vercel deployment URL
   - Example: `https://your-app.vercel.app`
   - Update after first deployment

3. **All variables are case-sensitive**

4. **Redeploy after adding/changing variables**
   - Environment variables are only loaded during build
   - Changes require a new deployment

## How to Add in Vercel Dashboard:

1. Go to your project in Vercel
2. Click "Settings" tab
3. Click "Environment Variables" in sidebar
4. Add each variable:
   - Key: Variable name (e.g., `MONGO_URL`)
   - Value: Variable value
   - Environment: Select "Production", "Preview", and "Development"
5. Click "Save"
6. Redeploy your project
