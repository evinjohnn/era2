# Enhanced Retail AI Assistant with PostgreSQL and Advanced Features
# This is the upgraded version with PostgreSQL database and enhanced conversation engine

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError, field_validator

from groq import Groq
from dotenv import load_dotenv

# Import enhanced components
try:
    from database import get_database_manager, init_database, ProductResponse
    from conversation_engine import get_conversation_engine, ConversationResponse
    from analytics import get_analytics_engine, MetricPeriod
    from staff_dashboard import create_staff_dashboard_routes
    from vector_db import get_vector_database, initialize_vector_database_with_products
    from rag_system import get_rag_system
    from cache import get_redis_client, is_redis_available
    ENHANCED_FEATURES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Enhanced features not available: {e}")
    ENHANCED_FEATURES_AVAILABLE = False

# Configuration
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)s] - %(message)s')

# Groq Client Initialization
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SELECTED_GROQ_MODEL = os.environ.get("SELECTED_GROQ_MODEL", "llama3-70b-8192")

client: Optional[Groq] = None
if not GROQ_API_KEY:
    logging.error("CRITICAL ERROR: GROQ_API_KEY not found. LLM features will be non-functional.")
else:
    try:
        client = Groq(api_key=GROQ_API_KEY)
        logging.info(f"Groq client initialized. Attempting to use model: {SELECTED_GROQ_MODEL}")
    except Exception as e:
        logging.error(f"Error initializing Groq client: {e}")
        client = None

# Pydantic Models for API
class UserInput(BaseModel):
    session_id: Optional[str] = None
    message: str

class BotResponse(BaseModel):
    session_id: str
    reply: str
    products: Optional[List[Dict[str, Any]]] = None
    current_state: str
    next_action_suggestion: str
    action_buttons: Optional[List[Dict[str, str]]] = None
    end_conversation: bool = False
    confidence_score: str = "medium"
    metadata: Optional[Dict[str, Any]] = None

class NewSessionRequest(BaseModel):
    session_id: Optional[str] = None

# Global instances
db_manager = None
conversation_engine = None
analytics_engine = None
vector_db_instance = None
rag_system_instance = None
redis_client = None

# FastAPI app
app = FastAPI(title="Enhanced Retail AI Assistant API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the index.html for the root URL
@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

@app.on_event("startup")
async def startup_event():
    """Initialize all enhanced components on startup"""
    global db_manager, conversation_engine, analytics_engine
    global vector_db_instance, rag_system_instance, redis_client
    
    logging.info("Starting Enhanced Retail AI Assistant...")
    
    if ENHANCED_FEATURES_AVAILABLE:
        try:
            # Initialize database
            logging.info("Initializing PostgreSQL database...")
            db_manager = get_database_manager()
            if init_database():
                logging.info("✅ PostgreSQL database initialized successfully")
            else:
                logging.error("❌ PostgreSQL database initialization failed")
            
            # Initialize conversation engine
            logging.info("Initializing enhanced conversation engine...")
            conversation_engine = get_conversation_engine()
            logging.info("✅ Enhanced conversation engine initialized")
            
            # Initialize analytics engine
            logging.info("Initializing analytics engine...")
            analytics_engine = get_analytics_engine()
            logging.info("✅ Analytics engine initialized")
            
            # Initialize Redis client
            logging.info("Initializing Redis client...")
            redis_client = get_redis_client()
            if redis_client and redis_client.is_connected():
                logging.info("✅ Redis client initialized successfully")
            else:
                logging.warning("⚠️ Redis client failed to connect - using database fallback")
            
            # Initialize vector database
            logging.info("Initializing vector database...")
            # Load products from database instead of JSON
            try:
                db = next(db_manager.get_db())
                products = db_manager.get_products(db, limit=1000)
                
                if products:
                    # Convert to dict format for vector DB
                    products_dict = [
                        {
                            "id": p.id,
                            "name": p.name,
                            "category": p.category,
                            "price": p.price,
                            "metal": p.metal,
                            "gemstones": p.gemstones,
                            "design_type": p.design_type,
                            "style_tags": p.style_tags,
                            "occasion_tags": p.occasion_tags,
                            "recipient_tags": p.recipient_tags,
                            "description": p.description
                        }
                        for p in products
                    ]
                    
                    vector_db_instance = initialize_vector_database_with_products(products_dict)
                    logging.info(f"✅ Vector database initialized with {len(products_dict)} products")
                    
                    # Initialize RAG system
                    rag_system_instance = get_rag_system()
                    logging.info("✅ RAG system initialized successfully")
                else:
                    logging.warning("⚠️ No products found in database for vector initialization")
                    
            except Exception as e:
                logging.error(f"❌ Error initializing vector database: {e}")
                vector_db_instance = None
                rag_system_instance = None
            
            # Create staff dashboard routes
            create_staff_dashboard_routes(app)
            logging.info("✅ Staff dashboard routes created")
            
        except Exception as e:
            logging.error(f"❌ Error during enhanced startup: {e}")
            import traceback
            traceback.print_exc()
    else:
        logging.error("❌ Enhanced features not available - running in fallback mode")

def get_llm_structured_response(session_id: str, user_message: str) -> Tuple[str, Dict[str, Any]]:
    """Get structured response from LLM using enhanced conversation engine"""
    default_error_response = {
        "current_conversational_state": "error_state",
        "next_action": "offer_staff_handoff",
        "missing_parameter_for_current_state": None,
        "confidence_score": "low",
    }
    
    if not client:
        logging.error("LLM client not initialized.")
        return "I'm having technical difficulties. Please ask staff for help.", {**default_error_response, "error": "LLM_CLIENT_NOT_INITIALIZED"}
    
    try:
        # Get conversation context
        context = conversation_engine.get_or_create_context(session_id)
        
        # Add user message to context
        conversation_engine.add_message_to_context(context, "user", user_message)
        
        # Build conversation history for LLM
        messages = [
            {"role": "system", "content": get_enhanced_system_prompt(context.preferences)}
        ]
        
        # Add recent conversation history
        for msg in context.conversation_history[-5:]:  # Last 5 messages
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        messages.append({"role": "user", "content": user_message})
        
        # Call LLM
        logging.info(f"Sending request to Groq for session {session_id} (model: {SELECTED_GROQ_MODEL})")
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=SELECTED_GROQ_MODEL,
            temperature=0.3,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        
        response_content = chat_completion.choices[0].message.content.strip()
        logging.info(f"LLM raw response for session {session_id}: {response_content[:600]}...")
        
        # Parse response
        parsed_output = json.loads(response_content)
        dialogue_reply = parsed_output.get("dialogue_response", "I'm here to help you find the perfect jewelry.")
        
        # Extract and update preferences
        extracted_prefs = parsed_output.get("extracted_preferences", {})
        conversation_engine.update_preferences(context, extracted_prefs)
        
        # Add assistant message to context
        conversation_engine.add_message_to_context(context, "assistant", dialogue_reply, parsed_output)
        
        # Save context
        conversation_engine.save_context(context)
        
        return dialogue_reply, {
            "current_conversational_state": parsed_output.get("current_conversational_state", "gathering_preferences"),
            "next_action": parsed_output.get("next_action", "ask_question"),
            "missing_parameter_for_current_state": parsed_output.get("missing_parameter_for_current_state"),
            "confidence_score": parsed_output.get("confidence_score", "medium"),
            "extracted_preferences": extracted_prefs
        }
        
    except Exception as e:
        logging.error(f"Error in LLM processing for session {session_id}: {e}")
        error_reply = "I'm experiencing a technical difficulty right now. Please try again in a moment."
        
        # Still try to save the user message
        try:
            context = conversation_engine.get_or_create_context(session_id)
            conversation_engine.add_message_to_context(context, "user", user_message)
            conversation_engine.add_message_to_context(context, "assistant", error_reply)
            conversation_engine.save_context(context)
        except:
            pass
        
        return error_reply, {**default_error_response, "error": "LLM_PROCESSING_ERROR"}

def get_enhanced_system_prompt(preferences: Dict[str, Any]) -> str:
    """Get enhanced system prompt with current preferences"""
    preferences_json = json.dumps(preferences, indent=2)
    
    return f"""
SYSTEM PROMPT: ESTROTECH AI ASSISTANT - LUXURY JEWELLERY SALESPERSON (Enhanced V2)
You are EstroTech AI Assistant, a highly intelligent, empathetic, and efficient digital salesperson in a luxury jewellery store. You have access to a comprehensive PostgreSQL database and advanced conversation tracking.

**Enhanced Capabilities:**
1. **Advanced Memory**: You have persistent conversation memory across sessions
2. **Database Access**: Real-time access to product catalog via PostgreSQL
3. **Analytics Tracking**: Your interactions are tracked for continuous improvement
4. **Vector Search**: Enhanced product matching using semantic search

**Current Known Parameters (from persistent session):**
{preferences_json}

**Core Principles:**
1. **Empathy & Professionalism**: Maintain a warm, friendly, and professional tone
2. **Context-Aware & Efficient**: Use conversation history and preferences effectively
3. **Proactive Product Focus**: Recommend products based on comprehensive understanding
4. **Enhanced Recommendations**: Leverage semantic search for better matches

**Conversation States:**
- initial_greeting: Start of conversation
- identifying_purpose: Collect occasion, recipient
- collecting_product_type: Collect category (CRITICAL)
- gathering_preferences: Collect metal, design_type, style, budget_max, gemstone
- ready_for_recommendation: Category known + 1-2 other preferences
- refining_recommendation: User feedback on shown items
- staff_handoff_requested: User asks for staff
- error_state: Error occurred

**Output Format (JSON):**
{{
  "dialogue_response": "The natural language conversational reply to the user.",
  "extracted_preferences": {{
    "occasion": "string or null", "recipient": "string or null", "category": "string or null",
    "metal": "string or null", "design_type": "string or null", "style": "string or null",
    "budget_max": "number or null", "gemstone": "string or null"
  }},
  "current_conversational_state": "string from defined states",
  "next_action": "ask_question" OR "recommend_products" OR "offer_staff_handoff",
  "missing_parameter_for_current_state": "string or null",
  "confidence_score": "high" OR "medium" OR "low"
}}

**Enhanced Features:**
- Conversation history is automatically maintained
- Product recommendations use advanced semantic matching
- All interactions are logged for analytics
- Session state persists across page refreshes
"""

@app.post("/chat", response_model=BotResponse)
async def enhanced_chat_endpoint(user_input: UserInput, background_tasks: BackgroundTasks):
    """Enhanced chat endpoint with PostgreSQL and conversation engine"""
    try:
        # Get or create session
        session_id = user_input.session_id or str(uuid.uuid4())
        user_message = user_input.message.strip()
        
        logging.info(f"Enhanced chat request - Session: {session_id}, Message: '{user_message}'")
        
        # Initialize response variables
        bot_reply_text = "Let me help you find the perfect jewelry."
        products_to_show = None
        action_buttons = None
        end_conversation_flag = False
        current_state = "gathering_preferences"
        next_action = "ask_question"
        confidence_score = "medium"
        
        # Handle special commands
        if user_message.lower() == "hi_ai_assistant":
            bot_reply_text = "Welcome to EstroTech Jewellery! I'm your enhanced AI assistant with advanced memory and personalized recommendations. How can I help you find something beautiful today?"
            current_state = "identifying_purpose"
            
        elif user_message.lower() == "request_staff_assistance_dialogue":
            bot_reply_text = "I'll connect you with a staff member right away. They'll have access to our full conversation history to assist you better."
            end_conversation_flag = True
            current_state = "staff_handoff_requested"
            next_action = "offer_staff_handoff"
            
            # Log staff handoff request
            background_tasks.add_task(log_staff_handoff, session_id)
            
        elif user_message.lower() == "adjust_preferences_dialogue":
            # Clear preferences but keep conversation history
            if conversation_engine:
                context = conversation_engine.get_or_create_context(session_id)
                context.preferences = {key: None for key in conversation_engine.preference_keys}
                conversation_engine.save_context(context)
            
            bot_reply_text = "I've cleared your preferences. What would you like to look for now?"
            current_state = "gathering_preferences"
            
        elif user_message.lower().startswith("item_details:"):
            # Handle item details request
            product_id = user_message.lower().replace("item_details:", "").strip()
            bot_reply_text, products_to_show = await handle_item_details(product_id)
            current_state = "refining_recommendation"
            
        else:
            # Process with LLM
            dialogue_reply, llm_data = get_llm_structured_response(session_id, user_message)
            bot_reply_text = dialogue_reply
            current_state = llm_data.get("current_conversational_state", "gathering_preferences")
            next_action = llm_data.get("next_action", "ask_question")
            confidence_score = llm_data.get("confidence_score", "medium")
        
        # Get products if recommending
        if next_action == "recommend_products" and conversation_engine:
            context = conversation_engine.get_or_create_context(session_id)
            products_to_show = await get_enhanced_product_recommendations(context)
            
            if products_to_show:
                # Track recommendations
                conversation_engine.track_product_recommendation(context, products_to_show, "enhanced")
        
        # Generate action buttons
        action_buttons = generate_action_buttons(current_state, products_to_show)
        
        # Log analytics in background
        background_tasks.add_task(log_conversation_analytics, session_id, user_message, bot_reply_text, current_state)
        
        return BotResponse(
            session_id=session_id,
            reply=bot_reply_text,
            products=products_to_show,
            current_state=current_state,
            next_action_suggestion=next_action,
            action_buttons=action_buttons,
            end_conversation=end_conversation_flag,
            confidence_score=confidence_score,
            metadata={
                "enhanced_mode": True,
                "database_enabled": True,
                "conversation_tracking": True
            }
        )
        
    except Exception as e:
        logging.error(f"Error in enhanced chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        
        return BotResponse(
            session_id=session_id or str(uuid.uuid4()),
            reply="I'm experiencing technical difficulties. Please try again or contact staff for assistance.",
            current_state="error_state",
            next_action_suggestion="offer_staff_handoff",
            end_conversation=False,
            confidence_score="low",
            metadata={"error": str(e)}
        )

async def get_enhanced_product_recommendations(context) -> Optional[List[Dict[str, Any]]]:
    """Get product recommendations using enhanced features"""
    try:
        if not rag_system_instance or not context.preferences:
            return None
        
        # Create query from preferences
        query_parts = []
        if context.preferences.get('category'):
            query_parts.append(context.preferences['category'])
        if context.preferences.get('occasion'):
            query_parts.append(f"for {context.preferences['occasion']}")
        if context.preferences.get('recipient'):
            query_parts.append(f"for {context.preferences['recipient']}")
        if context.preferences.get('style'):
            query_parts.append(context.preferences['style'])
        
        query = " ".join(query_parts) if query_parts else "jewelry recommendations"
        
        # Get recommendations from RAG system
        products = rag_system_instance.retrieve_relevant_products(
            query, context.preferences, top_k=5
        )
        
        return products
        
    except Exception as e:
        logging.error(f"Error getting enhanced recommendations: {e}")
        return None

async def handle_item_details(product_id: str) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
    """Handle item details request"""
    try:
        if not db_manager:
            return "Product details are not available right now.", None
        
        db = next(db_manager.get_db())
        product = db_manager.get_product_by_id(db, product_id)
        
        if product:
            details = f"Here are the details for {product.name}:\n\n"
            details += f"• Price: ${product.price:.2f}\n"
            details += f"• Material: {product.metal}\n"
            details += f"• Design: {product.design_type}\n"
            
            if product.gemstones and product.gemstones != ['none']:
                details += f"• Gemstones: {', '.join(product.gemstones)}\n"
            
            if product.style_tags:
                details += f"• Style: {', '.join(product.style_tags)}\n"
            
            if product.occasion_tags:
                details += f"• Perfect for: {', '.join(product.occasion_tags)}\n"
            
            if product.description:
                details += f"\n{product.description}"
            
            return details, None
        else:
            return "I couldn't find details for that specific item. Would you like to see similar products?", None
            
    except Exception as e:
        logging.error(f"Error handling item details: {e}")
        return "I'm having trouble accessing product details right now.", None

def generate_action_buttons(current_state: str, products: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, str]]]:
    """Generate contextual action buttons"""
    buttons = []
    
    if current_state == "gathering_preferences":
        buttons.extend([
            {"label": "Show me rings", "value": "show me rings"},
            {"label": "Looking for a gift", "value": "I'm looking for a gift"},
            {"label": "Special occasion", "value": "This is for a special occasion"}
        ])
    
    elif current_state == "ready_for_recommendation" or products:
        buttons.extend([
            {"label": "Show more options", "value": "show me more options"},
            {"label": "Adjust preferences", "value": "adjust_preferences_dialogue"},
            {"label": "Talk to staff", "value": "request_staff_assistance_dialogue"}
        ])
        
        if products and len(products) > 0:
            buttons.append({"label": f"More about {products[0].get('name', 'item')}", "value": f"item_details:{products[0].get('id')}"})
    
    elif current_state == "refining_recommendation":
        buttons.extend([
            {"label": "See similar items", "value": "show me similar items"},
            {"label": "Different style", "value": "show me different styles"},
            {"label": "Talk to staff", "value": "request_staff_assistance_dialogue"}
        ])
    
    return buttons if buttons else None

async def log_conversation_analytics(session_id: str, user_message: str, bot_reply: str, state: str):
    """Log conversation analytics in background"""
    try:
        if analytics_engine:
            # This would be implemented to log detailed analytics
            pass
    except Exception as e:
        logging.error(f"Error logging analytics: {e}")

async def log_staff_handoff(session_id: str):
    """Log staff handoff request"""
    try:
        if conversation_engine:
            conversation_engine.clear_session(session_id)
        logging.info(f"Staff handoff logged for session {session_id}")
    except Exception as e:
        logging.error(f"Error logging staff handoff: {e}")

@app.post("/new-session")
async def new_session_endpoint(request: NewSessionRequest):
    """Enhanced new session endpoint"""
    try:
        session_id = request.session_id
        
        if session_id and conversation_engine:
            # Clear the session properly
            success = conversation_engine.clear_session(session_id)
            
            if success:
                return JSONResponse(content={
                    "status": "cleared",
                    "session_id": session_id,
                    "message": "Session cleared successfully"
                })
            else:
                return JSONResponse(content={
                    "status": "not_found",
                    "session_id": session_id,
                    "message": "Session not found or already cleared"
                })
        
        return JSONResponse(content={
            "status": "no_session",
            "message": "No session ID provided"
        })
        
    except Exception as e:
        logging.error(f"Error in new session endpoint: {e}")
        return JSONResponse(content={
            "status": "error",
            "error": str(e)
        }, status_code=500)

# Enhanced Admin Endpoints
@app.get("/admin/enhanced-stats")
async def get_enhanced_system_stats():
    """Get enhanced system statistics"""
    try:
        stats = {
            "system_status": "enhanced_with_postgresql",
            "database": "postgresql",
            "conversation_engine": "enhanced",
            "analytics": "enabled",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Database stats
        if db_manager:
            try:
                db = next(db_manager.get_db())
                product_count = len(db_manager.get_products(db, limit=10000))
                
                # Import the models here to access them
                from database import ConversationSession, ConversationMessage
                session_count = db.query(ConversationSession).count()
                message_count = db.query(ConversationMessage).count()
                
                stats["database_stats"] = {
                    "products": product_count,
                    "sessions": session_count,
                    "messages": message_count,
                    "status": "connected"
                }
            except Exception as e:
                stats["database_stats"] = {"status": "error", "error": str(e)}
        
        # Vector database stats
        if vector_db_instance:
            try:
                vector_stats = vector_db_instance.get_collection_stats()
                stats["vector_database"] = vector_stats
            except Exception as e:
                stats["vector_database"] = {"status": "error", "error": str(e)}
        
        # Analytics stats
        if analytics_engine:
            try:
                conv_metrics = analytics_engine.get_conversation_metrics(MetricPeriod.LAST_DAY)
                stats["analytics"] = {
                    "total_sessions_today": conv_metrics.total_sessions,
                    "active_sessions": conv_metrics.active_sessions,
                    "average_session_duration": conv_metrics.average_session_duration
                }
            except Exception as e:
                stats["analytics"] = {"status": "error", "error": str(e)}
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        logging.error(f"Error getting enhanced stats: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/admin/conversation-metrics")
async def get_conversation_metrics(period: str = "last_day"):
    """Get conversation metrics"""
    try:
        if not analytics_engine:
            return JSONResponse(content={"error": "Analytics engine not available"}, status_code=503)
        
        period_enum = MetricPeriod(period)
        metrics = analytics_engine.get_conversation_metrics(period_enum)
        
        return JSONResponse(content={
            "metrics": {
                "total_sessions": metrics.total_sessions,
                "active_sessions": metrics.active_sessions,
                "completed_sessions": metrics.completed_sessions,
                "average_session_duration": metrics.average_session_duration,
                "total_messages": metrics.total_messages,
                "average_messages_per_session": metrics.average_messages_per_session,
                "staff_handoffs": metrics.staff_handoffs,
                "handoff_rate": metrics.handoff_rate
            },
            "period": metrics.period,
            "start_date": metrics.start_date.isoformat(),
            "end_date": metrics.end_date.isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error getting conversation metrics: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Keep compatibility with existing admin endpoints
@app.get("/admin/vector-stats")
async def get_vector_stats():
    """Get vector database statistics (compatibility)"""
    return await get_enhanced_system_stats()

@app.get("/admin/test-vector-search")
async def test_vector_search(query: str = "elegant engagement ring"):
    """Test vector search functionality"""
    try:
        if not rag_system_instance:
            return JSONResponse(content={
                "error": "RAG system not available",
                "query": query,
                "results_count": 0,
                "results": []
            })
        
        # Test search
        results = rag_system_instance.retrieve_relevant_products(
            query, {}, top_k=5
        )
        
        return JSONResponse(content={
            "query": query,
            "results_count": len(results),
            "results": results,
            "system_status": "enhanced_rag_active"
        })
        
    except Exception as e:
        logging.error(f"Error testing vector search: {e}")
        return JSONResponse(content={
            "error": str(e),
            "query": query,
            "results_count": 0,
            "results": []
        }, status_code=500)

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8001))
    
    print("🚀 Starting Enhanced Retail AI Assistant...")
    print(f"📊 Features: PostgreSQL Database, Enhanced Conversations, Analytics, Staff Dashboard")
    print(f"🌐 Server will run at: http://localhost:{port}")
    print(f"📋 Staff Dashboard at: http://localhost:{port}/staff/dashboard")
    
    uvicorn.run(app, host="0.0.0.0", port=port)