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
    interactive_options: Optional[List[Dict[str, Any]]] = None
    end_conversation: bool = False
    ui_mode: str = "chat"

class StartRequest(BaseModel):
    session_id: Optional[str] = None

SESSIONS_STORE: Dict[str, Dict[str, Any]] = {}
CONVERSATION_HISTORY_LOG: List[Dict[str, Any]] = []
PRODUCT_CATALOG_DB: List[Dict[str, Any]] = []
ALL_PREFERENCE_KEYS = list(ExtractedPreferences.model_fields.keys())

redis_client = get_redis_client() if REDIS_AVAILABLE and get_redis_client().is_connected() else None
if not redis_client: logging.warning("Redis not available - using in-memory storage")

app = FastAPI(title="Joxy Retail AI Assistant API")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index(): return FileResponse('static/index.html')

def load_products_from_json(filepath="product_catalog_large.json"):
    global PRODUCT_CATALOG_DB
    try:
        with open(filepath, 'r', encoding='utf-8') as f: PRODUCT_CATALOG_DB = json.load(f)
        logging.info(f"Successfully loaded {len(PRODUCT_CATALOG_DB)} products.")
    except Exception as e:
        logging.error(f"Error loading product catalog: {e}"); PRODUCT_CATALOG_DB = []

class JewelleryRecommender:
    def __init__(self, product_catalog: List[Dict[str, Any]]): self.product_catalog = product_catalog
    def _calculate_match_score(self, product: Dict[str, Any], preferences: Dict[str, Any]) -> float:
        score = 0.0
        # ... [Keeping the entire _calculate_match_score function from Code 2] ...
        matched_any_preference = False
        category_pref = preferences.get("category")
        if category_pref:
            if product.get("category","").lower() == category_pref.lower():
                score += 100
                matched_any_preference = True
            else:
                return 0.0
        if category_pref and len([v for k,v in preferences.items() if v and k != "category" and k != "user_query_was_generic_show_all"]) == 0:
             if product.get("category","").lower() == category_pref.lower():
                 return 50.0 
        metal_pref = preferences.get("metal")
        if metal_pref and metal_pref.lower() in product.get("metal","").lower(): score += 20; matched_any_preference = True
        gemstone_pref = preferences.get("gemstone")
        if gemstone_pref and gemstone_pref.lower() != "none":
            if gemstone_pref.lower() in [g.lower() for g in product.get("gemstones", [])]: score += 30; matched_any_preference = True
        elif gemstone_pref and gemstone_pref.lower() == "none":
            if "none" in [g.lower() for g in product.get("gemstones", ["none"])]: score += 10; matched_any_preference = True
        style_pref = preferences.get("style")
        if style_pref and style_pref.lower() in [s.lower() for s in product.get("style_tags",[])]: score += 15; matched_any_preference = True
        design_type_pref = preferences.get("design_type")
        if design_type_pref and product.get("design_type","").lower() == design_type_pref.lower(): score += 10; matched_any_preference = True
        occasion_pref = preferences.get("occasion")
        if occasion_pref and occasion_pref.lower() in [o.lower() for o in product.get("occasion_tags",[])]: score += 10; matched_any_preference = True
        recipient_pref = preferences.get("recipient")
        if recipient_pref and recipient_pref.lower() in [r.lower() for r in product.get("recipient_tags",[])]: score += 5; matched_any_preference = True
        budget_max_pref = preferences.get("budget_max")
        if budget_max_pref is not None:
            try:
                budget_max = float(budget_max_pref)
                price = product.get("price", float('inf'))
                if price <= budget_max: score += 20; matched_any_preference = True
                if price >= budget_max * 0.70: score += 5
            except (ValueError, TypeError): pass
        if not preferences or (not matched_any_preference and not (category_pref and len([v for k,v in preferences.items() if v and k != "category" and k != "user_query_was_generic_show_all"]) == 0)): return 0.0
        return score
    def recommend_products(self, preferences: Dict[str, Any], top_n: int = 5) -> List[Dict[str, Any]]:
        if not self.product_catalog: return []
        is_broad_category_search = preferences.get("user_query_was_generic_show_all", False)
        category_pref = preferences.get("category")
        if is_broad_category_search and category_pref:
            results = [p for p in self.product_catalog if p.get("category","").lower() == category_pref.lower()]
            results.sort(key=lambda p: p.get("price", 0)); return results[:top_n]
        scored_products = []
        for product in self.product_catalog:
            budget_max_pref = preferences.get("budget_max")
            if budget_max_pref is not None:
                try:
                    if product.get("price", float('inf')) > float(budget_max_pref): continue
                except (ValueError, TypeError): pass
            if category_pref and product.get("category","").lower() != category_pref.lower(): continue
            score = self._calculate_match_score(product, preferences)
            if score > 0: scored_products.append({"product": product, "score": score})
        scored_products.sort(key=lambda x: (x["score"], -x["product"].get("price", float('inf'))), reverse=True)
        return [sp["product"] for sp in scored_products[:top_n]]

jewellery_recommender_instance: Optional[JewelleryRecommender] = None
vector_db_instance = None
rag_system_instance = None

@app.on_event("startup")
async def startup_event():
    global jewellery_recommender_instance, vector_db_instance, rag_system_instance
    load_products_from_json()
    if PRODUCT_CATALOG_DB:
        jewellery_recommender_instance = JewelleryRecommender(PRODUCT_CATALOG_DB)
        if ENHANCED_FEATURES_AVAILABLE:
            try:
                vector_db_instance = initialize_vector_database_with_products(PRODUCT_CATALOG_DB)
                rag_system_instance = get_rag_system()
            except Exception as e:
                logging.error(f"Error initializing vector DB/RAG: {e}")
                vector_db_instance, rag_system_instance = None, None
    else: logging.critical("PRODUCT CATALOG IS EMPTY.")

def log_to_conversation_history(session_id: str, role: str, content: str, preferences_at_turn: Optional[Dict] = None):
    # This is a simplified function combining Code 2's logic for history
    session_data = get_session_data(session_id)
    history = session_data.get("history", [])
    history.append({"role": role, "content": content})
    session_data["history"] = history[-10:] # Keep last 10 turns
    
    if redis_client: redis_client.set_session(session_id, session_data)
    else: SESSIONS_STORE[session_id] = session_data
    logging.debug(f"History Logged for {session_id}: {role} - {content[:50]}...")

def get_session_data(session_id: str) -> Dict[str, Any]:
    if redis_client: return (redis_client.get_session(session_id) or {}).copy()
    else: return SESSIONS_STORE.get(session_id, {}).copy()

def update_session_data(session_id: str, updates: Dict[str, Any]):
    session_data = get_session_data(session_id)
    session_data.update(updates)
    if redis_client: redis_client.set_session(session_id, session_data)
    else: SESSIONS_STORE[session_id] = session_data

def get_or_create_session(session_id_str: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    if session_id_str:
        session_data = get_session_data(session_id_str)
        if session_data:
            return session_id_str, session_data
    
    new_id = str(uuid.uuid4())
    new_session_data = {
        "current_state": "initial_greeting",
        "user_name": None,
        "preferences": {key: None for key in ALL_PREFERENCE_KEYS},
        "history": []
    }
    update_session_data(new_id, new_session_data)
    logging.info(f"New session created: {new_id}")
    return new_id, new_session_data

def get_system_prompt_v4(current_preferences_json_string: str) -> str:
    # This is the powerful prompt from Code 2, used after the initial onboarding.
    return f"""
    SYSTEM PROMPT: ESTROTECH AI ASSISTANT - LUXURY JEWELLERY SALESPERSON (V4 - Dialogflow CX Inspired)
    You are EstroTech AI Assistant, a highly intelligent, empathetic, and efficient digital salesperson in a luxury jewellery store. Your primary goal is to understand the customer's needs through natural, guided conversation, proactively offer relevant product recommendations, and seamlessly connect them to staff when needed.
    **Current Known Parameters (from previous turns, acting as session parameters):**
    {current_preferences_json_string}
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
    ```
    """

def get_llm_structured_response(session_id: str, user_message: str) -> Tuple[str, Dict[str, Any]]:
    # This is the fully functional LLM call from Code 2.
    current_session_data = get_session_data(session_id)
    current_preferences = current_session_data.get("preferences", {})
    conversation_history = current_session_data.get("history", [])[-5:]
    system_prompt = get_system_prompt_v4(json.dumps(current_preferences))
    messages = [{"role": "system", "content": system_prompt}] + conversation_history + [{"role": "user", "content": user_message}]
    
    try:
        chat_completion = client.chat.completions.create(
            messages=messages, model=SELECTED_GROQ_MODEL,
            temperature=0.3, max_tokens=800, response_format={"type": "json_object"}
        )
        response_content = chat_completion.choices[0].message.content.strip()
        validated_output = LLMStructuredOutput.model_validate_json(response_content)
        
        # Update preferences based on LLM extraction
        new_prefs = validated_output.extracted_preferences.model_dump(exclude_none=True)
        current_preferences.update(new_prefs)
        update_session_data(session_id, {"preferences": current_preferences})

        return validated_output.dialogue_response, validated_output.model_dump(exclude={"dialogue_response"})
    except Exception as e:
        logging.error(f"LLM Error for session {session_id}: {e}")
        return "I'm having a little trouble thinking. Could we try that a different way?", {"next_action": "ask_question", "current_conversational_state": "gathering_preferences"}


@app.post("/start", response_model=BotResponse)
async def start_conversation(request: StartRequest):
    session_id, session_data = get_or_create_session(request.session_id)
    
    # If the session is new (no history logged), start the onboarding flow.
    if not session_data.get("history"):
        reply = "Welcome to Joxy! I'm your personal jewelry assistant. To get started, what should I call you?"
        update_session_data(session_id, {"current_state": "collecting_user_name"})
        log_to_conversation_history(session_id, "assistant", reply, session_data.get("preferences"))
        
        return BotResponse(session_id=session_id, reply=reply, current_state="collecting_user_name", ui_mode="text_input_only")
    
    # If session exists, resume.
    last_message = session_data["history"][-1]["content"] if session_data.get("history") else "our last chat."
    return BotResponse(session_id=session_id, reply=f"Welcome back, {session_data.get('user_name', '')}! We were discussing: \"{last_message}\"", current_state=session_data.get("current_state", "gathering_preferences"))

@app.post("/chat", response_model=BotResponse)
async def chat_endpoint(user_input: UserInput):
    session_id, session_data = get_or_create_session(user_input.session_id)
    user_message = user_input.message.strip()
    log_to_conversation_history(session_id, "user", user_message, session_data.get("preferences"))

    current_state = session_data.get("current_state", "initial_greeting")
    
    # --- STATE MACHINE FOR ONBOARDING ---
    if current_state == 'collecting_user_name':
        user_name = user_message.strip().capitalize()
        update_session_data(session_id, {"user_name": user_name, "current_state": "collecting_purpose"})
        reply = f"It's a pleasure to meet you, {user_name}! Are you looking for a special piece for yourself or for someone else?"
        options = [
            {"label": "For Myself", "value": "For myself"},
            {"label": "Someone Special", "value": "Someone special"},
            {"label": "Type Answer...", "value": "__type__"}
        ]
        log_to_conversation_history(session_id, "assistant", reply, session_data.get("preferences"))
        return BotResponse(session_id=session_id, reply=reply, current_state="collecting_purpose", interactive_options=options, ui_mode="chat")

    elif current_state == 'collecting_purpose':
        if "someone special" in user_message.lower():
            update_session_data(session_id, {"current_state": "collecting_recipient"})
            reply = "How wonderful! Who is the lucky person?"
            options = [
                {"label": "My Partner", "value": "My partner"},
                {"label": "A Family Member", "value": "A family member"},
                {"label": "A Friend", "value": "A friend"},
                {"label": "Type Answer...", "value": "__type__"}
            ]
            log_to_conversation_history(session_id, "assistant", reply, session_data.get("preferences"))
            return BotResponse(session_id=session_id, reply=reply, current_state="collecting_recipient", interactive_options=options, ui_mode="chat")
        else: # Assumes "For myself" or similar
            update_session_data(session_id, {"current_state": "gathering_preferences", "preferences": {"recipient": "myself"}})
            # Now, hand off to the LLM
            user_message = "I'm looking for something for myself." # Synthesize message for LLM
    
    elif current_state == 'collecting_recipient':
        update_session_data(session_id, {"current_state": "gathering_preferences", "preferences": {"recipient": user_message}})
        # Hand off to LLM
        user_message = f"I'm looking for a gift for my {user_message}."

    # --- GENERAL LLM HANDLING & ACTION CARDS ---
    bot_reply_text, llm_data = get_llm_structured_response(session_id, user_message)
    current_state = llm_data.get("current_conversational_state", "error_state")
    next_action = llm_data.get("next_action", "ask_question")
    products = []
    
    if next_action == "recommend_products":
        preferences = get_session_data(session_id).get("preferences", {})
        if rag_system_instance:
            products = rag_system_instance.retrieve_relevant_products(user_message, preferences, top_k=5)
        elif jewellery_recommender_instance:
            products = jewellery_recommender_instance.recommend_products(preferences, top_n=5)
    
    products_to_show = [ProductDetail(**p) for p in products] if products else None
    
    # Generate action buttons based on state
    interactive_options = []
    if next_action == "ask_question":
        if llm_data.get("missing_parameter_for_current_state") == "category":
            interactive_options = [{"label": "Rings", "value": "Rings"}, {"label": "Necklaces", "value": "Necklaces"}]
        else:
             interactive_options = [{"label": "Type Answer...", "value": "__type__"}]

    ui_mode = "chat" if interactive_options else "text_input_only"
    if products_to_show:
        ui_mode = "chat"
        interactive_options.extend([
             {"label": "Adjust Filters", "value": "adjust_preferences_dialogue"},
             {"label": "Chat with Staff", "value": "request_staff_assistance_dialogue"}
        ])


    return BotResponse(
        session_id=session_id,
        reply=bot_reply_text,
        products=products_to_show,
        current_state=current_state,
        interactive_options=interactive_options,
        ui_mode=ui_mode
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)