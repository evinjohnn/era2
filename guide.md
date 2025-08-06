# Enhanced Retail AI Assistant - Setup & Usage Guide

## 🚀 Overview

This guide will help you set up and run the Enhanced Retail AI Assistant with PostgreSQL database, advanced conversation engine, analytics, and staff dashboard.

## 📋 Prerequisites

### System Requirements
- Python 3.11+
- PostgreSQL 15+
- Redis Server
- At least 4GB RAM
- 10GB free disk space

### Required API Keys
- **Groq API Key**: Required for LLM functionality
  - Get your key from: https://console.groq.com/keys
  - Model used: `llama3-70b-8192`

## 🛠️ Installation & Setup

### 1. Environment Setup

```bash
# Navigate to the app directory
cd /app

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Database Setup

#### PostgreSQL Installation & Configuration
```bash
# Install PostgreSQL
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib

# Start PostgreSQL service
sudo service postgresql start

# Create database and user
sudo -u postgres createdb retail_ai_db
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE retail_ai_db TO postgres;"
```

#### Redis Installation
```bash
# Install Redis
sudo apt-get install -y redis-server

# Start Redis service
sudo service redis-server start
```

### 3. Environment Configuration

Create or update the `.env` file:

```bash
# Create .env file with your configuration
cat > /app/.env << 'EOF'
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here
SELECTED_GROQ_MODEL=llama3-70b-8192

# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/retail_ai_db
POSTGRES_DB=retail_ai_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Application Configuration
APP_ENV=development
LOG_LEVEL=INFO
SESSION_TTL=3600
CONVERSATION_HISTORY_LIMIT=50
EOF
```

**⚠️ Important**: Replace `your_groq_api_key_here` with your actual Groq API key.

### 4. Database Initialization

```bash
# Initialize database and migrate data
cd /app
python database.py
```

Expected output:
```
Testing database connection...
✅ Database connection successful
✅ Database initialization successful
```

### 5. Test System Components

#### Test Database Connection
```bash
python database.py
```

#### Test Redis Connection
```bash
python cache.py
```

#### Test Enhanced Components
```bash
python conversation_engine.py
python analytics.py
python staff_dashboard.py
```

## 🚀 Running the System

### Method 1: Using Supervisor (Recommended)

#### Update Supervisor Configuration
Ensure `/etc/supervisor/conf.d/supervisord.conf` contains:

```ini
[program:backend]
command=/root/.venv/bin/uvicorn main_enhanced:app --host 0.0.0.0 --port 8001 --workers 1 --reload
directory=/app
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/backend.err.log
stdout_logfile=/var/log/supervisor/backend.out.log
stopsignal=TERM
stopwaitsecs=30
stopasgroup=true
killasgroup=true

[program:mongodb]
command=/usr/bin/mongod --bind_ip_all
autostart=true
autorestart=true
stderr_logfile=/var/log/mongodb.err.log
stdout_logfile=/var/log/mongodb.out.log
```

#### Start Services
```bash
# Reload supervisor configuration
sudo supervisorctl reread
sudo supervisorctl update

# Start all services
sudo supervisorctl restart all

# Check status
sudo supervisorctl status
```

Expected output:
```
backend                          RUNNING   pid 1234, uptime 0:00:10
code-server                      RUNNING   pid 1235, uptime 0:00:10
mongodb                          RUNNING   pid 1236, uptime 0:00:10
```

### Method 2: Manual Startup

```bash
# Ensure databases are running
sudo service postgresql start
sudo service redis-server start

# Start the enhanced application
cd /app
uvicorn main_enhanced:app --host 0.0.0.0 --port 8001 --reload
```

## 🌐 Accessing the System

### Main Application
- **URL**: http://localhost:8001/
- **Description**: Main conversational AI interface
- **Features**: Enhanced conversation with memory, product recommendations

### Staff Dashboard
- **URL**: http://localhost:8001/staff/dashboard
- **Description**: Real-time analytics and session management
- **Features**: 
  - Live conversation metrics
  - Active session monitoring
  - System health status
  - Analytics and reporting

### API Endpoints

#### Core Chat API
```bash
# Start a conversation
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "hi_ai_assistant"}'

# Continue conversation
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your-session-id", "message": "I want an engagement ring"}'
```

#### Analytics APIs
```bash
# Enhanced system stats
curl -X GET http://localhost:8001/admin/enhanced-stats

# Conversation metrics
curl -X GET http://localhost:8001/admin/conversation-metrics?period=last_day

# Staff dashboard metrics
curl -X GET http://localhost:8001/staff/api/metrics

# System health
curl -X GET http://localhost:8001/staff/api/health
```

#### Vector Search API
```bash
# Test vector search
curl -X GET http://localhost:8001/admin/test-vector-search?query=elegant%20engagement%20ring
```

## 🧪 Testing the System

### Comprehensive Test Suite
```bash
# Run the enhanced test suite
cd /app
python enhanced_test.py
```

Expected output:
```
🚀 Starting Enhanced Retail AI Assistant Tests...
============================================================
Enhanced Retail AI Assistant Test Suite
Testing Enhanced System at: http://localhost:8001
============================================================

✅ Enhanced PostgreSQL System: Working
✅ Enhanced Conversation Engine: Working
✅ Staff Dashboard: Working

Tests Run: 9
Tests Passed: 9
Success Rate: 100.0%
```

### Manual Testing Scenarios

#### 1. Basic Conversation Flow
```bash
# Test conversation memory
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "hi_ai_assistant"}'

# Note the session_id from response, then continue
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "SESSION_ID_HERE", "message": "I want a diamond ring for my fiancee, budget 2000"}'
```

#### 2. Product Recommendations
```bash
# Request specific products
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "SESSION_ID_HERE", "message": "show me gold engagement rings"}'
```

#### 3. Staff Dashboard
```bash
# Check active sessions
curl -X GET http://localhost:8001/staff/api/recent

# Get session details
curl -X GET http://localhost:8001/staff/api/session/SESSION_ID_HERE
```

## 📊 System Features

### Enhanced Conversation Engine
- **Persistent Memory**: Conversations remembered across sessions
- **Context Awareness**: Understanding of previous interactions
- **Preference Tracking**: User preferences saved and applied
- **State Management**: Advanced conversation flow control

### PostgreSQL Database
- **Product Catalog**: 220 jewelry products with full metadata
- **Conversation History**: Complete conversation logs
- **Session Management**: Persistent user sessions
- **Analytics Data**: Comprehensive interaction tracking

### Staff Dashboard Features
- **Real-time Metrics**: Live conversation and product analytics
- **Session Monitoring**: Active session tracking and management
- **Health Monitoring**: System status and performance metrics
- **Analytics Reports**: Time-based performance analysis

### Vector Search & RAG
- **Semantic Search**: AI-powered product matching
- **RAG Enhancement**: Context-aware recommendations
- **Similarity Scoring**: Confidence-based product suggestions
- **Performance**: <200ms response time target

## 🔧 Configuration Options

### Environment Variables
```bash
# LLM Configuration
GROQ_API_KEY=your_api_key
SELECTED_GROQ_MODEL=llama3-70b-8192  # or other supported models

# Database URLs
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://localhost:6379

# Application Settings
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
SESSION_TTL=3600  # Session timeout in seconds
CONVERSATION_HISTORY_LIMIT=50  # Max messages per session
```

### Performance Tuning
```bash
# Database connection pool
export DB_POOL_SIZE=20
export DB_MAX_OVERFLOW=0

# Redis settings
export REDIS_MAX_CONNECTIONS=20

# Vector database
export VECTOR_DB_CACHE_SIZE=1000
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Backend Won't Start
```bash
# Check logs
tail -f /var/log/supervisor/backend.err.log

# Common causes:
# - Missing API key
# - Database connection failed
# - Port already in use
```

#### 2. Database Connection Issues
```bash
# Check PostgreSQL status
sudo service postgresql status

# Test connection manually
psql -h localhost -U postgres -d retail_ai_db

# Reset database if needed
sudo -u postgres dropdb retail_ai_db
sudo -u postgres createdb retail_ai_db
python database.py
```

#### 3. Redis Connection Problems
```bash
# Check Redis status
redis-cli ping

# Should return: PONG

# Restart Redis if needed
sudo service redis-server restart
```

#### 4. Vector Database Issues
```bash
# Clear vector database cache
rm -rf /app/chroma_db

# Restart backend to reinitialize
sudo supervisorctl restart backend
```

### Service Management Commands

```bash
# Check all service status
sudo supervisorctl status

# Restart specific service
sudo supervisorctl restart backend

# View service logs
sudo supervisorctl tail backend stderr

# Stop all services
sudo supervisorctl stop all

# Start all services
sudo supervisorctl start all
```

### Performance Monitoring

```bash
# Check system resources
htop

# Monitor database connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis memory usage
redis-cli info memory

# Monitor application logs
tail -f /var/log/supervisor/backend.out.log
```

## 📚 API Documentation

### Chat API Response Format
```json
{
  "session_id": "uuid-string",
  "reply": "AI response text",
  "products": [
    {
      "id": "product-id",
      "name": "Product Name",
      "category": "ring",
      "price": 1299.99,
      "metal": "gold",
      "gemstones": ["diamond"],
      "similarity_score": 0.85
    }
  ],
  "current_state": "ready_for_recommendation",
  "next_action_suggestion": "recommend_products",
  "action_buttons": [
    {"label": "Show more options", "value": "show me more"}
  ],
  "end_conversation": false,
  "confidence_score": "high",
  "metadata": {
    "enhanced_mode": true,
    "database_enabled": true,
    "conversation_tracking": true
  }
}
```

### Analytics API Response Format
```json
{
  "conversation_performance": {
    "total_sessions": 150,
    "active_sessions": 12,
    "average_session_duration": 180.5,
    "messages_per_session": 8.3,
    "handoff_rate": 0.05
  },
  "recommendation_performance": {
    "total_recommendations": 450,
    "unique_products": 89,
    "confidence_levels": {
      "high": 320,
      "medium": 100,
      "low": 30
    }
  }
}
```

## 🔒 Security Considerations

### Environment Security
- Store API keys in `.env` file, not in code
- Use strong database passwords
- Restrict database access to localhost
- Regular security updates

### Production Deployment
- Use HTTPS in production
- Set up firewall rules
- Use connection pooling
- Enable database SSL
- Implement rate limiting

## 📈 Monitoring & Maintenance

### Daily Checks
- Monitor system health via staff dashboard
- Check application logs for errors
- Verify database connectivity
- Review conversation analytics

### Weekly Maintenance
- Database performance analysis
- Clear old conversation logs if needed
- Update vector database if new products added
- Review and optimize slow queries

### Monthly Tasks
- System performance review
- Database backup verification
- Security updates
- Analytics report generation

## 🆘 Support

### Log Locations
- Backend logs: `/var/log/supervisor/backend.*.log`
- PostgreSQL logs: `/var/log/postgresql/`
- Redis logs: `/var/log/redis/`
- System logs: `/var/log/syslog`

### Useful Commands
```bash
# System status
sudo supervisorctl status

# Database status
sudo service postgresql status
sudo service redis-server status

# Test API endpoints
curl -X GET http://localhost:8001/admin/enhanced-stats

# View recent conversations
curl -X GET http://localhost:8001/staff/api/recent
```

### Emergency Recovery
```bash
# Full system restart
sudo supervisorctl stop all
sudo service postgresql restart
sudo service redis-server restart
sudo supervisorctl start all

# Database recovery
python database.py

# Clear caches
rm -rf /app/chroma_db
redis-cli FLUSHALL
```

---

## 🎉 Success Verification

If everything is working correctly, you should see:

1. **Main app at http://localhost:8001/**: Conversational interface loads
2. **Staff dashboard at http://localhost:8001/staff/dashboard**: Analytics dashboard loads
3. **API test returns**: `{"system_status": "enhanced_with_postgresql"}`
4. **Test suite passes**: All tests show ✅ status

The Enhanced Retail AI Assistant is now ready for use with full PostgreSQL backend, advanced conversation management, and comprehensive analytics!