# 🚀 Warborne Guild Tools - Django + React Setup Guide

This guide explains how to run both Django and React applications together on Koyeb using a single service deployment.

## 📁 Project Structure

```
Warborne/
├── backend/                    # Django application
│   ├── guilds/                # Main Django app
│   ├── warborne_tools/        # Django project settings
│   ├── manage.py
│   ├── requirements.txt
│   └── start.sh
├── frontend/                   # React application
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── App.js
│   │   └── index.js
│   ├── public/
│   └── package.json
├── nginx/                      # Nginx configuration
│   └── nginx.conf
├── Dockerfile                  # Multi-stage build
├── start-both.sh              # Startup script
├── docker-compose.yml         # Local development
└── koyeb.yaml                 # Koyeb deployment config
```

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│           Koyeb Instance            │
│  ┌─────────────────────────────────┐│
│  │        Nginx (Port 80)          ││
│  │  ┌─────────────┬─────────────┐  ││
│  │  │   React     │   Django    │  ││
│  │  │  (Static)   │  (Port 8000)│  ││
│  │  └─────────────┴─────────────┘  ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

## 🚀 Deployment to Koyeb

### Prerequisites
- Koyeb account (free tier works)
- GitHub repository with your code
- Environment variables configured in Koyeb

### Steps

1. **Push your code to GitHub**
   ```bash
   git add .
   git commit -m "Add Django + React integration"
   git push origin main
   ```

2. **Deploy on Koyeb**
   - Go to your Koyeb dashboard
   - Create a new service
   - Connect your GitHub repository
   - Koyeb will automatically detect the `koyeb.yaml` configuration
   - Deploy!

3. **Environment Variables**
   Make sure these are set in your Koyeb service:
   - `SECRET_KEY`
   - `ALLOWED_HOSTS`
   - Database credentials (already configured)

## 🧪 Local Development

### Option 1: Full Stack (Recommended)
```bash
# Build and run both Django and React
docker-compose up --build
```
Access at: http://localhost

### Option 2: Development Mode
```bash
# Run Django and React separately for development
docker-compose --profile dev up --build
```
- React: http://localhost:3000
- Django: http://localhost:8000

### Option 3: Manual Development
```bash
# Backend (Terminal 1)
cd backend
pip install -r requirements.txt
python manage.py runserver

# Frontend (Terminal 2)
cd frontend
npm install
npm start
```

## 🔧 Configuration Details

### Nginx Routing
- `/` → React app (frontend)
- `/api/` → Django API (backend)
- `/admin/` → Django admin
- `/static/` → Django static files
- `/health/` → Health check endpoint

### Docker Multi-Stage Build
1. **Stage 1**: Build React app with Node.js
2. **Stage 2**: Setup Python environment and copy React build
3. **Final**: Run both Django and Nginx

### Startup Process
1. Wait for database connection
2. Run Django migrations
3. Collect static files
4. Start Django with Gunicorn
5. Start Nginx in foreground

## 📊 API Endpoints

The React app will connect to these Django API endpoints:

- `GET /api/dashboard/stats/` - Dashboard statistics
- `GET /api/players/` - Player list
- `GET /api/loadouts/` - Loadout list
- `GET /api/guilds/` - Guild list

## 🔍 Troubleshooting

### Common Issues

1. **Build fails on Koyeb**
   - Check Dockerfile syntax
   - Verify all files are in correct directories
   - Check environment variables

2. **React app not loading**
   - Verify Nginx configuration
   - Check if React build was successful
   - Ensure port 80 is exposed

3. **Django API not responding**
   - Check Django logs in Koyeb
   - Verify database connection
   - Check Gunicorn configuration

### Logs
```bash
# View logs in Koyeb dashboard
# Or locally:
docker-compose logs -f web
```

## 🎯 Benefits of This Setup

✅ **Single Service** - Both apps deploy together  
✅ **Same Domain** - No CORS issues  
✅ **Automatic Startup** - Both start with one command  
✅ **Free Tier Compatible** - No additional costs  
✅ **Production Ready** - Nginx handles routing efficiently  
✅ **Easy Development** - Docker Compose for local testing  

## 🔄 Next Steps

1. **Add API endpoints** in Django for React to consume
2. **Implement authentication** between React and Django
3. **Add real-time features** with Django Channels
4. **Optimize performance** with caching and CDN
5. **Add monitoring** and logging

## 📚 Resources

- [Koyeb Documentation](https://www.koyeb.com/docs)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [React Documentation](https://reactjs.org/docs)
- [Nginx Configuration](https://nginx.org/en/docs/)
