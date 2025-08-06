# retail_ai_assistant_unified.py - Enhanced with Vector Database and RAG

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError, field_validator

from groq import Groq # type: ignore
from dotenv import load_dotenv

# Import enhanced components
try:
    from vector_db import get_vector_database, initialize_vector_database_with_products
    from rag_system import get_rag_system
    ENHANCED_FEATURES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Enhanced features not available: {e}")
    ENHANCED_FEATURES_AVAILABLE = False

# Import Redis cache
try:
    from cache import get_redis_client, is_redis_available
    REDIS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Redis not available: {e}")
    REDIS_AVAILABLE = False

# --- Basic Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)s] - %(message)s')

# --- Groq Client Initialization ---
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

# --- Pydantic Models for API and LLM Data ---
class ProductDetail(BaseModel):
    id: str
    name: str
    category: str
    image_url: str
    price: float
    metal: str
    gemstones: List[str] = Field(default_factory=list)
    design_type: str 
    style_tags: List[str] = Field(default_factory=list)
    occasion_tags: List[str] = Field(default_factory=list)
    recipient_tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    # Enhanced fields for vector search
    similarity_score: Optional[float] = None
    confidence: Optional[str] = None

class ExtractedPreferences(BaseModel):
    occasion: Optional[str] = None
    recipient: Optional[str] = None
    category: Optional[str] = None
    metal: Optional[str] = None
    design_type: Optional[str] = None
    style: Optional[str] = None
    budget_max: Optional[float] = None
    gemstone: Optional[str] = None

class LLMStructuredOutput(BaseModel):
    dialogue_response: str = Field(..., description="The natural language conversational reply to the user.")
    extracted_preferences: ExtractedPreferences
    current_conversational_state: str = Field(..., description="The current stage of the conversation.")
    next_action: str = Field(..., description="The next action to take.")
    missing_parameter_for_current_state: Optional[str] = Field(None, description="If action is ask_question, the critical missing parameter.")
    confidence_score: str = Field(..., description="Confidence in extraction and action.")

    @field_validator('next_action')
    @classmethod
    def validate_next_action(cls, value: str) -> str:
        allowed_actions = ["ask_question", "recommend_products", "offer_staff_handoff"]
        if value not in allowed_actions:
            raise ValueError(f"next_action must be one of {allowed_actions}, got {value}")
        return value

    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_score(cls, value: str) -> str:
        allowed_scores = ["high", "medium", "low"]
        if value not in allowed_scores:
            raise ValueError(f"confidence_score must be one of {allowed_scores}, got {value}")
        return value

class UserInput(BaseModel):
    session_id: Optional[str] = None
    message: str

class BotResponse(BaseModel):
    session_id: str
    reply: str
    products: Optional[List[ProductDetail]] = None
    current_state: str
    next_action_suggestion: str
    action_buttons: Optional[List[Dict[str, str]]] = None
    end_conversation: bool = False

SESSIONS_STORE: Dict[str, Dict[str, Any]] = {}
CONVERSATION_HISTORY_LOG: List[Dict[str, Any]] = []
PRODUCT_CATALOG_DB: List[Dict[str, Any]] = []
ALL_PREFERENCE_KEYS = list(ExtractedPreferences.model_fields.keys())

# Initialize Redis client
redis_client = None
if REDIS_AVAILABLE:
    redis_client = get_redis_client()
    if redis_client.is_connected():
        logging.info("Redis client initialized successfully")
    else:
        logging.warning("Redis client failed to connect - using in-memory storage")
        redis_client = None
else:
    logging.warning("Redis not available - using in-memory storage")

app = FastAPI(title="EstroTech Retail AI Assistant API")

# Mount the static directory to serve CSS, JS, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the index.html for the root URL
@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

def load_products_from_json(filepath="product_catalog_large.json"):
    global PRODUCT_CATALOG_DB
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            PRODUCT_CATALOG_DB = json.load(f)
        logging.info(f"Successfully loaded {len(PRODUCT_CATALOG_DB)} products from {filepath}")
        if not PRODUCT_CATALOG_DB:
            logging.warning(f"Product catalog file {filepath} was empty.")
    except FileNotFoundError:
        logging.error(f"Product catalog file not found: {filepath}. PRODUCT_CATALOG_DB will be empty.")
        PRODUCT_CATALOG_DB = []
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from product catalog: {filepath}. PRODUCT_CATALOG_DB will be empty.")
        PRODUCT_CATALOG_DB = []
    except Exception as e:
        logging.error(f"An unexpected error occurred loading product catalog: {e}. PRODUCT_CATALOG_DB will be empty.")
        PRODUCT_CATALOG_DB = []

class JewelleryRecommender:
    def __init__(self, product_catalog: List[Dict[str, Any]]):
        self.product_catalog = product_catalog
        if not self.product_catalog:
            logging.warning("JewelleryRecommender initialized with an empty product catalog!")

    def _calculate_match_score(self, product: Dict[str, Any], preferences: Dict[str, Any]) -> float:
        score = 0.0
        matched_any_preference = False
        category_pref = preferences.get("category")
        if category_pref:
            if product.get("category","").lower() == category_pref.lower():
                score += 100
                matched_any_preference = True
            else:
                return 0.0
        if category_pref and len([v for k,v in preferences.items() if v and k != "category" and k != "user_query_was_generic_show_all"]) == 0: # Check if only category (and our flag) is set
             if product.get("category","").lower() == category_pref.lower():
                 return 50.0 

        metal_pref = preferences.get("metal")
        if metal_pref and metal_pref.lower() in product.get("metal","").lower():
            score += 20; matched_any_preference = True
        
        gemstone_pref = preferences.get("gemstone")
        if gemstone_pref and gemstone_pref.lower() != "none":
            if gemstone_pref.lower() in [g.lower() for g in product.get("gemstones", [])]:
                score += 30; matched_any_preference = True
        elif gemstone_pref and gemstone_pref.lower() == "none":
            if "none" in [g.lower() for g in product.get("gemstones", ["none"])]:
                 score += 10; matched_any_preference = True
        
        style_pref = preferences.get("style")
        if style_pref and style_pref.lower() in [s.lower() for s in product.get("style_tags",[])]:
            score += 15; matched_any_preference = True
        
        design_type_pref = preferences.get("design_type")
        if design_type_pref and product.get("design_type","").lower() == design_type_pref.lower():
            score += 10; matched_any_preference = True

        occasion_pref = preferences.get("occasion")
        if occasion_pref and occasion_pref.lower() in [o.lower() for o in product.get("occasion_tags",[])]:
            score += 10; matched_any_preference = True
        
        recipient_pref = preferences.get("recipient")
        if recipient_pref and recipient_pref.lower() in [r.lower() for r in product.get("recipient_tags",[])]:
            score += 5; matched_any_preference = True

        budget_max_pref = preferences.get("budget_max")
        if budget_max_pref is not None:
            try:
                budget_max = float(budget_max_pref)
                price = product.get("price", float('inf'))
                if price <= budget_max:
                    score += 20 
                    matched_any_preference = True
                    if price >= budget_max * 0.70: score += 5
            except (ValueError, TypeError): pass
        
        if not preferences or (not matched_any_preference and not (category_pref and len([v for k,v in preferences.items() if v and k != "category" and k != "user_query_was_generic_show_all"]) == 0)):
            return 0.0
        return score

    def recommend_products(self, preferences: Dict[str, Any], top_n: int = 5) -> List[Dict[str, Any]]:
        if not self.product_catalog:
            logging.warning("Recommender: Attempting to recommend from an empty catalog.")
            return []
        
        is_broad_category_search = preferences.get("user_query_was_generic_show_all", False)
        category_pref = preferences.get("category")

        if is_broad_category_search and category_pref:
            logging.info(f"Recommender: Performing broad search for category '{category_pref}'.")
            results = [p for p in self.product_catalog if p.get("category","").lower() == category_pref.lower()]
            results.sort(key=lambda p: p.get("price", 0))
            logging.info(f"Recommender found {len(results)} products for broad category search. Returning top {top_n}.")
            return results[:top_n]

        scored_products = []
        for product in self.product_catalog:
            budget_max_pref = preferences.get("budget_max")
            if budget_max_pref is not None:
                try:
                    if product.get("price", float('inf')) > float(budget_max_pref):
                        continue
                except (ValueError, TypeError): pass
            if category_pref and product.get("category","").lower() != category_pref.lower():
                continue
            score = self._calculate_match_score(product, preferences)
            if score > 0:
                scored_products.append({"product": product, "score": score})
        scored_products.sort(key=lambda x: (x["score"], -x["product"].get("price", float('inf'))), reverse=True)
        logging.info(f"Recommender found {len(scored_products)} potential matches based on score. Returning top {top_n}.")
        return [sp["product"] for sp in scored_products[:top_n]]

jewellery_recommender_instance: Optional[JewelleryRecommender] = None
vector_db_instance = None
rag_system_instance = None

@app.on_event("startup")
async def startup_event():
    global jewellery_recommender_instance, vector_db_instance, rag_system_instance
    
    # Load products from JSON
    load_products_from_json()
    
    if PRODUCT_CATALOG_DB:
        # Initialize legacy recommender
        jewellery_recommender_instance = JewelleryRecommender(PRODUCT_CATALOG_DB)
        logging.info("JewelleryRecommender initialized with product catalog.")
        
        # Initialize vector database with products if enhanced features available
        if ENHANCED_FEATURES_AVAILABLE:
            try:
                vector_db_instance = initialize_vector_database_with_products(PRODUCT_CATALOG_DB)
                logging.info("Vector database initialized successfully.")
                
                # Initialize RAG system
                rag_system_instance = get_rag_system()
                logging.info("RAG system initialized successfully.")
                
            except Exception as e:
                logging.error(f"Error initializing vector database or RAG system: {e}")
                logging.info("Enhanced features disabled, using legacy recommender only.")
                vector_db_instance = None
                rag_system_instance = None
        else:
            logging.info("Enhanced features not available, using legacy recommender only.")
    else:
        logging.critical("PRODUCT CATALOG IS EMPTY. Recommender will not function.")

def _get_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

def log_to_conversation_history(session_id: str, role: str, content: str, preferences_at_turn: Optional[Dict] = None):
    """Log conversation to history - Redis or in-memory fallback"""
    if redis_client and redis_client.is_connected():
        # Use Redis
        redis_client.add_to_conversation_history(session_id, role, content, preferences_at_turn)
    else:
        # Fallback to in-memory
        CONVERSATION_HISTORY_LOG.append({
            "session_id": session_id, "timestamp": _get_timestamp(),
            "role": role, "content": content,
            "preferences_at_turn": preferences_at_turn.copy() if preferences_at_turn else {}
        })
    logging.debug(f"History Logged for {session_id}: {role} - {content[:50]}...")

def get_recent_conversation_history(session_id: str, limit: int = 5) -> List[Dict[str, str]]:
    """Get recent conversation history - Redis or in-memory fallback"""
    if redis_client and redis_client.is_connected():
        # Use Redis
        messages = redis_client.get_conversation_history(session_id, limit)
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]
    else:
        # Fallback to in-memory
        session_messages = [msg for msg in CONVERSATION_HISTORY_LOG if msg["session_id"] == session_id]
        return [{"role": msg["role"], "content": msg["content"]} for msg in session_messages[-limit:]]

def get_session_data(session_id: str) -> Dict[str, Any]:
    """Get session data - Redis or in-memory fallback"""
    if redis_client and redis_client.is_connected():
        # Use Redis
        data = redis_client.get_session(session_id)
        return data.copy() if data else {}
    else:
        # Fallback to in-memory
        return SESSIONS_STORE.get(session_id, {}).copy()

def update_session_preferences(session_id: str, new_prefs_dict: Dict[str, Any]):
    """Update session preferences - Redis or in-memory fallback"""
    if redis_client and redis_client.is_connected():
        # Use Redis
        session_data = redis_client.get_session(session_id)
        if not session_data:
            session_data = {
                "current_conversational_state": "initial_greeting",
                "preferences": {key: None for key in ALL_PREFERENCE_KEYS},
                "last_shown_product_ids": []
            }
        
        current_prefs = session_data.get("preferences", {})
        for key in ALL_PREFERENCE_KEYS:
            if key in new_prefs_dict and new_prefs_dict[key] is not None and str(new_prefs_dict[key]).strip() != "" and str(new_prefs_dict[key]).lower() != "null":
                current_prefs[key] = new_prefs_dict[key]
            elif key in new_prefs_dict and (new_prefs_dict[key] is None or str(new_prefs_dict[key]).lower() == "null"):
                current_prefs[key] = None
            elif key not in current_prefs:
                current_prefs[key] = None
        
        session_data["preferences"] = current_prefs
        redis_client.set_session(session_id, session_data)
        logging.info(f"Updated preferences for session {session_id}: {current_prefs}")
    else:
        # Fallback to in-memory
        if session_id not in SESSIONS_STORE:
            SESSIONS_STORE[session_id] = {"preferences": {key: None for key in ALL_PREFERENCE_KEYS}}
        current_prefs = SESSIONS_STORE[session_id].get("preferences", {})
        for key in ALL_PREFERENCE_KEYS:
            if key in new_prefs_dict and new_prefs_dict[key] is not None and str(new_prefs_dict[key]).strip() != "" and str(new_prefs_dict[key]).lower() != "null":
                current_prefs[key] = new_prefs_dict[key]
            elif key in new_prefs_dict and (new_prefs_dict[key] is None or str(new_prefs_dict[key]).lower() == "null"):
                current_prefs[key] = None
            elif key not in current_prefs:
                current_prefs[key] = None
        SESSIONS_STORE[session_id]["preferences"] = current_prefs
        logging.info(f"Updated preferences for session {session_id}: {SESSIONS_STORE[session_id]['preferences']}")

def get_or_create_session(session_id_str: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    """Get or create session - Redis or in-memory fallback"""
    if redis_client and redis_client.is_connected():
        # Use Redis
        if session_id_str:
            session_data = redis_client.get_session(session_id_str)
            if session_data:
                return session_id_str, session_data
        
        # Create new session
        new_id = str(uuid.uuid4())
        new_session_data = {
            "current_conversational_state": "initial_greeting",
            "preferences": {key: None for key in ALL_PREFERENCE_KEYS},
            "last_shown_product_ids": []
        }
        redis_client.set_session(new_id, new_session_data)
        logging.info(f"New session created: {new_id}")
        return new_id, new_session_data
    else:
        # Fallback to in-memory
        if not session_id_str or session_id_str not in SESSIONS_STORE:
            new_id = str(uuid.uuid4())
            SESSIONS_STORE[new_id] = {
                "current_conversational_state": "initial_greeting",
                "preferences": {key: None for key in ALL_PREFERENCE_KEYS},
                "last_shown_product_ids": []
            }
            logging.info(f"New session created: {new_id}")
            return new_id, SESSIONS_STORE[new_id]
        return session_id_str, SESSIONS_STORE[session_id_str]

def get_system_prompt_v4(current_preferences_json_string: str) -> str:
    return f"""
SYSTEM PROMPT: ESTROTECH AI ASSISTANT - LUXURY JEWELLERY SALESPERSON (V4 - Dialogflow CX Inspired)
You are EstroTech AI Assistant, a highly intelligent, empathetic, and efficient digital salesperson in a luxury jewellery store. Your primary goal is to understand the customer's needs through natural, guided conversation, proactively offer relevant product recommendations, and seamlessly connect them to staff when needed.
**Think of the conversation as progressing through distinct 'conversational states' or 'pages', each designed to collect specific 'parameters' (preferences) to fulfill a user's request.**
**Core Principles:**
1.  **Empathy & Professionalism:** Maintain a warm, friendly, and professional tone. Always be helpful and understanding.
2.  **Context-Aware & Efficient:** Pay close attention to ALL information the user provides. Do NOT ask for information you already know or that can be inferred. Parse the user's entire input to extract ALL relevant parameters in a single turn.
3.  **Natural Flow & State Management:**
    *   Identify the `current_conversational_state` based on user input and `Current Known Parameters`.
    *   If parameters for the current state are met, determine `next_action`.
    *   If essential parameters are missing/ambiguous, identify `missing_parameter_for_current_state` and ask a targeted question. Prioritize critical missing info.
4.  **Proactive Product Focus:** Aim to recommend products. Once 'category' and 1-2 other strong preferences are known, proactively suggest items. Look for upsell/cross-sell opportunities naturally.
5.  **Handling Broad Category Requests:** If the user asks to see 'all' items of a specific category (e.g., "show me all rings"), your `next_action` should be "recommend_products". The `extracted_preferences` should primarily focus on the `category`, and other preferences should ideally be `null` or not influence filtering for this specific broad request. Your `dialogue_response` should acknowledge this broad search.
**Defined Conversational States (Pages) and their Primary Parameters:**
*   `initial_greeting`: Start of conversation.
*   `identifying_purpose`: Collect `occasion`, `recipient`.
*   `collecting_product_type`: Collect `category` (CRITICAL).
*   `gathering_preferences`: Collect `metal`, `design_type`, `style`, `budget_max`, `gemstone`.
*   `ready_for_recommendation`: 'category' known, + 1-2 other strong preferences.
*   `refining_recommendation`: User gives feedback on shown items.
*   `staff_handoff_requested`: User asks for staff.
*   `error_state`: Error occurred.
**Current Known Parameters (from previous turns, acting as session parameters):**
{current_preferences_json_string}
**Available Parameters for Extraction (Entity Types):**
- occasion, recipient, category, metal, design_type, style, budget_max (numeric, handle ranges like 'around 1500' as 1500, remove currency symbols), gemstone (e.g. "diamond", "none")
**Output Format:**
You MUST output a single, valid JSON object. `dialogue_response` is the user-facing reply.
```json
{{
  "dialogue_response": "The natural language conversational reply to the user.",
  "extracted_preferences": {{
    "occasion": "string or null", "recipient": "string or null", "category": "string or null",
    "metal": "string or null", "design_type": "string or null", "style": "string or null",
    "budget_max": "number or null", "gemstone": "string or null"
  }},
  "current_conversational_state": "string from Defined Conversational States",
  "next_action": "ask_question" OR "recommend_products" OR "offer_staff_handoff",
  "missing_parameter_for_current_state": "string (parameter name) or null",
  "confidence_score": "high" OR "medium" OR "low"
}}
Use code with caution.
Python
Ensure all JSON string values are double-quoted. budget_max is number/null.
If next_action is "recommend_products", missing_parameter_for_current_state MUST be null.
If next_action is "ask_question", missing_parameter_for_current_state MUST specify the parameter.
"""
def get_llm_structured_response(session_id: str, user_message: str) -> Tuple[str, Dict[str, Any]]:
    default_error_prefs = ExtractedPreferences().model_dump(exclude_none=True)
    default_error_response_dict = {
        "extracted_preferences": default_error_prefs,
        "current_conversational_state": "error_state",
        "next_action": "offer_staff_handoff",
        "missing_parameter_for_current_state": None,
        "confidence_score": "low",
    }
    if not client:
        logging.error("LLM client not initialized.")
        return "I'm having technical difficulties. Please ask staff for help.", {**default_error_response_dict, "error": "LLM_CLIENT_NOT_INITIALIZED"}
    current_session_data = get_session_data(session_id)
    current_preferences = current_session_data.get("preferences", {key: None for key in ALL_PREFERENCE_KEYS})
    prompt_ready_prefs = {key: current_preferences.get(key) for key in ALL_PREFERENCE_KEYS}
    conversation_history = get_recent_conversation_history(session_id, limit=5)
    system_prompt_instance = get_system_prompt_v4(json.dumps(prompt_ready_prefs))
    messages = [{"role": "system", "content": system_prompt_instance}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})
    try:
        logging.info(f"Sending request to Groq for session {session_id} (model: {SELECTED_GROQ_MODEL})")
        chat_completion = client.chat.completions.create(
            messages=messages, model=SELECTED_GROQ_MODEL,
            temperature=0.3, max_tokens=800, response_format={"type": "json_object"}
        )
        response_content = chat_completion.choices[0].message.content.strip()
        logging.info(f"LLM raw response for session {session_id}: {response_content[:600]}...")
        parsed_output_dict = json.loads(response_content)
        validated_output = LLMStructuredOutput.model_validate(parsed_output_dict)
        dialogue_reply = validated_output.dialogue_response
        extracted_prefs_this_turn = validated_output.extracted_preferences.model_dump(exclude_none=True)
        update_session_preferences(session_id, extracted_prefs_this_turn)
        log_to_conversation_history(session_id, "user", user_message, current_preferences)
        log_to_conversation_history(session_id, "assistant", dialogue_reply, get_session_data(session_id).get("preferences"))
        return dialogue_reply, validated_output.model_dump(exclude={"dialogue_response"})
    except json.JSONDecodeError as json_e:
        logging.error(f"Failed to parse JSON from LLM for session {session_id}: {response_content}. Error: {json_e}")
        error_reply = "I seem to have gotten my wires crossed. Could you please rephrase that?"
    except ValidationError as val_e:
        logging.error(f"Pydantic validation failed for LLM output (session {session_id}): {response_content}. Errors: {val_e.errors()}")
        error_reply = "I'm having a bit of trouble understanding the details. Could you try saying that a different way?"
    except Exception as e_api:
        logging.error(f"Error calling Groq API or processing response for session {session_id}: {e_api}")
        api_error_message = str(e_api).lower()
        if hasattr(e_api, 'status_code') and e_api.status_code == 401:
            error_reply = "There's an issue with accessing the AI service (Authentication Error). Please let staff know."
        elif "model_decommissioned" in api_error_message or \
             (hasattr(e_api, 'status_code') and e_api.status_code == 400 and ("model not found" in api_error_message or "model_name_not_found" in api_error_message)):
            error_reply = f"The AI model ({SELECTED_GROQ_MODEL}) is currently unavailable or not supported by your key. Please notify staff."
        else:
            error_reply = "I'm experiencing a technical difficulty right now. Please try again in a moment."
    log_to_conversation_history(session_id, "user", user_message, current_preferences)
    log_to_conversation_history(session_id, "assistant", error_reply, get_session_data(session_id).get("preferences"))
    return error_reply, {**default_error_response_dict, "error": "LLM_PROCESSING_ERROR"}

@app.post("/chat", response_model=BotResponse)
async def chat_endpoint(user_input: UserInput):
    session_id, session_data = get_or_create_session(user_input.session_id)
    user_message = user_input.message.strip()
    user_message_lower = user_message.lower()
    # Log user message to history *before* it's processed by LLM or heuristics for the current turn
    # Preferences logged here are those *before* this turn's extraction
    log_to_conversation_history(session_id, "user", user_message, session_data.get("preferences"))
    logging.info(f"--- Turn Start ---")
    logging.info(f"Session: {session_id}, App State Before Processing: {session_data.get('current_conversational_state')}")
    logging.info(f"User Message: '{user_message}'")
    logging.info(f"Preferences Before LLM/Heuristics: {session_data.get('preferences')}")
    bot_reply_text = "Let me check on that for you..."
    products_to_show_details: Optional[List[ProductDetail]] = None
    action_buttons_for_frontend: Optional[List[Dict[str, str]]] = None
    end_conversation_flag = False
    current_app_state_for_turn = session_data.get("current_conversational_state", "initial_greeting")
    llm_action_suggestion = "ask_question" 
    
    # --- FIX: Initialize llm_structured_data with a default value ---
    llm_structured_data = {}

    is_broad_category_search_heuristic = False
    category_for_broad_search = None
    # More robust keyword checking for broad search
    broad_search_triggers = ["all rings", "all necklaces", "show me rings", "just rings", 
                               "all earrings", "show me earrings", "just earrings",
                               "all bracelets", "show me bracelets", "just bracelets"]
    if any(trigger in user_message_lower for trigger in broad_search_triggers):
        if "ring" in user_message_lower: category_for_broad_search = "ring"
        elif "necklace" in user_message_lower: category_for_broad_search = "necklace"
        elif "earring" in user_message_lower: category_for_broad_search = "earrings"
        elif "bracelet" in user_message_lower: category_for_broad_search = "bracelet"
        
        if category_for_broad_search:
            is_broad_category_search_heuristic = True
    if is_broad_category_search_heuristic:
        logging.info(f"Heuristic: Broad '{category_for_broad_search}' search. Forcing recommend action.")
        prefs_for_broad_search = {key: None for key in ALL_PREFERENCE_KEYS} # Clear all first
        prefs_for_broad_search["category"] = category_for_broad_search
        prefs_for_broad_search["user_query_was_generic_show_all"] = True # Flag for recommender
        update_session_preferences(session_id, prefs_for_broad_search)
        bot_reply_text = f"Certainly! Let me show you our collection of {category_for_broad_search}s."
        llm_action_suggestion = "recommend_products"
        current_app_state_for_turn = "POST_RECOMMENDATION_FEEDBACK"
    elif user_message_lower == "talk_to_staff" or user_message_lower == "request_staff_assistance_dialogue":
        current_app_state_for_turn = "staff_handoff_requested"
        llm_action_suggestion = "offer_staff_handoff"
        bot_reply_text = "Okay, I'll get a staff member to assist you right away!"
        end_conversation_flag = True
        logging.info(f"WEBHOOK SIMULATION: Staff notified for session {session_id}. Prefs: {get_session_data(session_id).get('preferences')}")
    elif user_message_lower == "adjust_preferences_dialogue":
        temp_prefs = {key: None for key in ALL_PREFERENCE_KEYS}
        update_session_preferences(session_id, temp_prefs)
        
        # Clear last shown product IDs
        if redis_client and redis_client.is_connected():
            session_data = redis_client.get_session(session_id)
            if session_data:
                session_data["last_shown_product_ids"] = []
                redis_client.set_session(session_id, session_data)
        else:
            SESSIONS_STORE[session_id]["last_shown_product_ids"] = []
        
        dialogue_reply, llm_structured_data = get_llm_structured_response(session_id, "User wants to adjust preferences. Ask what they'd like to change or look for now.")
        bot_reply_text = dialogue_reply
        current_app_state_for_turn = llm_structured_data.get("current_conversational_state", "gathering_preferences")
        llm_action_suggestion = llm_structured_data.get("next_action", "ask_question")
    elif user_message_lower.startswith("item_details:"):
        # Handle "More About Item" requests
        product_id = user_message_lower.replace("item_details:", "").strip()
        
        # Find the product in catalog
        product_found = None
        for product in PRODUCT_CATALOG_DB:
            if product.get("id") == product_id:
                product_found = product
                break
        
        if product_found:
            # Generate detailed description
            bot_reply_text = f"Here are the details for {product_found['name']}:\n\n"
            bot_reply_text += f"• Price: ${product_found['price']:.2f}\n"
            bot_reply_text += f"• Material: {product_found['metal']}\n"
            bot_reply_text += f"• Design: {product_found['design_type']}\n"
            
            if product_found.get('gemstones') and product_found['gemstones'] != ['none']:
                bot_reply_text += f"• Gemstones: {', '.join(product_found['gemstones'])}\n"
            
            if product_found.get('style_tags'):
                bot_reply_text += f"• Style: {', '.join(product_found['style_tags'])}\n"
            
            if product_found.get('occasion_tags'):
                bot_reply_text += f"• Perfect for: {', '.join(product_found['occasion_tags'])}\n"
            
            if product_found.get('description'):
                bot_reply_text += f"\n{product_found['description']}"
                
            current_app_state_for_turn = "refining_recommendation"
            llm_action_suggestion = "ask_question"
        else:
            bot_reply_text = "I couldn't find details for that specific item. Would you like to see similar products or adjust your search?"
            current_app_state_for_turn = "gathering_preferences"
            llm_action_suggestion = "ask_question"
    elif user_message_lower == "hi_ai_assistant" and current_app_state_for_turn == "initial_greeting":
        bot_reply_text = "Welcome to EstroTech Jewellery! I'm your personal AI assistant. How can I help you find something beautiful today?"
        current_app_state_for_turn = "identifying_purpose" # LLM will likely confirm this or ask first question
        llm_action_suggestion = "ask_question" # Default for welcome
    else:
        dialogue_reply, llm_structured_data = get_llm_structured_response(session_id, user_message)
        bot_reply_text = dialogue_reply
        current_app_state_for_turn = llm_structured_data.get("current_conversational_state", "error_state")
        llm_action_suggestion = llm_structured_data.get("next_action", "offer_staff_handoff")
        if "error" in llm_structured_data:
            logging.error(f"Error from LLM service for session {session_id}: {llm_structured_data['error']}")
            if llm_action_suggestion == "offer_staff_handoff":
                 current_app_state_for_turn = "staff_handoff_requested"
    # Update session state
    if redis_client and redis_client.is_connected():
        session_data = redis_client.get_session(session_id)
        if session_data:
            session_data["current_conversational_state"] = current_app_state_for_turn
            redis_client.set_session(session_id, session_data)
    else:
        SESSIONS_STORE[session_id]["current_conversational_state"] = current_app_state_for_turn
    if llm_action_suggestion == "recommend_products":
        latest_preferences_for_filtering = get_session_data(session_id).get("preferences", {})
        logging.info(f"Attempting to recommend products with preferences: {latest_preferences_for_filtering}")
        
        # Try to use RAG system first, fallback to legacy recommender
        filtered_product_list = []
        
        if ENHANCED_FEATURES_AVAILABLE and rag_system_instance and vector_db_instance:
            try:
                # Use RAG system for enhanced recommendations
                logging.info("Using RAG system for product recommendations")
                
                # Create query from user message and preferences
                query = user_message
                if latest_preferences_for_filtering.get('category'):
                    query += f" {latest_preferences_for_filtering['category']}"
                if latest_preferences_for_filtering.get('occasion'):
                    query += f" for {latest_preferences_for_filtering['occasion']}"
                
                # Get products using RAG system
                rag_products = rag_system_instance.retrieve_relevant_products(
                    query, latest_preferences_for_filtering, top_k=5
                )
                
                # Convert to expected format
                filtered_product_list = rag_products
                
                # Log RAG performance
                if rag_products:
                    avg_score = sum(p.get('similarity_score', 0) for p in rag_products) / len(rag_products)
                    logging.info(f"RAG system found {len(rag_products)} products with avg similarity: {avg_score:.3f}")
                
            except Exception as e:
                logging.error(f"Error using RAG system: {e}")
                # Fallback to legacy recommender
                filtered_product_list = []
        
        # Fallback to legacy recommender if RAG failed or not available
        if not filtered_product_list and jewellery_recommender_instance:
            logging.info("Falling back to legacy recommender system")
            filtered_product_list = jewellery_recommender_instance.recommend_products(
                preferences=latest_preferences_for_filtering, top_n=5
            )
            
        if not filtered_product_list:
            logging.error("No product recommenders available or working!")
            bot_reply_text = "I'm having trouble accessing our product catalog right now. Please try again in a moment."
            SESSIONS_STORE[session_id]["current_conversational_state"] = "error_state"
        else:
            if filtered_product_list:
                products_to_show_details = [ProductDetail(**p) for p in filtered_product_list]
                product_ids = [p.id for p in products_to_show_details]
                
                # Update last shown products
                if redis_client and redis_client.is_connected():
                    session_data = redis_client.get_session(session_id)
                    if session_data:
                        session_data["last_shown_product_ids"] = product_ids
                        redis_client.set_session(session_id, session_data)
                else:
                    SESSIONS_STORE[session_id]["last_shown_product_ids"] = product_ids
                
                action_buttons_for_frontend = [
                    {"label": "More About Item (Select)", "value": "item_details_placeholder"},
                    {"label": "Different Options", "value": "show_different_items"},
                    {"label": "Adjust Filters", "value": "adjust_preferences_dialogue"},
                    {"label": "Chat with Staff", "value": "request_staff_assistance_dialogue"}
                ]
                
                if redis_client and redis_client.is_connected():
                    session_data = redis_client.get_session(session_id)
                    if session_data and session_data.get("current_conversational_state") != "refining_recommendation":
                        session_data["current_conversational_state"] = "POST_RECOMMENDATION_FEEDBACK"
                        redis_client.set_session(session_id, session_data)
                else:
                    if SESSIONS_STORE[session_id]["current_conversational_state"] != "refining_recommendation":
                        SESSIONS_STORE[session_id]["current_conversational_state"] = "POST_RECOMMENDATION_FEEDBACK"
            else:
                logging.warning(f"Action was 'recommend_products', but no products found for prefs: {latest_preferences_for_filtering}")
                if not "(But I couldn't find specific items right now" in bot_reply_text and not is_broad_category_search_heuristic :
                     bot_reply_text += " (However, I couldn't find items with those exact details right now. Want to try adjusting the search?)"
                elif is_broad_category_search_heuristic and not products_to_show_details: # Only if broad search yielded nothing
                     bot_reply_text = f"I looked for our {latest_preferences_for_filtering.get('category')}s, but it seems we don't have any matching that right now. Would you like to try a different category or ask for staff help?"
                action_buttons_for_frontend = [
                    {"label": "Adjust Search", "value": "adjust_preferences_dialogue"},
                    {"label": "Chat with Staff", "value": "request_staff_assistance_dialogue"}
                ]
                
                if redis_client and redis_client.is_connected():
                    session_data = redis_client.get_session(session_id)
                    if session_data:
                        session_data["current_conversational_state"] = "gathering_preferences"
                        redis_client.set_session(session_id, session_data)
                else:
                    SESSIONS_STORE[session_id]["current_conversational_state"] = "gathering_preferences"
    elif llm_action_suggestion == "ask_question":
        missing_param = llm_structured_data.get("missing_parameter_for_current_state") if isinstance(llm_structured_data, dict) else None # Check if llm_structured_data is dict
        if missing_param == "category":
            action_buttons_for_frontend = [
                {"label": "Rings", "value": "Rings"}, {"label": "Necklaces", "value": "Necklaces"},
                {"label": "Earrings", "value": "Earrings"}, {"label": "Bracelets", "value": "Bracelets"}
            ]
        else:
             action_buttons_for_frontend = [{"label": "Chat with Staff", "value": "request_staff_assistance_dialogue"}]
    elif llm_action_suggestion == "offer_staff_handoff":
        current_app_state_for_turn = "staff_handoff_requested"
        # Bot reply for staff handoff is already set if heuristic caught it or LLM decided it
        if not bot_reply_text.lower().startswith(("okay, i'll get a staff member", "sure, i'm notifying")):
             bot_reply_text = "Sure, I'm notifying a staff member to help you now."
        end_conversation_flag = True
        action_buttons_for_frontend = None
    # Log the assistant's reply *after* all processing for the turn is done
    log_to_conversation_history(session_id, "assistant", bot_reply_text, get_session_data(session_id).get("preferences"))
    logging.info(f"Bot Reply to Frontend: '{bot_reply_text}'")
    
    final_state = get_session_data(session_id).get("current_conversational_state", current_app_state_for_turn)
    logging.info(f"Final App State for session {session_id}: {final_state}")
    logging.info(f"--- Turn End ---\n")
    
    return BotResponse(
        session_id=session_id, reply=bot_reply_text, products=products_to_show_details,
        current_state=final_state,
        next_action_suggestion=llm_action_suggestion,
        action_buttons=action_buttons_for_frontend, end_conversation=end_conversation_flag
    )

@app.post("/new-session")
async def new_session_endpoint(data: dict):
    """
    Create a new session and clear existing session data
    
    Args:
        data: Dictionary containing session_id
        
    Returns:
        Status of session reset
    """
    session_id = data.get("session_id")
    
    if not session_id:
        return {"status": "error", "message": "session_id required"}
    
    try:
        if redis_client and redis_client.is_connected():
            # Delete from Redis
            result = redis_client.delete_session(session_id)
            if result:
                logging.info(f"Session {session_id} cleared from Redis")
                return {"status": "cleared", "message": "Session cleared from Redis"}
            else:
                logging.warning(f"Session {session_id} not found in Redis")
                return {"status": "not_found", "message": "Session not found in Redis"}
        else:
            # Clear from in-memory storage
            if session_id in SESSIONS_STORE:
                del SESSIONS_STORE[session_id]
                logging.info(f"Session {session_id} cleared from memory")
            
            # Clear conversation history
            global CONVERSATION_HISTORY_LOG
            CONVERSATION_HISTORY_LOG = [
                msg for msg in CONVERSATION_HISTORY_LOG 
                if msg.get("session_id") != session_id
            ]
            
            return {"status": "cleared", "message": "Session cleared from memory"}
            
    except Exception as e:
        logging.error(f"Error clearing session {session_id}: {e}")
        return {"status": "error", "message": str(e)}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.get("/admin/sessions")
async def admin_get_all_sessions(): return SESSIONS_STORE

@app.get("/admin/history")
async def admin_get_conversation_history(): return CONVERSATION_HISTORY_LOG

@app.get("/admin/redis-stats")
async def admin_get_redis_stats():
    """Get Redis connection and usage statistics"""
    try:
        if redis_client and redis_client.is_connected():
            stats = redis_client.get_stats()
            return {"redis_available": True, "stats": stats}
        else:
            return {"redis_available": False, "message": "Redis not connected"}
    except Exception as e:
        logging.error(f"Error getting Redis stats: {e}")
        return {"redis_available": False, "error": str(e)}

@app.get("/admin/vector-stats")
async def admin_get_vector_stats():
    """Get vector database and RAG system statistics"""
    try:
        stats = {
            "vector_database": None,
            "rag_system": None,
            "legacy_recommender": None,
            "system_status": "unknown"
        }
        
        if vector_db_instance:
            stats["vector_database"] = vector_db_instance.get_collection_stats()
        
        if rag_system_instance:
            stats["rag_system"] = rag_system_instance.get_system_stats()
        
        if jewellery_recommender_instance:
            stats["legacy_recommender"] = {
                "status": "initialized",
                "product_count": len(PRODUCT_CATALOG_DB) if PRODUCT_CATALOG_DB else 0
            }
        
        # Determine system status
        if vector_db_instance and rag_system_instance:
            stats["system_status"] = "enhanced_with_rag"
        elif jewellery_recommender_instance:
            stats["system_status"] = "legacy_only"
        else:
            stats["system_status"] = "error"
            
        return stats
        
    except Exception as e:
        logging.error(f"Error getting system stats: {e}")
        return {"error": str(e)}

@app.get("/admin/test-vector-search")
async def admin_test_vector_search(query: str = "elegant gold ring"):
    """Test vector search functionality"""
    try:
        if not vector_db_instance:
            return {"error": "Vector database not initialized"}
            
        results = vector_db_instance.semantic_search(query, top_k=3)
        return {
            "query": query,
            "results_count": len(results),
            "results": results
        }
        
    except Exception as e:
        logging.error(f"Error testing vector search: {e}")
        return {"error": str(e)}