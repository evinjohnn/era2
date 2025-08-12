"""
Staff Dashboard for Retail AI Assistant - Serves the dashboard HTML and its API endpoints.
"""
import logging
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from database import get_database_manager # Assuming analytics logic will be added here later

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_staff_dashboard_routes(app: FastAPI):
    """Create staff dashboard routes"""
    
    @app.get("/staff/dashboard")
    async def staff_dashboard_page():
        """Serves the standalone staff dashboard HTML file."""
        return FileResponse('static/dashboard.html')

    @app.get("/staff/api/dashboard-data")
    async def get_dashboard_data():
        """Provides mock data for the dashboard. In a real app, this would query the analytics engine."""
        # This is mock data. A full implementation would use the analytics.py module.
        mock_data = {
            "conversation_metrics": {
                "total_sessions": 152,
                "active_sessions": 8,
                "completed_sessions": 144,
                "average_session_duration": 125.6,
                "handoff_rate": 0.08
            },
            "user_behavior_metrics": {
                "peak_hours": [5, 3, 2, 4, 6, 8, 15, 25, 40, 55, 60, 50, 45, 48, 52, 40, 35, 30, 22, 18, 15, 12, 10, 8]
            },
            "product_metrics": {
                "top_recommended_products": [
                    {"product_name": "Elegant Diamond Solitaire Ring", "recommendation_count": 45},
                    {"product_name": "Classic Pearl Necklace", "recommendation_count": 32},
                    {"product_name": "Modern Gold Hoop Earrings", "recommendation_count": 28}
                ],
                "category_breakdown": {"rings": 120, "necklaces": 80, "earrings": 65, "bracelets": 50},
                "price_range_breakdown": {
                    "Under $500": 150,
                    "$500-$1000": 90,
                    "$1000-$2000": 65,
                    "Over $2000": 30
                }
            }
        }
        return JSONResponse(content=mock_data)