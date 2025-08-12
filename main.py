import os
import json
import uuid
import logging
import random
from typing import Optional, List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from database import init_database, wait_for_db, get_database_manager
from vector_db import initialize_vector_database_with_products
from rag_system import get_rag_system
from staff_dashboard import create_staff_dashboard_routes

# --- Configuration & Initialization ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)s] - %(message)s')

app = FastAPI(title="Joxy Retail AI Assistant API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# --- Global Instances & Data ---
SESSIONS = {}  # In-memory session storage for simplicity
PRODUCT_CATALOG = []
rag_system = None

@app.on_event("startup")
async def startup_event():
    global PRODUCT_CATALOG, rag_system
    if wait_for_db():
        init_database()
        db_manager = get_database_manager()
        db = next(db_manager.get_db())
        products_from_db = db_manager.get_all_products(db)
        db.close()
        
        PRODUCT_CATALOG = [p.__dict__ for p in products_from_db]
        if PRODUCT_CATALOG:
            initialize_vector_database_with_products(PRODUCT_CATALOG)
            rag_system = get_rag_system()
            logging.info("Application startup complete with RAG system.")
        else:
            logging.error("No products found in the database. Recommendations will fail.")
    else:
        logging.critical("DATABASE NOT READY. Application startup failed.")

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str

class UIOption(BaseModel):
    label: str
    value: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    action_buttons: Optional[List[UIOption]] = None
    products: Optional[List[Dict[str, Any]]] = None

class NewSessionRequest(BaseModel):
    session_id: Optional[str] = None

# --- Recommendation Logic ---
def get_recommendations(attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
    query = f"A {attributes.get('occasion', '')} gift for my {attributes.get('recipient', '')}"
    
    try:
        if rag_system:
            logging.info(f"Attempting RAG recommendation with query: '{query}'")
            rag_products = rag_system.retrieve_relevant_products(query, attributes, top_k=4)
            if rag_products:
                logging.info(f"RAG system returned {len(rag_products)} products.")
                return rag_products
        logging.warning("RAG system not available or returned no results.")
    except Exception as e:
        logging.error(f"RAG recommendation failed: {e}. Proceeding to fallback.")

    logging.info("Executing legacy tag-based filter.")
    required_tags = {v for k, v in attributes.items() if v and k in ['occasion', 'recipient']}
    if not required_tags: return []

    filtered = [p for p in PRODUCT_CATALOG if required_tags.issubset(set(p.get('tags', [])))]
    filtered.sort(key=lambda p: p.get('price', 0), reverse=True)
    logging.info(f"Legacy filter found {len(filtered)} products.")
    return filtered[:4]

# --- Conversational Flow State Machine ---
def process_turn(session: Dict, user_message: str) -> Dict:
    state = session.get('state', 'AWAITING_NAME')
    attributes = session.get('attributes', {})
    response = {}

    if state == 'AWAITING_NAME':
        attributes['name'] = user_message.strip()
        session['state'] = 'AWAITING_INTENT'
        response['reply'] = f"Hi {attributes['name']}! Are you looking for something special or just browsing today?"
        response['action_buttons'] = [UIOption(label="I'm looking for something special", value="special"), UIOption(label="I'm just browsing", value="browse")]
    
    elif state == 'AWAITING_INTENT':
        if 'special' in user_message.lower():
            attributes['intent'] = 'special'
            session['state'] = 'AWAITING_OCCASION'
            response['reply'] = "Excellent! What is the special occasion?"
            response['action_buttons'] = [UIOption(label="Wedding", value="wedding"), UIOption(label="Birthday", value="birthday"), UIOption(label="Anniversary", value="anniversary"), UIOption(label="Other", value="other")]
        else:
            attributes['intent'] = 'browse'
            session['state'] = 'BROWSING'
            response['reply'] = "No problem! Here are some of our most popular items to get you started."
            response['products'] = random.sample(PRODUCT_CATALOG, 4) if PRODUCT_CATALOG else []

    elif state == 'AWAITING_OCCASION':
        attributes['occasion'] = user_message.lower()
        session['state'] = 'AWAITING_RECIPIENT'
        response['reply'] = "That's wonderful. Who is this gift for?"
        response['action_buttons'] = [UIOption(label="Wife", value="wife"), UIOption(label="Parent", value="parent"), UIOption(label="Girlfriend", value="girlfriend"), UIOption(label="Friend", value="friend"), UIOption(label="Myself", value="myself")]

    elif state == 'AWAITING_RECIPIENT':
        attributes['recipient'] = user_message.lower()
        session['state'] = 'RECOMMENDING'
        products = get_recommendations(attributes)
        if products:
            response['reply'] = f"Based on a {attributes['occasion']} gift for your {attributes['recipient']}, here are a few ideas:"
            response['products'] = products
        else:
            response['reply'] = f"I searched for a {attributes['occasion']} gift for your {attributes['recipient']} but couldn't find a perfect match. Here are some general best-sellers you might like."
            response['products'] = random.sample(PRODUCT_CATALOG, 4) if PRODUCT_CATALOG else []
            session['state'] = 'BROWSING'

    session['attributes'] = attributes
    return response

# --- API Endpoints ---
@app.post("/chat", response_model=ChatResponse)
async def chat_handler(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    session = SESSIONS.get(session_id, {'state': 'AWAITING_NAME', 'attributes': {}})
    
    # Initial greeting logic
    if not request.message and session['state'] == 'AWAITING_NAME':
        response_data = {'reply': "Welcome to our store! I'm your personal shopping assistant. What's your name?"}
    else:
        response_data = process_turn(session, request.message)
    
    SESSIONS[session_id] = session
    
    return ChatResponse(
        session_id=session_id,
        reply=response_data.get('reply'),
        action_buttons=response_data.get('action_buttons'),
        products=response_data.get('products')
    )

@app.post("/new-session")
async def new_session_handler(request: NewSessionRequest):
    if request.session_id and request.session_id in SESSIONS:
        del SESSIONS[request.session_id]
        logging.info(f"Cleared session {request.session_id}")
    return {"status": "success", "message": "Session cleared"}

# --- Static Files & Dashboard ---
app.mount("/static", StaticFiles(directory="static"), name="static")
create_staff_dashboard_routes(app) # Add dashboard routes

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')