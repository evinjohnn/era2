# Joxy Retail AI Assistant - Setup Guide

This guide will help you set up and run the integrated Joxy Retail AI Assistant application.

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- Redis (optional, for caching)

## Environment Setup

Create a `.env` file in your project root with the following variables:

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/retail_ai_db

# API Keys (if needed)
GROQ_API_KEY=your_groq_api_key_here

# Application Settings
DEBUG=true
LOG_LEVEL=INFO
```

## Installation Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up PostgreSQL Database

Create a new database:

```sql
CREATE DATABASE retail_ai_db;
```

Update your `.env` file with the correct database credentials.

### 3. Generate Product Data

```bash
python generate_product_data.py
```

This will create a `product_catalog_large.json` file with 500 sample jewelry products.

### 4. Initialize Database

```bash
python database.py
```

This will create the necessary tables and migrate the product data from JSON to PostgreSQL.

### 5. Run the Application

```bash
uvicorn main:app --reload
```

The application will be available at `http://127.0.0.1:8000`

## Application Features

### Main Interface
- **Welcome Screen**: Clean, iPad-inspired design
- **Conversational Flow**: Guided shopping experience with state machine
- **Product Recommendations**: RAG-based + fallback filtering
- **Action Buttons**: Guided user interaction

### Staff Dashboard
- **Analytics**: Conversation metrics and product performance
- **Charts**: Peak hours, category breakdown, price ranges
- **Access**: Available at `/staff/dashboard`

### API Endpoints
- `POST /chat`: Main conversation endpoint
- `POST /new-session`: Start new conversation
- `GET /staff/dashboard`: Staff dashboard page
- `GET /staff/api/dashboard-data`: Dashboard data API

## Architecture

### Backend Components
- **main.py**: Central application hub with conversation state machine
- **database.py**: PostgreSQL models and database management
- **vector_db.py**: ChromaDB vector database for semantic search
- **rag_system.py**: RAG-based recommendation engine
- **staff_dashboard.py**: Staff analytics and monitoring

### Frontend Components
- **static/index.html**: Main user interface
- **static/script.js**: Frontend logic and API communication
- **static/style.css**: iPad-inspired design system
- **static/dashboard.html**: Staff analytics dashboard

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running
- Check database credentials in `.env`
- Verify database exists and is accessible

### Product Recommendations Not Working
- Check if `product_catalog_large.json` exists
- Verify database migration completed successfully
- Check vector database initialization logs

### Frontend Issues
- Ensure all static files are in the `static/` directory
- Check browser console for JavaScript errors
- Verify API endpoints are responding correctly

## Development

### Adding New Features
- **New Conversation States**: Update `process_turn()` in `main.py`
- **Additional Product Attributes**: Modify `Product` model in `database.py`
- **Enhanced Recommendations**: Extend `RAGSystem` class in `rag_system.py`

### Testing
- Test conversation flow with various user inputs
- Verify product recommendations match user preferences
- Check staff dashboard data accuracy

## Production Deployment

### Environment Variables
- Set `DEBUG=false` in production
- Use strong database passwords
- Configure proper logging levels

### Security Considerations
- Implement proper authentication for staff dashboard
- Use HTTPS in production
- Regular database backups
- Monitor API usage and rate limiting

## Support

For issues or questions:
1. Check the application logs
2. Verify database connectivity
3. Test individual components
4. Review the conversation flow logic

The application is designed to be robust and provide fallback recommendations when the RAG system is unavailable.
