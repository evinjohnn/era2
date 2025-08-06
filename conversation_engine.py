"""
Advanced Conversation Engine for Retail AI Assistant
Handles enhanced conversation management with memory, context tracking, and analytics
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum

from database import DatabaseManager, get_database_manager, SessionCreate, MessageCreate
from cache import get_redis_client
from rag_system import get_rag_system

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationState(Enum):
    """Conversation state enumeration"""
    INITIAL_GREETING = "initial_greeting"
    IDENTIFYING_PURPOSE = "identifying_purpose"
    COLLECTING_PRODUCT_TYPE = "collecting_product_type"
    GATHERING_PREFERENCES = "gathering_preferences"
    READY_FOR_RECOMMENDATION = "ready_for_recommendation"
    REFINING_RECOMMENDATION = "refining_recommendation"
    STAFF_HANDOFF_REQUESTED = "staff_handoff_requested"
    ERROR_STATE = "error_state"
    CONVERSATION_ENDED = "conversation_ended"

class ConversationAction(Enum):
    """Conversation action enumeration"""
    ASK_QUESTION = "ask_question"
    RECOMMEND_PRODUCTS = "recommend_products"
    OFFER_STAFF_HANDOFF = "offer_staff_handoff"
    END_CONVERSATION = "end_conversation"

@dataclass
class ConversationContext:
    """Conversation context data structure"""
    session_id: str
    user_id: Optional[str] = None
    current_state: ConversationState = ConversationState.INITIAL_GREETING
    preferences: Dict[str, Any] = None
    conversation_history: List[Dict[str, Any]] = None
    last_shown_products: List[str] = None
    conversation_metadata: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.preferences is None:
            self.preferences = {}
        if self.conversation_history is None:
            self.conversation_history = []
        if self.last_shown_products is None:
            self.last_shown_products = []
        if self.conversation_metadata is None:
            self.conversation_metadata = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

@dataclass
class ConversationResponse:
    """Conversation response data structure"""
    session_id: str
    reply: str
    products: Optional[List[Dict[str, Any]]] = None
    current_state: str = ConversationState.INITIAL_GREETING.value
    next_action: str = ConversationAction.ASK_QUESTION.value
    action_buttons: Optional[List[Dict[str, str]]] = None
    end_conversation: bool = False
    confidence_score: str = "medium"
    conversation_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.conversation_metadata is None:
            self.conversation_metadata = {}

class EnhancedConversationEngine:
    """Enhanced conversation engine with advanced memory and context tracking"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self.redis_client = get_redis_client()
        self.rag_system = get_rag_system()
        self.redis_available = self.redis_client.is_connected() if self.redis_client else False
        
        # Conversation configuration
        self.max_conversation_turns = 50
        self.session_timeout = 3600  # 1 hour
        self.preference_keys = [
            "occasion", "recipient", "category", "metal", 
            "design_type", "style", "budget_max", "gemstone"
        ]
        
        logger.info("Enhanced Conversation Engine initialized")
    
    def get_or_create_context(self, session_id: str, user_id: Optional[str] = None) -> ConversationContext:
        """Get or create conversation context"""
        try:
            # Try to get from database first
            db = next(self.db_manager.get_db())
            session = self.db_manager.get_session(db, session_id)
            
            if session:
                # Load conversation history
                messages = self.db_manager.get_conversation_history(db, session_id, limit=20)
                history = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat(),
                        "preferences": msg.preferences_at_turn
                    }
                    for msg in reversed(messages)
                ]
                
                context = ConversationContext(
                    session_id=session.id,
                    user_id=session.user_id,
                    current_state=ConversationState(session.current_state),
                    preferences=session.preferences,
                    conversation_history=history,
                    last_shown_products=session.last_shown_product_ids,
                    created_at=session.created_at,
                    updated_at=session.updated_at
                )
                
                logger.info(f"Loaded existing context for session {session_id}")
                return context
            
            # Create new context
            context = ConversationContext(
                session_id=session_id,
                user_id=user_id,
                preferences={key: None for key in self.preference_keys}
            )
            
            # Save to database
            session_data = SessionCreate(
                id=session_id,
                user_id=user_id,
                current_state=context.current_state.value,
                preferences=context.preferences
            )
            
            self.db_manager.create_session(db, session_data)
            
            # Log analytics event
            self.db_manager.log_analytics_event(
                db, session_id, "session_created", 
                {"user_id": user_id, "timestamp": datetime.utcnow().isoformat()}
            )
            
            logger.info(f"Created new context for session {session_id}")
            return context
            
        except Exception as e:
            logger.error(f"Error getting/creating context for session {session_id}: {e}")
            # Return default context as fallback
            return ConversationContext(
                session_id=session_id,
                user_id=user_id,
                preferences={key: None for key in self.preference_keys}
            )
    
    def save_context(self, context: ConversationContext) -> bool:
        """Save conversation context to database"""
        try:
            db = next(self.db_manager.get_db())
            
            # Update session
            updates = {
                "current_state": context.current_state.value,
                "preferences": context.preferences,
                "last_shown_product_ids": context.last_shown_products,
                "updated_at": datetime.utcnow()
            }
            
            self.db_manager.update_session(db, context.session_id, updates)
            
            logger.debug(f"Saved context for session {context.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving context for session {context.session_id}: {e}")
            return False
    
    def add_message_to_context(self, context: ConversationContext, role: str, 
                             content: str, llm_metadata: Dict[str, Any] = None) -> bool:
        """Add message to conversation context and database"""
        try:
            db = next(self.db_manager.get_db())
            
            # Add to database
            message_data = MessageCreate(
                session_id=context.session_id,
                role=role,
                content=content,
                preferences_at_turn=context.preferences.copy(),
                llm_metadata=llm_metadata or {}
            )
            
            message = self.db_manager.add_message(db, message_data)
            
            # Update context history
            context.conversation_history.append({
                "role": role,
                "content": content,
                "timestamp": message.created_at.isoformat(),
                "preferences": context.preferences.copy()
            })
            
            # Keep only recent history in memory
            if len(context.conversation_history) > 20:
                context.conversation_history = context.conversation_history[-20:]
            
            # Log analytics event
            self.db_manager.log_analytics_event(
                db, context.session_id, "message_added",
                {"role": role, "content_length": len(content)}
            )
            
            logger.debug(f"Added message to context for session {context.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding message to context: {e}")
            return False
    
    def update_preferences(self, context: ConversationContext, new_preferences: Dict[str, Any]) -> bool:
        """Update conversation preferences"""
        try:
            # Update preferences
            for key in self.preference_keys:
                if key in new_preferences:
                    if new_preferences[key] is not None and str(new_preferences[key]).strip() != "":
                        context.preferences[key] = new_preferences[key]
                    elif new_preferences[key] is None:
                        context.preferences[key] = None
            
            context.updated_at = datetime.utcnow()
            
            # Save to database
            self.save_context(context)
            
            logger.info(f"Updated preferences for session {context.session_id}: {context.preferences}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return False
    
    def get_conversation_summary(self, context: ConversationContext) -> Dict[str, Any]:
        """Get conversation summary and analytics"""
        try:
            db = next(self.db_manager.get_db())
            
            # Get full conversation history
            messages = self.db_manager.get_conversation_history(db, context.session_id, limit=100)
            
            # Calculate metrics
            total_messages = len(messages)
            user_messages = len([m for m in messages if m.role == "user"])
            assistant_messages = len([m for m in messages if m.role == "assistant"])
            
            # Get recommendations
            recommendations = db.query(context.db_manager.ProductRecommendation).filter(
                context.db_manager.ProductRecommendation.session_id == context.session_id
            ).all()
            
            summary = {
                "session_id": context.session_id,
                "current_state": context.current_state.value,
                "total_messages": total_messages,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "preferences": context.preferences,
                "recommendations_count": len(recommendations),
                "session_duration": (context.updated_at - context.created_at).total_seconds(),
                "created_at": context.created_at.isoformat(),
                "updated_at": context.updated_at.isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting conversation summary: {e}")
            return {"error": str(e)}
    
    def determine_next_action(self, context: ConversationContext, user_message: str) -> Tuple[ConversationAction, str]:
        """Determine next conversation action based on context"""
        try:
            # Check for explicit user intents
            user_message_lower = user_message.lower()
            
            # Staff handoff requests
            if any(keyword in user_message_lower for keyword in ["staff", "help", "human", "agent"]):
                return ConversationAction.OFFER_STAFF_HANDOFF, "staff_handoff_requested"
            
            # Product recommendation requests
            if any(keyword in user_message_lower for keyword in ["show", "recommend", "suggest", "find"]):
                return ConversationAction.RECOMMEND_PRODUCTS, "ready_for_recommendation"
            
            # Check preference completeness
            key_preferences = ['category', 'occasion', 'recipient']
            has_key_preferences = sum(1 for key in key_preferences if context.preferences.get(key)) >= 1
            
            if has_key_preferences:
                return ConversationAction.RECOMMEND_PRODUCTS, "ready_for_recommendation"
            
            # Continue gathering information
            return ConversationAction.ASK_QUESTION, "gathering_preferences"
            
        except Exception as e:
            logger.error(f"Error determining next action: {e}")
            return ConversationAction.ASK_QUESTION, "gathering_preferences"
    
    def get_recommendation_confidence(self, context: ConversationContext, products: List[Dict[str, Any]]) -> str:
        """Determine recommendation confidence level"""
        try:
            if not products:
                return "low"
            
            # Check preference completeness
            filled_preferences = sum(1 for v in context.preferences.values() if v is not None)
            preference_ratio = filled_preferences / len(self.preference_keys)
            
            # Check product similarity scores
            avg_similarity = sum(p.get('similarity_score', 0) for p in products) / len(products)
            
            # Check category match
            has_category = context.preferences.get('category') is not None
            
            if preference_ratio >= 0.5 and avg_similarity >= 0.7 and has_category:
                return "high"
            elif preference_ratio >= 0.3 and avg_similarity >= 0.5:
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            logger.error(f"Error determining confidence: {e}")
            return "low"
    
    def track_product_recommendation(self, context: ConversationContext, products: List[Dict[str, Any]], 
                                   recommendation_type: str = "enhanced") -> bool:
        """Track product recommendations for analytics"""
        try:
            db = next(self.db_manager.get_db())
            
            for product in products:
                self.db_manager.track_recommendation(
                    db,
                    session_id=context.session_id,
                    product_id=product.get('id'),
                    similarity_score=product.get('similarity_score', 0),
                    confidence_level=self.get_recommendation_confidence(context, [product]),
                    recommendation_type=recommendation_type
                )
            
            # Update last shown products
            context.last_shown_products = [p.get('id') for p in products]
            self.save_context(context)
            
            logger.info(f"Tracked {len(products)} recommendations for session {context.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking recommendations: {e}")
            return False
    
    def clear_session(self, session_id: str) -> bool:
        """Clear conversation session"""
        try:
            db = next(self.db_manager.get_db())
            
            # End session in database
            updates = {
                "ended_at": datetime.utcnow(),
                "is_active": False
            }
            
            self.db_manager.update_session(db, session_id, updates)
            
            # Log analytics event
            self.db_manager.log_analytics_event(
                db, session_id, "session_ended",
                {"timestamp": datetime.utcnow().isoformat()}
            )
            
            logger.info(f"Cleared session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing session {session_id}: {e}")
            return False
    
    def get_session_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get detailed session analytics"""
        try:
            db = next(self.db_manager.get_db())
            
            # Get analytics events
            events = db.query(self.db_manager.ConversationAnalytics).filter(
                self.db_manager.ConversationAnalytics.session_id == session_id
            ).all()
            
            analytics = {
                "session_id": session_id,
                "total_events": len(events),
                "events": [
                    {
                        "event_type": event.event_type,
                        "event_data": event.event_data,
                        "timestamp": event.timestamp.isoformat()
                    }
                    for event in events
                ],
                "event_types": {}
            }
            
            # Count event types
            for event in events:
                if event.event_type not in analytics["event_types"]:
                    analytics["event_types"][event.event_type] = 0
                analytics["event_types"][event.event_type] += 1
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting session analytics: {e}")
            return {"error": str(e)}

# Global conversation engine instance
conversation_engine = None

def get_conversation_engine() -> EnhancedConversationEngine:
    """Get or create global conversation engine instance"""
    global conversation_engine
    if conversation_engine is None:
        conversation_engine = EnhancedConversationEngine()
    return conversation_engine

if __name__ == "__main__":
    # Test the enhanced conversation engine
    print("Testing Enhanced Conversation Engine...")
    
    try:
        engine = get_conversation_engine()
        
        # Test context creation
        context = engine.get_or_create_context("test_session_123")
        print(f"✅ Created context for session: {context.session_id}")
        
        # Test adding message
        engine.add_message_to_context(context, "user", "Hello, I'm looking for a ring")
        print("✅ Added message to context")
        
        # Test preference updates
        engine.update_preferences(context, {"category": "ring", "budget_max": 1000})
        print("✅ Updated preferences")
        
        # Test conversation summary
        summary = engine.get_conversation_summary(context)
        print(f"✅ Generated conversation summary: {summary}")
        
        # Test clearing session
        engine.clear_session("test_session_123")
        print("✅ Cleared test session")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()