"""
Staff Dashboard for Retail AI Assistant - Serves the dashboard HTML and its API endpoints.
"""
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from analytics import get_analytics_engine, MetricPeriod
from datetime import datetime, timedelta

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
        """Provides real analytics data for the dashboard using the analytics engine."""
        try:
            analytics_engine = get_analytics_engine()
            
            # Get analytics data for the last 24 hours
            dashboard_data = analytics_engine.get_comprehensive_dashboard_data(MetricPeriod.LAST_DAY)
            
            if "error" in dashboard_data:
                logger.error(f"Error getting dashboard data: {dashboard_data['error']}")
                raise HTTPException(status_code=500, detail="Failed to fetch analytics data")
            
            # Transform the data to match the expected format in the frontend
            transformed_data = {
                "conversation_metrics": {
                    "total_sessions": dashboard_data["conversation_metrics"].get("total_sessions", 0),
                    "active_sessions": dashboard_data["conversation_metrics"].get("active_sessions", 0),
                    "completed_sessions": dashboard_data["conversation_metrics"].get("completed_sessions", 0),
                    "average_session_duration": dashboard_data["conversation_metrics"].get("average_session_duration", 0),
                    "handoff_rate": dashboard_data["conversation_metrics"].get("handoff_rate", 0),
                    "total_messages": dashboard_data["conversation_metrics"].get("total_messages", 0),
                    "user_messages": dashboard_data["conversation_metrics"].get("user_messages", 0),
                    "assistant_messages": dashboard_data["conversation_metrics"].get("assistant_messages", 0),
                    "average_messages_per_session": dashboard_data["conversation_metrics"].get("average_messages_per_session", 0),
                    "products_recommended": dashboard_data["conversation_metrics"].get("products_recommended", 0),
                    "average_recommendations_per_session": dashboard_data["conversation_metrics"].get("average_recommendations_per_session", 0)
                },
                "user_behavior_metrics": {
                    "peak_hours": dashboard_data["user_behavior_metrics"].get("peak_hours", [0] * 24)
                },
                "product_metrics": {
                    "top_recommended_products": dashboard_data["product_metrics"].get("top_recommended_products", []),
                    "category_breakdown": dashboard_data["product_metrics"].get("category_breakdown", {}),
                    "price_range_breakdown": dashboard_data["product_metrics"].get("price_range_breakdown", {}),
                    "total_recommendations": dashboard_data["product_metrics"].get("total_recommendations", 0),
                    "unique_products_recommended": dashboard_data["product_metrics"].get("unique_products_recommended", 0)
                }
            }
            
            logger.info(f"Successfully fetched dashboard data: {transformed_data['conversation_metrics']['total_sessions']} sessions")
            return JSONResponse(content=transformed_data)
            
        except Exception as e:
            logger.error(f"Error in get_dashboard_data: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    @app.get("/staff/api/analytics/{period}")
    async def get_analytics_by_period(period: str):
        """Get analytics data for a specific time period."""
        try:
            analytics_engine = get_analytics_engine()
            
            # Map period string to MetricPeriod enum
            period_map = {
                "last_hour": MetricPeriod.LAST_HOUR,
                "last_day": MetricPeriod.LAST_DAY,
                "last_week": MetricPeriod.LAST_WEEK,
                "last_month": MetricPeriod.LAST_MONTH
            }
            
            if period not in period_map:
                raise HTTPException(status_code=400, detail="Invalid period. Use: last_hour, last_day, last_week, last_month")
            
            metric_period = period_map[period]
            dashboard_data = analytics_engine.get_comprehensive_dashboard_data(metric_period)
            
            if "error" in dashboard_data:
                logger.error(f"Error getting analytics for period {period}: {dashboard_data['error']}")
                raise HTTPException(status_code=500, detail="Failed to fetch analytics data")
            
            return JSONResponse(content=dashboard_data)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in get_analytics_by_period: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    @app.get("/staff/api/session/{session_id}")
    async def get_session_details(session_id: str):
        """Get detailed information about a specific conversation session."""
        try:
            analytics_engine = get_analytics_engine()
            session_data = analytics_engine.get_session_details(session_id)
            
            if "error" in session_data:
                raise HTTPException(status_code=404, detail=session_data["error"])
            
            return JSONResponse(content=session_data)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in get_session_details: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    @app.get("/staff/api/health")
    async def dashboard_health_check():
        """Health check endpoint for the dashboard."""
        try:
            analytics_engine = get_analytics_engine()
            
            # Test basic analytics functionality
            test_metrics = analytics_engine.get_conversation_metrics(MetricPeriod.LAST_DAY)
            
            return JSONResponse(content={
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "analytics_engine": "operational",
                "test_metrics": {
                    "total_sessions": test_metrics.total_sessions,
                    "database_connection": "successful"
                }
            })
            
        except Exception as e:
            logger.error(f"Dashboard health check failed: {e}")
            return JSONResponse(
                content={
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e)
                },
                status_code=500
            )