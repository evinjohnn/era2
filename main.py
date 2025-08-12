import os
import json
import uuid
import logging
from typing import Optional, List, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from rag_system import get_rag_system
from vector_db import initialize_vector_database_with_products

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Data and Model Loading ---
PRODUCT_CATALOG = []
try:
    with open("product_catalog_large.json", 'r') as f:
        PRODUCT_CATALOG = json.load(f)
    logging.info(f"Loaded {len(PRODUCT_CATALOG)} products from catalog.")
except (FileNotFoundError, json.JSONDecodeError) as e:
    logging.error(f"Could not load product catalog: {e}. Recommendations will not work.")

# --- FastAPI App Initialization ---
app = FastAPI(title="Guided Conversational E-commerce Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# --- Global Instances ---
SESSIONS = {}  # In-memory session storage
rag_system = None
vector_db = None

@app.on_event("startup")
def startup_event():
    global rag_system, vector_db
    if PRODUCT_CATALOG:
        logging.info("Initializing Vector DB and RAG System...")
        vector_db = initialize_vector_database_with_products(PRODUCT_CATALOG)
        rag_system = get_rag_system()
        logging.info("Vector DB and RAG System initialized successfully.")
    else:
        logging.warning("Skipping RAG/Vector DB initialization due to empty product catalog.")

# --- Pydantic Models for API ---
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str

class UIOption(BaseModel):
    label: str
    value: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    ui_options: Optional[List[UIOption]] = None
    products: Optional[List[Dict[str, Any]]] = None

# --- Recommendation Logic ---
def get_recommendations(attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Two-tiered recommendation engine: RAG primary, legacy filter fallback.
    """
    query = f"A {attributes.get('occasion', '')} gift for my {attributes.get('recipient', '')}"
    
    # 1. Primary Method: RAG Recommendation
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

    # 2. Fallback Method: Legacy Tag-based Filtering
    logging.info("Executing legacy tag-based filter.")
    required_tags = {v for k, v in attributes.items() if v and k in ['occasion', 'recipient']}
    if not required_tags:
        return []

    filtered_products = [
        p for p in PRODUCT_CATALOG
        if required_tags.issubset(set(p.get('tags', [])))
    ]
    
    # Sort by price as a simple ranking mechanism for the fallback
    filtered_products.sort(key=lambda p: p.get('price', 0), reverse=True)
    logging.info(f"Legacy filter found {len(filtered_products)} products.")
    return filtered_products[:4]

# --- Conversational Flow (State Machine) ---
def process_conversational_turn(session: Dict, user_message: str) -> Dict:
    state = session.get('state', 'AWAITING_NAME')
    attributes = session.get('attributes', {})
    response = {}

    if state == 'AWAITING_NAME':
        attributes['name'] = user_message
        session['state'] = 'AWAITING_INTENT'
        response['reply'] = f"Hi {attributes['name']}! Are you looking for something special or just Browse today?"
        response['ui_options'] = [
            UIOption(label="I'm looking for something special", value="special"),
            UIOption(label="I'm just Browse", value="browse")
        ]
    
    elif state == 'AWAITING_INTENT':
        if user_message.lower() == 'special':
            attributes['intent'] = 'special'
            session['state'] = 'AWAITING_OCCASION'
            response['reply'] = "Excellent! What is the special occasion?"
            response['ui_options'] = [
                UIOption(label="Wedding", value="wedding"),
                UIOption(label="Birthday", value="birthday"),
                UIOption(label="Anniversary", value="anniversary"),
                UIOption(label="Other", value="other")
            ]
        else:
            attributes['intent'] = 'browse'
            session['state'] = 'BROWSING'
            response['reply'] = "No problem! Feel free to look around. What category are you interested in?"
            # In a full browsing implementation, more options would follow.
            response['products'] = random.sample(PRODUCT_CATALOG, 4)

    elif state == 'AWAITING_OCCASION':
        attributes['occasion'] = user_message.lower()
        session['state'] = 'AWAITING_RECIPIENT'
        response['reply'] = "That's wonderful. Who is this gift for?"
        response['ui_options'] = [
            UIOption(label="Wife", value="wife"),
            UIOption(label="Parent", value="parent"),
            UIOption(label="Girlfriend", value="girlfriend"),
            UIOption(label="Friend", value="friend"),
            UIOption(label="Myself", value="myself")
        ]

    elif state == 'AWAITING_RECIPIENT':
        attributes['recipient'] = user_message.lower()
        session['state'] = 'RECOMMENDING'
        # Transition directly to recommendations
        products = get_recommendations(attributes)
        if products:
            response['reply'] = f"Based on a {attributes['occasion']} for your {attributes['recipient']}, here are a few ideas I think you'll love:"
            response['products'] = products
        else:
            response['reply'] = f"I searched for a {attributes['occasion']} gift for your {attributes['recipient']} but couldn't find a perfect match. Would you like to browse our general collection?"
            session['state'] = 'BROWSING' # Fallback state

    session['attributes'] = attributes
    return response

# --- API Endpoints ---
@app.post("/chat", response_model=ChatResponse)
def chat_handler(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    session = SESSIONS.get(session_id, {'state': 'AWAITING_NAME', 'attributes': {}})
    
    response_data = process_conversational_turn(session, request.message)
    
    SESSIONS[session_id] = session
    
    return ChatResponse(
        session_id=session_id,
        reply=response_data.get('reply', "I'm not sure how to respond to that."),
        ui_options=response_data.get('ui_options'),
        products=response_data.get('products')
    )

# --- Static File Serving ---
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')