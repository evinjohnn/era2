import os
import json
import uuid
import logging
import random
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
    action_buttons: Optional[List[UIOption]] = None
    products: Optional[List[Dict[str, Any]]] = None

class NewSessionRequest(BaseModel):
    session_id: str

# --- Enhanced Recommendation Logic ---
def get_recommendations(attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Two-tiered recommendation engine: RAG primary, legacy filter fallback.
    Enhanced to understand user responses and create meaningful queries.
    """
    # Create a natural language query based on collected attributes
    query_parts = []
    
    if attributes.get('occasion'):
        occasion = attributes['occasion']
        if occasion == 'wedding':
            query_parts.append("wedding jewelry engagement ring")
        elif occasion == 'birthday':
            query_parts.append("birthday gift jewelry")
        elif occasion == 'anniversary':
            query_parts.append("anniversary jewelry romantic gift")
        else:
            query_parts.append(f"{occasion} jewelry gift")
    
    if attributes.get('recipient'):
        recipient = attributes['recipient']
        if recipient == 'wife':
            query_parts.append("for wife elegant")
        elif recipient == 'girlfriend':
            query_parts.append("for girlfriend romantic")
        elif recipient == 'mother':
            query_parts.append("for mother classic")
        elif recipient == 'friend':
            query_parts.append("for friend stylish")
        else:
            query_parts.append(f"for {recipient}")
    
    # Combine all parts into a meaningful query
    query = " ".join(query_parts) if query_parts else "jewelry gift"
    
    logging.info(f"Generated RAG query: '{query}' from attributes: {attributes}")
    
    # 1. Primary Method: RAG Recommendation
    try:
        if rag_system:
            logging.info(f"Attempting RAG recommendation with query: '{query}'")
            # Create preferences dict for the RAG system
            preferences = {
                'occasion': attributes.get('occasion'),
                'recipient': attributes.get('recipient'),
                'category': attributes.get('category', 'jewelry')
            }
            
            rag_products = rag_system.retrieve_relevant_products(query, preferences, top_k=6)
            if rag_products and len(rag_products) >= 3:
                logging.info(f"RAG system returned {len(rag_products)} products.")
                return rag_products[:6]
        logging.warning("RAG system not available or returned insufficient results.")
    except Exception as e:
        logging.error(f"RAG recommendation failed: {e}. Proceeding to fallback.")

    # 2. Fallback Method: Enhanced Tag-based Filtering
    logging.info("Executing enhanced tag-based filter.")
    
    # Build comprehensive filter criteria
    filter_criteria = []
    
    # Occasion-based filtering
    if attributes.get('occasion'):
        occasion = attributes['occasion']
        if occasion == 'wedding':
            filter_criteria.extend(['wedding', 'engagement', 'formal'])
        elif occasion == 'birthday':
            filter_criteria.extend(['birthday', 'gift', 'celebration'])
        elif occasion == 'anniversary':
            filter_criteria.extend(['anniversary', 'romantic', 'love'])
        else:
            filter_criteria.append(occasion)
    
    # Recipient-based filtering
    if attributes.get('recipient'):
        recipient = attributes['recipient']
        if recipient == 'wife':
            filter_criteria.extend(['wife', 'spouse', 'romantic'])
        elif recipient == 'girlfriend':
            filter_criteria.extend(['girlfriend', 'romantic', 'love'])
        elif recipient == 'mother':
            filter_criteria.extend(['mother', 'parent', 'family'])
        elif recipient == 'friend':
            filter_criteria.extend(['friend', 'casual', 'stylish'])
        else:
            filter_criteria.append(recipient)
    
    # Apply filters to products
    filtered_products = []
    for product in PRODUCT_CATALOG:
        product_tags = set()
        
        # Collect all tags from the product
        if product.get('tags'):
            product_tags.update(product['tags'])
        if product.get('occasion_tags'):
            product_tags.update(product['occasion_tags'])
        if product.get('recipient_tags'):
            product_tags.update(product['recipient_tags'])
        if product.get('style_tags'):
            product_tags.update(product['style_tags'])
        
        # Check if product matches any of our criteria
        if any(criteria.lower() in tag.lower() for criteria in filter_criteria for tag in product_tags):
            filtered_products.append(product)
    
    # Sort by relevance (products with more matching tags first) and price
    def relevance_score(product):
        product_tags = set()
        if product.get('tags'):
            product_tags.update(product['tags'])
        if product.get('occasion_tags'):
            product_tags.update(product['occasion_tags'])
        if product.get('recipient_tags'):
            product_tags.update(product['recipient_tags'])
        if product.get('style_tags'):
            product_tags.update(product['style_tags'])
        
        # Count matching criteria
        matches = sum(1 for criteria in filter_criteria 
                     if any(criteria.lower() in tag.lower() for tag in product_tags))
        return (matches, product.get('price', 0))
    
    filtered_products.sort(key=relevance_score, reverse=True)
    logging.info(f"Enhanced filter found {len(filtered_products)} products.")
    return filtered_products[:6]

# --- Conversational Flow (Enhanced State Machine) ---
def process_conversational_turn(session: Dict, user_message: str) -> Dict:
    state = session.get('state', 'AWAITING_NAME')
    attributes = session.get('attributes', {})
    response = {}

    if state == 'AWAITING_NAME':
        # Extract name from user message
        name = user_message.strip()
        if name and len(name) > 0:
            attributes['name'] = name
            session['state'] = 'AWAITING_INTENT'
            response['reply'] = f"Hi {attributes['name']}! Are you looking for something special or just browsing today?"
            response['action_buttons'] = [
                UIOption(label="I'm looking for something special", value="special"),
                UIOption(label="I'm just browsing", value="browse")
            ]
        else:
            response['reply'] = "I didn't catch your name. Could you please tell me what to call you?"
    
    elif state == 'AWAITING_INTENT':
        user_choice = user_message.lower().strip()
        if user_choice in ['special', 'something special', 'looking for something special']:
            attributes['intent'] = 'special'
            session['state'] = 'AWAITING_OCCASION'
            response['reply'] = "Excellent! What is the special occasion?"
            response['action_buttons'] = [
                UIOption(label="Wedding", value="wedding"),
                UIOption(label="Birthday", value="birthday"),
                UIOption(label="Anniversary", value="anniversary"),
                UIOption(label="Other", value="other")
            ]
        elif user_choice in ['browse', 'browsing', 'just browsing']:
            attributes['intent'] = 'browse'
            session['state'] = 'BROWSING'
            response['reply'] = "No problem! Feel free to look around. What category are you interested in?"
            response['action_buttons'] = [
                UIOption(label="Rings", value="rings"),
                UIOption(label="Necklaces", value="necklaces"),
                UIOption(label="Earrings", value="earrings"),
                UIOption(label="Bracelets", value="bracelets")
            ]
        else:
            # Handle text input fallback
            if 'special' in user_choice or 'gift' in user_choice or 'occasion' in user_choice:
                attributes['intent'] = 'special'
                session['state'] = 'AWAITING_OCCASION'
                response['reply'] = "I understand you're looking for something special! What is the occasion?"
                response['action_buttons'] = [
                    UIOption(label="Wedding", value="wedding"),
                    UIOption(label="Birthday", value="birthday"),
                    UIOption(label="Anniversary", value="anniversary"),
                    UIOption(label="Other", value="other")
                ]
            else:
                response['reply'] = "I'm not sure I understood. Are you looking for something special or just browsing? You can also type your answer."
                response['action_buttons'] = [
                    UIOption(label="I'm looking for something special", value="special"),
                    UIOption(label="I'm just browsing", value="browse")
                ]

    elif state == 'AWAITING_OCCASION':
        occasion = user_message.lower().strip()
        if occasion in ['wedding', 'birthday', 'anniversary', 'other']:
            attributes['occasion'] = occasion
            session['state'] = 'AWAITING_RECIPIENT'
            response['reply'] = "That's wonderful! Who is this gift for?"
            response['action_buttons'] = [
                UIOption(label="Wife", value="wife"),
                UIOption(label="Mother", value="mother"),
                UIOption(label="Girlfriend", value="girlfriend"),
                UIOption(label="Friend", value="friend"),
                UIOption(label="Myself", value="myself")
            ]
        else:
            # Handle text input fallback
            if any(word in occasion for word in ['wedding', 'marriage', 'engagement']):
                attributes['occasion'] = 'wedding'
            elif any(word in occasion for word in ['birthday', 'birth day', 'bday']):
                attributes['occasion'] = 'birthday'
            elif any(word in occasion for word in ['anniversary', 'anniversary']):
                attributes['occasion'] = 'anniversary'
            else:
                attributes['occasion'] = 'other'
            
            session['state'] = 'AWAITING_RECIPIENT'
            response['reply'] = f"I understand it's for a {attributes['occasion']} occasion! Who is this gift for?"
            response['action_buttons'] = [
                UIOption(label="Wife", value="wife"),
                UIOption(label="Mother", value="mother"),
                UIOption(label="Girlfriend", value="girlfriend"),
                UIOption(label="Friend", value="friend"),
                UIOption(label="Myself", value="myself")
            ]

    elif state == 'AWAITING_RECIPIENT':
        recipient = user_message.lower().strip()
        if recipient in ['wife', 'mother', 'girlfriend', 'friend', 'myself']:
            attributes['recipient'] = recipient
        else:
            # Handle text input fallback
            if any(word in recipient for word in ['wife', 'spouse', 'partner']):
                attributes['recipient'] = 'wife'
            elif any(word in recipient for word in ['mother', 'mom', 'parent']):
                attributes['recipient'] = 'mother'
            elif any(word in recipient for word in ['girlfriend', 'girl friend', 'partner']):
                attributes['recipient'] = 'girlfriend'
            elif any(word in recipient for word in ['friend', 'buddy', 'pal']):
                attributes['recipient'] = 'friend'
            else:
                attributes['recipient'] = 'myself'
        
        session['state'] = 'RECOMMENDING'
        # Generate recommendations based on collected attributes
        products = get_recommendations(attributes)
        
        if products:
            occasion_text = attributes.get('occasion', 'special')
            recipient_text = attributes.get('recipient', 'loved one')
            
            response['reply'] = f"Perfect! Based on a {occasion_text} gift for your {recipient_text}, here are some recommendations I think you'll love:"
            response['products'] = products
        else:
            response['reply'] = f"I searched for a {attributes.get('occasion', 'special')} gift for your {attributes.get('recipient', 'loved one')} but couldn't find a perfect match. Would you like to browse our general collection?"
            session['state'] = 'BROWSING'
            response['action_buttons'] = [
                UIOption(label="Browse All Products", value="browse_all"),
                UIOption(label="Try Different Criteria", value="restart")
            ]

    elif state == 'BROWSING':
        if user_message.lower() in ['rings', 'necklaces', 'earrings', 'bracelets']:
            attributes['category'] = user_message.lower()
            # Filter products by category
            category_products = [p for p in PRODUCT_CATALOG if p.get('category') == attributes['category']]
            if category_products:
                response['reply'] = f"Great choice! Here are some beautiful {attributes['category']}:"
                response['products'] = random.sample(category_products, min(6, len(category_products)))
            else:
                response['reply'] = f"I couldn't find any {attributes['category']} at the moment. Would you like to browse a different category?"
                response['action_buttons'] = [
                    UIOption(label="Rings", value="rings"),
                    UIOption(label="Necklaces", value="necklaces"),
                    UIOption(label="Earrings", value="earrings"),
                    UIOption(label="Bracelets", value="bracelets")
                ]
        elif user_message.lower() == 'browse_all':
            response['reply'] = "Here are some of our featured products:"
            response['products'] = random.sample(PRODUCT_CATALOG, min(6, len(PRODUCT_CATALOG)))
        elif user_message.lower() == 'restart':
            session['state'] = 'AWAITING_NAME'
            response['reply'] = "Let's start over! What's your name?"
        else:
            response['reply'] = "I'm here to help you find the perfect jewelry. You can select from the options above or type what you're looking for."
            response['action_buttons'] = [
                UIOption(label="Rings", value="rings"),
                UIOption(label="Necklaces", value="necklaces"),
                UIOption(label="Earrings", value="earrings"),
                UIOption(label="Bracelets", value="bracelets"),
                UIOption(label="Start Over", value="restart")
            ]

    elif state == 'RECOMMENDING':
        # User can ask for more recommendations or start over
        if any(word in user_message.lower() for word in ['more', 'other', 'different']):
            # Generate more recommendations
            products = get_recommendations(attributes)
            if products:
                response['reply'] = "Here are some more recommendations for you:"
                response['products'] = products
            else:
                response['reply'] = "I don't have more specific recommendations, but here are some general options:"
                response['products'] = random.sample(PRODUCT_CATALOG, min(6, len(PRODUCT_CATALOG)))
        elif any(word in user_message.lower() for word in ['start over', 'restart', 'new']):
            session['state'] = 'AWAITING_NAME'
            response['reply'] = "Let's start over! What's your name?"
        else:
            response['reply'] = "Is there anything specific you'd like to know about these products, or would you like me to find more options?"
            response['action_buttons'] = [
                UIOption(label="More Recommendations", value="more"),
                UIOption(label="Start Over", value="restart"),
                UIOption(label="Browse All", value="browse_all")
            ]

    session['attributes'] = attributes
    return response

# --- API Endpoints ---
@app.post("/chat", response_model=ChatResponse)
def chat_handler(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    session = SESSIONS.get(session_id, {'state': 'AWAITING_NAME', 'attributes': {}})
    
    # Handle initial greeting
    if not request.session_id and session['state'] == 'AWAITING_NAME':
        response_data = {
            'reply': "Welcome to our store! I'm your personal shopping assistant. What's your name?",
            'action_buttons': []
        }
    elif not request.message or request.message.strip() == "":
        # Handle empty message (welcome case)
        response_data = {
            'reply': "Welcome to our store! I'm your personal shopping assistant. What's your name?",
            'action_buttons': []
        }
    else:
        response_data = process_conversational_turn(session, request.message)
    
    SESSIONS[session_id] = session
    
    return ChatResponse(
        session_id=session_id,
        reply=response_data.get('reply', "I'm not sure how to respond to that."),
        action_buttons=response_data.get('action_buttons'),
        products=response_data.get('products')
    )

@app.post("/new-session")
def new_session_handler(request: NewSessionRequest):
    """Clear an existing session and start fresh"""
    try:
        # Remove the old session
        if request.session_id in SESSIONS:
            del SESSIONS[request.session_id]
            logging.info(f"Cleared session {request.session_id}")
        
        return {"status": "success", "message": "Session cleared successfully"}
    except Exception as e:
        logging.error(f"Error clearing session {request.session_id}: {e}")
        return {"status": "error", "message": str(e)}

# --- Static File Serving ---
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')