# Troubleshooting Guide

## MongoDB Connection Issues

### Error: DNS Resolution Timeout

**Symptoms:**
```
pymongo.errors.ConfigurationError: The resolution lifetime expired after X seconds
```

**Causes:**
1. Network connectivity issues
2. DNS server problems
3. Firewall blocking MongoDB connection
4. Incorrect MongoDB connection string

**Solutions:**

1. **Check MongoDB Connection String**
   - Verify `MONGO_URL` in your `.env` file
   - Ensure the connection string is correct
   - For MongoDB Atlas, check if your IP is whitelisted

2. **Test Network Connectivity**
   ```bash
   # Test if you can reach MongoDB
   ping <your-mongodb-host>
   ```

3. **Check Firewall Settings**
   - Ensure port 27017 (or your MongoDB port) is not blocked
   - For MongoDB Atlas, check Network Access settings

4. **Use Direct Connection (if DNS fails)**
   - If using MongoDB Atlas, try using the direct connection string instead of SRV
   - Example: `mongodb://username:password@host:port/database`

5. **Temporary Workaround**
   - The application will now start even if MongoDB connection fails
   - Database operations will fail gracefully with error messages
   - Fix the connection string and restart the server

### Error: WinError 10038 (Socket Error)

**Symptoms:**
```
OSError: [WinError 10038] An operation was attempted on something that is not a socket
```

**Causes:**
- Windows-specific issue with Flask's auto-reloader
- Socket file descriptor issues on Windows

**Solutions:**

1. **Auto-fixed**: The application now disables the reloader on Windows automatically
2. **Manual Fix**: If issues persist, run with:
   ```bash
   python app.py
   # Or set environment variable
   set FLASK_ENV=development
   python -m flask run --no-reload
   ```

## Database Connection String Format

### MongoDB Atlas (SRV)
```
mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true&w=majority
```

### MongoDB Local/Standard
```
mongodb://username:password@host:port/database?retryWrites=true&w=majority
```

### Environment Variables (.env file)
```env
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true&w=majority
DATABASE_NAME=email_tracking
```

## Common Issues

### 1. Connection String Not Set
**Error**: `MongoDB connection string is not provided`

**Fix**: Add `MONGO_URL` to your `.env` file

### 2. Authentication Failed
**Error**: `Authentication failed`

**Fix**: 
- Check username and password in connection string
- Ensure special characters are URL-encoded (e.g., `@` → `%40`)
- Verify database user has proper permissions

### 3. Network Timeout
**Error**: `Server selection timed out`

**Fix**:
- Check internet connection
- Verify MongoDB server is accessible
- Check firewall rules
- For MongoDB Atlas, verify IP whitelist

## Testing Database Connection

You can test the MongoDB connection using this Python script:

```python
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

try:
    client = MongoClient(
        MONGO_URL,
        serverSelectionTimeoutMS=5000
    )
    client.admin.command('ping')
    print("✓ MongoDB connection successful!")
except Exception as e:
    print(f"✗ MongoDB connection failed: {e}")
```

## Application Behavior with Database Issues

The application is now designed to:
- Start even if MongoDB connection fails
- Show clear warning messages
- Handle database errors gracefully
- Allow frontend to load (though features requiring database will fail)

**Note**: Some features will not work without a database connection:
- User authentication
- Campaign creation
- Email sending
- Data retrieval

Fix the MongoDB connection to restore full functionality.

