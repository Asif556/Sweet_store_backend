# Sweet Store Backend

Flask backend API for Sweet Store application with MongoDB integration.

## Features

- Sweet inventory management
- Order processing with delivery dates
- Admin dashboard with daily summaries
- MongoDB Atlas integration
- CORS enabled for frontend integration

## Local Development

1. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```
MONGO_URI=your_mongodb_connection_string
```

4. Run the application:
```bash
python app.py
```

## Deploy to Render (Free Tier)

### Step 1: Prepare Your Repository

All required files are already created:
- ✅ `gunicorn_config.py` - Production server configuration
- ✅ `requirements.txt` - Updated with gunicorn
- ✅ `render.yaml` - Render deployment configuration
- ✅ `runtime.txt` - Python version specification
- ✅ `.gitignore` - Excludes unnecessary files

### Step 2: Push to GitHub

```bash
git add .
git commit -m "Add Render deployment configuration"
git push origin main
```

### Step 3: Deploy on Render

1. **Go to Render Dashboard**
   - Visit: https://dashboard.render.com/
   - Sign up/Login (you can use GitHub)

2. **Create New Web Service**
   - Click "New +" button → Select "Web Service"
   - Connect your GitHub repository: `Asif556/Sweet_store_backend`
   - Click "Connect"

3. **Configure Your Service**
   - **Name**: `sweet-store-backend` (or your preferred name)
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --config gunicorn_config.py app:app`
   - **Instance Type**: `Free`

4. **Add Environment Variables**
   - Click "Advanced" or scroll to "Environment Variables"
   - Add your MongoDB URI:
     - **Key**: `MONGO_URI`
     - **Value**: Your MongoDB Atlas connection string
       ```
       mongodb+srv://username:password@cluster.mongodb.net/sweet_store?retryWrites=true&w=majority
       ```
   - (Optional) Add:
     - **Key**: `PYTHON_VERSION`
     - **Value**: `3.11.0`

5. **Deploy**
   - Click "Create Web Service"
   - Wait 5-10 minutes for the first deployment
   - Render will build and deploy your application

### Step 4: Get Your Backend URL

Once deployed, you'll get a URL like:
```
https://sweet-store-backend.onrender.com
```

### Step 5: Update Frontend

Update your frontend to use the new Render URL:
```javascript
const API_URL = 'https://sweet-store-backend.onrender.com';
```

### Step 6: Test Your API

Test these endpoints:
- `GET /sweets` - Get all sweets
- `GET /admin/orders` - Get all orders
- `POST /place_order` - Place new order

## Important Notes for Render Free Tier

⚠️ **Free Tier Limitations:**

1. **Service Spins Down**: After 15 minutes of inactivity, your service will sleep
   - First request after sleep takes 30-60 seconds (cold start)
   - Solution: Use a service like [Cron-Job.org](https://cron-job.org/) to ping your API every 10 minutes

2. **750 Free Hours/Month**: Enough if you have only one service
   - If multiple services, consider upgrading or managing usage

3. **No Custom Domains**: Free tier provides `*.onrender.com` subdomain
   - Custom domains require paid plan

4. **Build Time**: Up to 10 minutes for first deployment

### Keep Your Service Awake (Optional)

Create a free cron job to ping your API:
- URL: `https://your-app.onrender.com/sweets`
- Frequency: Every 10 minutes
- Services: [Cron-Job.org](https://cron-job.org/), [UptimeRobot](https://uptimerobot.com/)

## Troubleshooting

### Deployment Failed
- Check Render logs in the dashboard
- Verify `MONGO_URI` is set correctly
- Ensure all files are pushed to GitHub

### Database Connection Issues
- Verify MongoDB Atlas allows connections from anywhere (0.0.0.0/0)
- Check your MongoDB credentials
- Ensure database user has read/write permissions

### CORS Errors
- Frontend must use the exact Render URL
- Check CORS is enabled in `app.py`

## API Endpoints

### Public Endpoints
- `GET /sweets?category={category}` - Get sweets (optional category filter)
- `POST /place_order` - Place new order

### Admin Endpoints
- `POST /admin/add_sweet` - Add new sweet
- `DELETE /admin/remove_sweet?name={name}` - Remove sweet
- `GET /admin/orders` - Get all orders
- `GET /admin/daily_summary` - Get daily sales summary
- `PUT /admin/update_order_status` - Update order status
- `PUT /admin/edit_order/<order_id>` - Edit order details

## MongoDB Setup

Your MongoDB Atlas cluster should:
1. Have a database named `sweet_store`
2. Contain collections: `sweets` and `orders`
3. Allow network access from 0.0.0.0/0 (for Render)

## Tech Stack

- **Framework**: Flask 3.0.0
- **Database**: MongoDB Atlas
- **Server**: Gunicorn (production)
- **Deployment**: Render
- **Python**: 3.11.0

## License

MIT
