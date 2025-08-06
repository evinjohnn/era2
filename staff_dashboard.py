"""
Staff Dashboard for Retail AI Assistant
Provides web interface for staff to view analytics, manage conversations, and monitor system performance
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_database_manager, DatabaseManager
from analytics import get_analytics_engine, AnalyticsEngine, MetricPeriod
from conversation_engine import get_conversation_engine, EnhancedConversationEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API requests
class SessionFilterRequest(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    state: Optional[str] = None
    active_only: Optional[bool] = False
    limit: Optional[int] = 50

class MetricsRequest(BaseModel):
    period: str = "last_day"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class StaffDashboard:
    """Staff dashboard management"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self.analytics_engine = get_analytics_engine()
        self.conversation_engine = get_conversation_engine()
        logger.info("Staff Dashboard initialized")
    
    def get_active_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get currently active conversation sessions"""
        try:
            db = next(self.db_manager.get_db())
            
            sessions = db.query(self.db_manager.ConversationSession).filter(
                self.db_manager.ConversationSession.is_active == True
            ).order_by(self.db_manager.ConversationSession.updated_at.desc()).limit(limit).all()
            
            active_sessions = []
            for session in sessions:
                # Get latest message
                latest_message = db.query(self.db_manager.ConversationMessage).filter(
                    self.db_manager.ConversationMessage.session_id == session.id
                ).order_by(self.db_manager.ConversationMessage.created_at.desc()).first()
                
                # Get recommendation count
                recommendation_count = db.query(self.db_manager.ProductRecommendation).filter(
                    self.db_manager.ProductRecommendation.session_id == session.id
                ).count()
                
                active_sessions.append({
                    "session_id": session.id,
                    "user_id": session.user_id,
                    "current_state": session.current_state,
                    "preferences": session.preferences,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "latest_message": latest_message.content if latest_message else None,
                    "latest_message_time": latest_message.created_at.isoformat() if latest_message else None,
                    "recommendation_count": recommendation_count,
                    "session_duration": (datetime.utcnow() - session.created_at).total_seconds()
                })
            
            return active_sessions
            
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []
    
    def get_recent_sessions(self, limit: int = 50, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent conversation sessions"""
        try:
            db = next(self.db_manager.get_db())
            
            since_time = datetime.utcnow() - timedelta(hours=hours)
            
            sessions = db.query(self.db_manager.ConversationSession).filter(
                self.db_manager.ConversationSession.created_at >= since_time
            ).order_by(self.db_manager.ConversationSession.created_at.desc()).limit(limit).all()
            
            recent_sessions = []
            for session in sessions:
                # Get message count
                message_count = db.query(self.db_manager.ConversationMessage).filter(
                    self.db_manager.ConversationMessage.session_id == session.id
                ).count()
                
                # Get recommendation count
                recommendation_count = db.query(self.db_manager.ProductRecommendation).filter(
                    self.db_manager.ProductRecommendation.session_id == session.id
                ).count()
                
                recent_sessions.append({
                    "session_id": session.id,
                    "user_id": session.user_id,
                    "current_state": session.current_state,
                    "preferences": session.preferences,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                    "is_active": session.is_active,
                    "message_count": message_count,
                    "recommendation_count": recommendation_count,
                    "session_duration": (
                        (session.ended_at - session.created_at).total_seconds()
                        if session.ended_at else
                        (datetime.utcnow() - session.created_at).total_seconds()
                    )
                })
            
            return recent_sessions
            
        except Exception as e:
            logger.error(f"Error getting recent sessions: {e}")
            return []
    
    def get_sessions_needing_attention(self) -> List[Dict[str, Any]]:
        """Get sessions that need staff attention"""
        try:
            db = next(self.db_manager.get_db())
            
            # Sessions with staff handoff requested
            handoff_sessions = db.query(self.db_manager.ConversationSession).filter(
                self.db_manager.ConversationSession.current_state == "staff_handoff_requested",
                self.db_manager.ConversationSession.is_active == True
            ).order_by(self.db_manager.ConversationSession.updated_at.desc()).all()
            
            # Long running sessions without resolution
            long_running_sessions = db.query(self.db_manager.ConversationSession).filter(
                self.db_manager.ConversationSession.is_active == True,
                self.db_manager.ConversationSession.created_at < datetime.utcnow() - timedelta(hours=2)
            ).order_by(self.db_manager.ConversationSession.created_at).all()
            
            # Error state sessions
            error_sessions = db.query(self.db_manager.ConversationSession).filter(
                self.db_manager.ConversationSession.current_state == "error_state",
                self.db_manager.ConversationSession.is_active == True
            ).order_by(self.db_manager.ConversationSession.updated_at.desc()).all()
            
            attention_needed = []
            
            # Process handoff sessions
            for session in handoff_sessions:
                latest_message = db.query(self.db_manager.ConversationMessage).filter(
                    self.db_manager.ConversationMessage.session_id == session.id
                ).order_by(self.db_manager.ConversationMessage.created_at.desc()).first()
                
                attention_needed.append({
                    "session_id": session.id,
                    "user_id": session.user_id,
                    "reason": "Staff handoff requested",
                    "priority": "high",
                    "current_state": session.current_state,
                    "preferences": session.preferences,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "latest_message": latest_message.content if latest_message else None,
                    "session_duration": (datetime.utcnow() - session.created_at).total_seconds()
                })
            
            # Process long running sessions
            for session in long_running_sessions:
                if session.id not in [s["session_id"] for s in attention_needed]:
                    attention_needed.append({
                        "session_id": session.id,
                        "user_id": session.user_id,
                        "reason": "Long running session (>2 hours)",
                        "priority": "medium",
                        "current_state": session.current_state,
                        "preferences": session.preferences,
                        "created_at": session.created_at.isoformat(),
                        "updated_at": session.updated_at.isoformat(),
                        "session_duration": (datetime.utcnow() - session.created_at).total_seconds()
                    })
            
            # Process error sessions
            for session in error_sessions:
                if session.id not in [s["session_id"] for s in attention_needed]:
                    attention_needed.append({
                        "session_id": session.id,
                        "user_id": session.user_id,
                        "reason": "Error state",
                        "priority": "high",
                        "current_state": session.current_state,
                        "preferences": session.preferences,
                        "created_at": session.created_at.isoformat(),
                        "updated_at": session.updated_at.isoformat(),
                        "session_duration": (datetime.utcnow() - session.created_at).total_seconds()
                    })
            
            return attention_needed
            
        except Exception as e:
            logger.error(f"Error getting sessions needing attention: {e}")
            return []
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics"""
        try:
            db = next(self.db_manager.get_db())
            
            # Database health
            try:
                session_count = db.query(self.db_manager.ConversationSession).count()
                db_healthy = True
            except Exception:
                db_healthy = False
                session_count = 0
            
            # Redis health (if available)
            redis_healthy = self.conversation_engine.redis_available
            
            # Vector database health
            try:
                vector_stats = self.conversation_engine.rag_system.get_system_stats()
                vector_healthy = True
            except Exception:
                vector_healthy = False
                vector_stats = {}
            
            # Recent error count
            recent_errors = db.query(self.db_manager.ConversationSession).filter(
                self.db_manager.ConversationSession.current_state == "error_state",
                self.db_manager.ConversationSession.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            # Active sessions
            active_sessions = db.query(self.db_manager.ConversationSession).filter(
                self.db_manager.ConversationSession.is_active == True
            ).count()
            
            return {
                "database": {
                    "healthy": db_healthy,
                    "total_sessions": session_count
                },
                "redis": {
                    "healthy": redis_healthy,
                    "available": redis_healthy
                },
                "vector_database": {
                    "healthy": vector_healthy,
                    "stats": vector_stats
                },
                "system_metrics": {
                    "active_sessions": active_sessions,
                    "recent_errors": recent_errors,
                    "uptime": "Available"  # Could be enhanced with actual uptime tracking
                },
                "status": "healthy" if db_healthy and vector_healthy else "degraded",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        try:
            # Get recent metrics
            conv_metrics = self.analytics_engine.get_conversation_metrics(MetricPeriod.LAST_HOUR)
            prod_metrics = self.analytics_engine.get_product_metrics(MetricPeriod.LAST_HOUR)
            
            return {
                "conversation_performance": {
                    "total_sessions": conv_metrics.total_sessions,
                    "active_sessions": conv_metrics.active_sessions,
                    "average_session_duration": conv_metrics.average_session_duration,
                    "messages_per_session": conv_metrics.average_messages_per_session,
                    "handoff_rate": conv_metrics.handoff_rate
                },
                "recommendation_performance": {
                    "total_recommendations": prod_metrics.total_recommendations,
                    "unique_products": prod_metrics.unique_products_recommended,
                    "confidence_levels": prod_metrics.confidence_levels,
                    "recommendation_types": prod_metrics.recommendation_types
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {"error": str(e)}

# Global staff dashboard instance
staff_dashboard = None

def get_staff_dashboard() -> StaffDashboard:
    """Get or create global staff dashboard instance"""
    global staff_dashboard
    if staff_dashboard is None:
        staff_dashboard = StaffDashboard()
    return staff_dashboard

# FastAPI routes for staff dashboard
def create_staff_dashboard_routes(app: FastAPI):
    """Create staff dashboard routes"""
    
    dashboard = get_staff_dashboard()
    
    @app.get("/staff/dashboard", response_class=HTMLResponse)
    async def staff_dashboard_page(request: Request):
        """Staff dashboard main page"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Staff Dashboard - Retail AI Assistant</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .dashboard { max-width: 1200px; margin: 0 auto; }
                .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
                .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .metric-card h3 { margin-top: 0; color: #333; }
                .metric-value { font-size: 2em; font-weight: bold; color: #2196F3; margin: 10px 0; }
                .sessions-table { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .sessions-table table { width: 100%; border-collapse: collapse; }
                .sessions-table th, .sessions-table td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
                .sessions-table th { background: #f8f9fa; }
                .status-healthy { color: #4CAF50; }
                .status-error { color: #f44336; }
                .priority-high { color: #f44336; font-weight: bold; }
                .priority-medium { color: #ff9800; }
                .refresh-btn { background: #2196F3; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
                .refresh-btn:hover { background: #1976D2; }
            </style>
        </head>
        <body>
            <div class="dashboard">
                <div class="header">
                    <h1>Staff Dashboard - Retail AI Assistant</h1>
                    <button class="refresh-btn" onclick="refreshDashboard()">Refresh Data</button>
                </div>
                
                <div class="metrics-grid">
                    <div class="metric-card">
                        <h3>Active Sessions</h3>
                        <div class="metric-value" id="active-sessions">Loading...</div>
                    </div>
                    <div class="metric-card">
                        <h3>Today's Sessions</h3>
                        <div class="metric-value" id="today-sessions">Loading...</div>
                    </div>
                    <div class="metric-card">
                        <h3>Staff Handoffs</h3>
                        <div class="metric-value" id="staff-handoffs">Loading...</div>
                    </div>
                    <div class="metric-card">
                        <h3>System Health</h3>
                        <div class="metric-value" id="system-health">Loading...</div>
                    </div>
                </div>
                
                <div class="sessions-table">
                    <h3>Sessions Needing Attention</h3>
                    <table id="attention-table">
                        <thead>
                            <tr>
                                <th>Session ID</th>
                                <th>Reason</th>
                                <th>Priority</th>
                                <th>Duration</th>
                                <th>State</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody id="attention-tbody">
                            <tr><td colspan="6">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
                
                <div class="sessions-table">
                    <h3>Recent Sessions</h3>
                    <table id="recent-table">
                        <thead>
                            <tr>
                                <th>Session ID</th>
                                <th>State</th>
                                <th>Messages</th>
                                <th>Recommendations</th>
                                <th>Duration</th>
                                <th>Created</th>
                            </tr>
                        </thead>
                        <tbody id="recent-tbody">
                            <tr><td colspan="6">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <script>
                async function refreshDashboard() {
                    // Update metrics
                    const metricsResponse = await fetch('/staff/api/metrics');
                    const metricsData = await metricsResponse.json();
                    
                    document.getElementById('active-sessions').textContent = metricsData.conversation_performance.active_sessions || 0;
                    document.getElementById('today-sessions').textContent = metricsData.conversation_performance.total_sessions || 0;
                    document.getElementById('staff-handoffs').textContent = Math.round((metricsData.conversation_performance.handoff_rate || 0) * 100) + '%';
                    
                    // Update system health
                    const healthResponse = await fetch('/staff/api/health');
                    const healthData = await healthResponse.json();
                    const healthElement = document.getElementById('system-health');
                    healthElement.textContent = healthData.status;
                    healthElement.className = healthData.status === 'healthy' ? 'metric-value status-healthy' : 'metric-value status-error';
                    
                    // Update sessions needing attention
                    const attentionResponse = await fetch('/staff/api/attention');
                    const attentionData = await attentionResponse.json();
                    const attentionTbody = document.getElementById('attention-tbody');
                    
                    if (attentionData.length === 0) {
                        attentionTbody.innerHTML = '<tr><td colspan="6">No sessions need attention</td></tr>';
                    } else {
                        attentionTbody.innerHTML = attentionData.map(session => `
                            <tr>
                                <td>${session.session_id.substring(0, 8)}...</td>
                                <td>${session.reason}</td>
                                <td class="priority-${session.priority}">${session.priority}</td>
                                <td>${Math.round(session.session_duration / 60)} min</td>
                                <td>${session.current_state}</td>
                                <td><a href="/staff/session/${session.session_id}">View</a></td>
                            </tr>
                        `).join('');
                    }
                    
                    // Update recent sessions
                    const recentResponse = await fetch('/staff/api/recent');
                    const recentData = await recentResponse.json();
                    const recentTbody = document.getElementById('recent-tbody');
                    
                    recentTbody.innerHTML = recentData.map(session => `
                        <tr>
                            <td>${session.session_id.substring(0, 8)}...</td>
                            <td>${session.current_state}</td>
                            <td>${session.message_count}</td>
                            <td>${session.recommendation_count}</td>
                            <td>${Math.round(session.session_duration / 60)} min</td>
                            <td>${new Date(session.created_at).toLocaleString()}</td>
                        </tr>
                    `).join('');
                }
                
                // Auto-refresh every 30 seconds
                setInterval(refreshDashboard, 30000);
                
                // Initial load
                refreshDashboard();
            </script>
        </body>
        </html>
        """
    
    @app.get("/staff/api/metrics")
    async def get_staff_metrics():
        """Get staff dashboard metrics"""
        try:
            metrics = dashboard.get_performance_metrics()
            return JSONResponse(content=metrics)
        except Exception as e:
            logger.error(f"Error getting staff metrics: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
    
    @app.get("/staff/api/health")
    async def get_system_health():
        """Get system health status"""
        try:
            health = dashboard.get_system_health()
            return JSONResponse(content=health)
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
    
    @app.get("/staff/api/attention")
    async def get_attention_sessions():
        """Get sessions needing attention"""
        try:
            sessions = dashboard.get_sessions_needing_attention()
            return JSONResponse(content=sessions)
        except Exception as e:
            logger.error(f"Error getting attention sessions: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
    
    @app.get("/staff/api/recent")
    async def get_recent_sessions():
        """Get recent sessions"""
        try:
            sessions = dashboard.get_recent_sessions()
            return JSONResponse(content=sessions)
        except Exception as e:
            logger.error(f"Error getting recent sessions: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
    
    @app.get("/staff/api/session/{session_id}")
    async def get_session_details(session_id: str):
        """Get detailed session information"""
        try:
            details = dashboard.analytics_engine.get_session_details(session_id)
            return JSONResponse(content=details)
        except Exception as e:
            logger.error(f"Error getting session details: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
    
    @app.get("/staff/api/dashboard")
    async def get_dashboard_data():
        """Get comprehensive dashboard data"""
        try:
            data = dashboard.analytics_engine.get_comprehensive_dashboard_data()
            return JSONResponse(content=data)
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    # Test the staff dashboard
    print("Testing Staff Dashboard...")
    
    try:
        dashboard = get_staff_dashboard()
        
        # Test active sessions
        active_sessions = dashboard.get_active_sessions()
        print(f"✅ Active sessions: {len(active_sessions)}")
        
        # Test system health
        health = dashboard.get_system_health()
        print(f"✅ System health: {health['status']}")
        
        # Test performance metrics
        metrics = dashboard.get_performance_metrics()
        print("✅ Performance metrics retrieved")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()