"""
Analytics and Reporting System for Retail AI Assistant
Handles conversation analytics, performance metrics, and business intelligence
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from dataclasses import dataclass, asdict
from enum import Enum

from database import (
    DatabaseManager, get_database_manager, 
    ConversationSession, ConversationMessage, 
    ProductRecommendation, ConversationAnalytics, Product
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricPeriod(Enum):
    """Time period for metrics"""
    LAST_HOUR = "last_hour"
    LAST_DAY = "last_day"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    CUSTOM = "custom"

@dataclass
class ConversationMetrics:
    """Conversation performance metrics"""
    total_sessions: int
    active_sessions: int
    completed_sessions: int
    average_session_duration: float
    total_messages: int
    average_messages_per_session: float
    user_messages: int
    assistant_messages: int
    products_recommended: int
    average_recommendations_per_session: float
    staff_handoffs: int
    handoff_rate: float
    period: str
    start_date: datetime
    end_date: datetime

@dataclass
class ProductMetrics:
    """Product recommendation metrics"""
    total_recommendations: int
    unique_products_recommended: int
    top_recommended_products: List[Dict[str, Any]]
    recommendation_types: Dict[str, int]
    confidence_levels: Dict[str, int]
    user_interactions: Dict[str, int]
    category_breakdown: Dict[str, int]
    price_range_breakdown: Dict[str, int]
    period: str
    start_date: datetime
    end_date: datetime

@dataclass
class UserBehaviorMetrics:
    """User behavior and engagement metrics"""
    total_unique_sessions: int
    average_session_length: float
    bounce_rate: float
    engagement_score: float
    most_common_intents: List[Dict[str, Any]]
    preference_patterns: Dict[str, Any]
    conversion_funnel: Dict[str, int]
    peak_hours: List[int]
    period: str
    start_date: datetime
    end_date: datetime

class AnalyticsEngine:
    """Analytics engine for conversation and product metrics"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
        logger.info("Analytics Engine initialized")
    
    def get_period_dates(self, period: MetricPeriod, start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None) -> Tuple[datetime, datetime]:
        """Get start and end dates for a given period"""
        now = datetime.utcnow()
        
        if period == MetricPeriod.CUSTOM:
            return start_date or now, end_date or now
        elif period == MetricPeriod.LAST_HOUR:
            return now - timedelta(hours=1), now
        elif period == MetricPeriod.LAST_DAY:
            return now - timedelta(days=1), now
        elif period == MetricPeriod.LAST_WEEK:
            return now - timedelta(weeks=1), now
        elif period == MetricPeriod.LAST_MONTH:
            return now - timedelta(days=30), now
        else:
            return now - timedelta(days=1), now
    
    def get_conversation_metrics(self, period: MetricPeriod = MetricPeriod.LAST_DAY,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> ConversationMetrics:
        """Get conversation performance metrics"""
        try:
            db = next(self.db_manager.get_db())
            period_start, period_end = self.get_period_dates(period, start_date, end_date)
            
            # Base query for sessions in period
            session_query = db.query(ConversationSession).filter(
                ConversationSession.created_at >= period_start,
                ConversationSession.created_at <= period_end
            )
            
            # Session metrics
            total_sessions = session_query.count()
            active_sessions = session_query.filter(ConversationSession.is_active == True).count()
            completed_sessions = session_query.filter(ConversationSession.ended_at.isnot(None)).count()
            
            # Session duration
            completed_sessions_data = session_query.filter(
                ConversationSession.ended_at.isnot(None)
            ).all()
            
            if completed_sessions_data:
                durations = [
                    (session.ended_at - session.created_at).total_seconds()
                    for session in completed_sessions_data
                ]
                average_session_duration = sum(durations) / len(durations)
            else:
                average_session_duration = 0
            
            # Message metrics
            message_query = db.query(ConversationMessage).filter(
                ConversationMessage.created_at >= period_start,
                ConversationMessage.created_at <= period_end
            )
            
            total_messages = message_query.count()
            user_messages = message_query.filter(ConversationMessage.role == "user").count()
            assistant_messages = message_query.filter(ConversationMessage.role == "assistant").count()
            
            average_messages_per_session = total_messages / total_sessions if total_sessions > 0 else 0
            
            # Recommendation metrics
            recommendation_query = db.query(ProductRecommendation).filter(
                ProductRecommendation.created_at >= period_start,
                ProductRecommendation.created_at <= period_end
            )
            
            products_recommended = recommendation_query.count()
            average_recommendations_per_session = products_recommended / total_sessions if total_sessions > 0 else 0
            
            # Staff handoff metrics
            staff_handoff_sessions = session_query.filter(
                ConversationSession.current_state == "staff_handoff_requested"
            ).count()
            
            handoff_rate = staff_handoff_sessions / total_sessions if total_sessions > 0 else 0
            
            return ConversationMetrics(
                total_sessions=total_sessions,
                active_sessions=active_sessions,
                completed_sessions=completed_sessions,
                average_session_duration=average_session_duration,
                total_messages=total_messages,
                average_messages_per_session=average_messages_per_session,
                user_messages=user_messages,
                assistant_messages=assistant_messages,
                products_recommended=products_recommended,
                average_recommendations_per_session=average_recommendations_per_session,
                staff_handoffs=staff_handoff_sessions,
                handoff_rate=handoff_rate,
                period=period.value,
                start_date=period_start,
                end_date=period_end
            )
            
        except Exception as e:
            logger.error(f"Error getting conversation metrics: {e}")
            return ConversationMetrics(
                total_sessions=0, active_sessions=0, completed_sessions=0,
                average_session_duration=0, total_messages=0,
                average_messages_per_session=0, user_messages=0,
                assistant_messages=0, products_recommended=0,
                average_recommendations_per_session=0, staff_handoffs=0,
                handoff_rate=0, period=period.value,
                start_date=period_start, end_date=period_end
            )
    
    def get_product_metrics(self, period: MetricPeriod = MetricPeriod.LAST_DAY,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> ProductMetrics:
        """Get product recommendation metrics"""
        try:
            db = next(self.db_manager.get_db())
            period_start, period_end = self.get_period_dates(period, start_date, end_date)
            
            # Base query for recommendations in period
            recommendation_query = db.query(ProductRecommendation).filter(
                ProductRecommendation.created_at >= period_start,
                ProductRecommendation.created_at <= period_end
            )
            
            total_recommendations = recommendation_query.count()
            unique_products_recommended = recommendation_query.distinct(ProductRecommendation.product_id).count()
            
            # Top recommended products
            top_products = (
                db.query(
                    ProductRecommendation.product_id,
                    func.count(ProductRecommendation.product_id).label('count'),
                    func.avg(ProductRecommendation.similarity_score).label('avg_score')
                )
                .filter(
                    ProductRecommendation.created_at >= period_start,
                    ProductRecommendation.created_at <= period_end
                )
                .group_by(ProductRecommendation.product_id)
                .order_by(func.count(ProductRecommendation.product_id).desc())
                .limit(10)
                .all()
            )
            
            # Get product details for top products
            top_recommended_products = []
            for product_id, count, avg_score in top_products:
                product = db.query(Product).filter(Product.id == product_id).first()
                if product:
                    top_recommended_products.append({
                        "product_id": product_id,
                        "product_name": product.name,
                        "category": product.category,
                        "price": product.price,
                        "recommendation_count": count,
                        "average_similarity_score": float(avg_score) if avg_score else 0
                    })
            
            # Recommendation types
            recommendation_types = {}
            for rec_type, count in (
                db.query(ProductRecommendation.recommendation_type, func.count())
                .filter(
                    ProductRecommendation.created_at >= period_start,
                    ProductRecommendation.created_at <= period_end
                )
                .group_by(ProductRecommendation.recommendation_type)
                .all()
            ):
                recommendation_types[rec_type] = count
            
            # Confidence levels
            confidence_levels = {}
            for confidence, count in (
                db.query(ProductRecommendation.confidence_level, func.count())
                .filter(
                    ProductRecommendation.created_at >= period_start,
                    ProductRecommendation.created_at <= period_end
                )
                .group_by(ProductRecommendation.confidence_level)
                .all()
            ):
                confidence_levels[confidence] = count
            
            # User interactions
            user_interactions = {}
            for interaction, count in (
                db.query(ProductRecommendation.user_interaction, func.count())
                .filter(
                    ProductRecommendation.created_at >= period_start,
                    ProductRecommendation.created_at <= period_end,
                    ProductRecommendation.user_interaction.isnot(None)
                )
                .group_by(ProductRecommendation.user_interaction)
                .all()
            ):
                user_interactions[interaction] = count
            
            # Category breakdown
            category_breakdown = {}
            for category, count in (
                db.query(Product.category, func.count())
                .join(ProductRecommendation, Product.id == ProductRecommendation.product_id)
                .filter(
                    ProductRecommendation.created_at >= period_start,
                    ProductRecommendation.created_at <= period_end
                )
                .group_by(Product.category)
                .all()
            ):
                category_breakdown[category] = count
            
            # Price range breakdown
            price_ranges = [
                ("Under $500", 0, 500),
                ("$500-$1000", 500, 1000),
                ("$1000-$2000", 1000, 2000),
                ("$2000-$5000", 2000, 5000),
                ("Over $5000", 5000, float('inf'))
            ]
            
            price_range_breakdown = {}
            for range_name, min_price, max_price in price_ranges:
                count = (
                    db.query(ProductRecommendation)
                    .join(Product, Product.id == ProductRecommendation.product_id)
                    .filter(
                        ProductRecommendation.created_at >= period_start,
                        ProductRecommendation.created_at <= period_end,
                        Product.price >= min_price,
                        Product.price < max_price if max_price != float('inf') else True
                    )
                    .count()
                )
                price_range_breakdown[range_name] = count
            
            return ProductMetrics(
                total_recommendations=total_recommendations,
                unique_products_recommended=unique_products_recommended,
                top_recommended_products=top_recommended_products,
                recommendation_types=recommendation_types,
                confidence_levels=confidence_levels,
                user_interactions=user_interactions,
                category_breakdown=category_breakdown,
                price_range_breakdown=price_range_breakdown,
                period=period.value,
                start_date=period_start,
                end_date=period_end
            )
            
        except Exception as e:
            logger.error(f"Error getting product metrics: {e}")
            return ProductMetrics(
                total_recommendations=0, unique_products_recommended=0,
                top_recommended_products=[], recommendation_types={},
                confidence_levels={}, user_interactions={},
                category_breakdown={}, price_range_breakdown={},
                period=period.value, start_date=period_start, end_date=period_end
            )
    
    def get_user_behavior_metrics(self, period: MetricPeriod = MetricPeriod.LAST_DAY,
                                start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None) -> UserBehaviorMetrics:
        """Get user behavior and engagement metrics"""
        try:
            db = next(self.db_manager.get_db())
            period_start, period_end = self.get_period_dates(period, start_date, end_date)
            
            # Base metrics
            total_unique_sessions = db.query(ConversationSession).filter(
                ConversationSession.created_at >= period_start,
                ConversationSession.created_at <= period_end
            ).count()
            
            # Session lengths
            sessions_with_messages = (
                db.query(
                    ConversationSession.id,
                    func.count(ConversationMessage.id).label('message_count'),
                    func.max(ConversationMessage.created_at).label('last_message'),
                    func.min(ConversationMessage.created_at).label('first_message')
                )
                .join(ConversationMessage, ConversationSession.id == ConversationMessage.session_id)
                .filter(
                    ConversationSession.created_at >= period_start,
                    ConversationSession.created_at <= period_end
                )
                .group_by(ConversationSession.id)
                .all()
            )
            
            if sessions_with_messages:
                session_lengths = [
                    (session.last_message - session.first_message).total_seconds()
                    for session in sessions_with_messages
                ]
                average_session_length = sum(session_lengths) / len(session_lengths)
                
                # Bounce rate (sessions with only 1 message)
                single_message_sessions = sum(1 for session in sessions_with_messages if session.message_count <= 1)
                bounce_rate = single_message_sessions / len(sessions_with_messages) if sessions_with_messages else 0
            else:
                average_session_length = 0
                bounce_rate = 0
            
            # Engagement score (average messages per session)
            total_messages = db.query(ConversationMessage).filter(
                ConversationMessage.created_at >= period_start,
                ConversationMessage.created_at <= period_end
            ).count()
            
            engagement_score = total_messages / total_unique_sessions if total_unique_sessions > 0 else 0
            
            # Most common intents (based on conversation states)
            most_common_intents = []
            for state, count in (
                db.query(ConversationSession.current_state, func.count())
                .filter(
                    ConversationSession.created_at >= period_start,
                    ConversationSession.created_at <= period_end
                )
                .group_by(ConversationSession.current_state)
                .order_by(func.count().desc())
                .limit(10)
                .all()
            ):
                most_common_intents.append({
                    "intent": state,
                    "count": count,
                    "percentage": (count / total_unique_sessions) * 100 if total_unique_sessions > 0 else 0
                })
            
            # Preference patterns
            preference_patterns = {}
            sessions_with_preferences = db.query(ConversationSession).filter(
                ConversationSession.created_at >= period_start,
                ConversationSession.created_at <= period_end,
                ConversationSession.preferences.isnot(None)
            ).all()
            
            for session in sessions_with_preferences:
                prefs = session.preferences or {}
                for key, value in prefs.items():
                    if value is not None:
                        if key not in preference_patterns:
                            preference_patterns[key] = {}
                        if value not in preference_patterns[key]:
                            preference_patterns[key][value] = 0
                        preference_patterns[key][value] += 1
            
            # Conversion funnel (simplified)
            conversion_funnel = {
                "initiated_conversation": total_unique_sessions,
                "provided_preferences": len(sessions_with_preferences),
                "received_recommendations": db.query(ConversationSession).filter(
                    ConversationSession.created_at >= period_start,
                    ConversationSession.created_at <= period_end
                ).join(ProductRecommendation).distinct(ConversationSession.id).count(),
                "requested_staff": db.query(ConversationSession).filter(
                    ConversationSession.created_at >= period_start,
                    ConversationSession.created_at <= period_end,
                    ConversationSession.current_state == "staff_handoff_requested"
                ).count()
            }
            
            # Peak hours
            peak_hours = []
            for hour in range(24):
                count = db.query(ConversationSession).filter(
                    ConversationSession.created_at >= period_start,
                    ConversationSession.created_at <= period_end,
                    func.extract('hour', ConversationSession.created_at) == hour
                ).count()
                peak_hours.append(count)
            
            return UserBehaviorMetrics(
                total_unique_sessions=total_unique_sessions,
                average_session_length=average_session_length,
                bounce_rate=bounce_rate,
                engagement_score=engagement_score,
                most_common_intents=most_common_intents,
                preference_patterns=preference_patterns,
                conversion_funnel=conversion_funnel,
                peak_hours=peak_hours,
                period=period.value,
                start_date=period_start,
                end_date=period_end
            )
            
        except Exception as e:
            logger.error(f"Error getting user behavior metrics: {e}")
            return UserBehaviorMetrics(
                total_unique_sessions=0, average_session_length=0,
                bounce_rate=0, engagement_score=0,
                most_common_intents=[], preference_patterns={},
                conversion_funnel={}, peak_hours=[0] * 24,
                period=period.value, start_date=period_start, end_date=period_end
            )
    
    def get_comprehensive_dashboard_data(self, period: MetricPeriod = MetricPeriod.LAST_DAY) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        try:
            conversation_metrics = self.get_conversation_metrics(period)
            product_metrics = self.get_product_metrics(period)
            user_behavior_metrics = self.get_user_behavior_metrics(period)
            
            return {
                "conversation_metrics": asdict(conversation_metrics),
                "product_metrics": asdict(product_metrics),
                "user_behavior_metrics": asdict(user_behavior_metrics),
                "generated_at": datetime.utcnow().isoformat(),
                "period": period.value
            }
            
        except Exception as e:
            logger.error(f"Error getting comprehensive dashboard data: {e}")
            return {"error": str(e)}
    
    def get_session_details(self, session_id: str) -> Dict[str, Any]:
        """Get detailed session information"""
        try:
            db = next(self.db_manager.get_db())
            
            # Get session
            session = db.query(ConversationSession).filter(
                ConversationSession.id == session_id
            ).first()
            
            if not session:
                return {"error": "Session not found"}
            
            # Get messages
            messages = db.query(ConversationMessage).filter(
                ConversationMessage.session_id == session_id
            ).order_by(ConversationMessage.created_at).all()
            
            # Get recommendations
            recommendations = db.query(ProductRecommendation).filter(
                ProductRecommendation.session_id == session_id
            ).all()
            
            # Get analytics events
            analytics_events = db.query(ConversationAnalytics).filter(
                ConversationAnalytics.session_id == session_id
            ).order_by(ConversationAnalytics.timestamp).all()
            
            return {
                "session": {
                    "id": session.id,
                    "user_id": session.user_id,
                    "current_state": session.current_state,
                    "preferences": session.preferences,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                    "is_active": session.is_active
                },
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "preferences_at_turn": msg.preferences_at_turn,
                        "created_at": msg.created_at.isoformat()
                    }
                    for msg in messages
                ],
                "recommendations": [
                    {
                        "id": rec.id,
                        "product_id": rec.product_id,
                        "similarity_score": rec.similarity_score,
                        "confidence_level": rec.confidence_level,
                        "recommendation_type": rec.recommendation_type,
                        "user_interaction": rec.user_interaction,
                        "created_at": rec.created_at.isoformat()
                    }
                    for rec in recommendations
                ],
                "analytics_events": [
                    {
                        "id": event.id,
                        "event_type": event.event_type,
                        "event_data": event.event_data,
                        "timestamp": event.timestamp.isoformat()
                    }
                    for event in analytics_events
                ],
                "summary": {
                    "total_messages": len(messages),
                    "total_recommendations": len(recommendations),
                    "total_analytics_events": len(analytics_events),
                    "session_duration": (
                        (session.ended_at - session.created_at).total_seconds()
                        if session.ended_at else
                        (datetime.utcnow() - session.created_at).total_seconds()
                    )
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting session details: {e}")
            return {"error": str(e)}

# Global analytics engine instance
analytics_engine = None

def get_analytics_engine() -> AnalyticsEngine:
    """Get or create global analytics engine instance"""
    global analytics_engine
    if analytics_engine is None:
        analytics_engine = AnalyticsEngine()
    return analytics_engine

if __name__ == "__main__":
    # Test the analytics engine
    print("Testing Analytics Engine...")
    
    try:
        engine = get_analytics_engine()
        
        # Test conversation metrics
        conv_metrics = engine.get_conversation_metrics(MetricPeriod.LAST_DAY)
        print(f"✅ Conversation metrics: {conv_metrics.total_sessions} sessions")
        
        # Test product metrics
        prod_metrics = engine.get_product_metrics(MetricPeriod.LAST_DAY)
        print(f"✅ Product metrics: {prod_metrics.total_recommendations} recommendations")
        
        # Test user behavior metrics
        behavior_metrics = engine.get_user_behavior_metrics(MetricPeriod.LAST_DAY)
        print(f"✅ User behavior metrics: {behavior_metrics.total_unique_sessions} unique sessions")
        
        # Test comprehensive dashboard
        dashboard_data = engine.get_comprehensive_dashboard_data(MetricPeriod.LAST_DAY)
        print("✅ Generated comprehensive dashboard data")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()