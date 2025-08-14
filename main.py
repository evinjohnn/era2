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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

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
        
        PRODUCT_CATALOG = []
        for product in products_from_db:
            product_dict = {k: v for k, v in product.__dict__.items() if not k.startswith('_')}
            PRODUCT_CATALOG.append(product_dict)
                
        if PRODUCT_CATALOG:
            # IMPORTANT: This now ONLY initializes the connection, it doesn't re-index.
            # The one-time indexing should be done via a separate script or build command.
            rag_system = get_rag_system()
            # This line ensures the global catalog in vector_db.py is set for fallback searches
            get_vector_database().PRODUCT_CATALOG = PRODUCT_CATALOG
            logging.info(f"Application startup complete with RAG system. Loaded {len(PRODUCT_CATALOG)} products.")
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
def get_recommendations(attributes: dict) -> List[dict]:
    """Get product recommendations based on user attributes with improved matching"""
    try:
        # Build search query based on available attributes
        search_terms = []
        
        if attributes.get('occasion'):
            search_terms.append(attributes['occasion'])
        
        if attributes.get('recipient'):
            search_terms.append(attributes['recipient'])
        
        if attributes.get('category'):
            search_terms.append(attributes['category'])
        
        if attributes.get('metal'):
            search_terms.append(attributes['metal'])
        
        if attributes.get('style'):
            search_terms.append(attributes['style'])
        
        if attributes.get('gemstone'):
            search_terms.append(attributes['gemstone'])
        
        # If we have search terms, use RAG system
        if search_terms:
            query = " ".join(search_terms)
            logging.info(f"Searching with query: {query}")
            
            # Get RAG recommendations
            rag_products = rag_system.get_recommendations(query, limit=15)
            
            if rag_products:
                # Convert to clean dictionaries and apply comprehensive filtering
                clean_products = []
                budget_max = attributes.get('budget_max')
                
                for product in rag_products:
                    if isinstance(product, dict):
                        product_dict = product
                    else:
                        # Handle SQLAlchemy objects if needed
                        product_dict = {
                            'id': getattr(product, 'id', None),
                            'name': getattr(product, 'name', ''),
                            'description': getattr(product, 'description', ''),
                            'price': getattr(product, 'price', 0.0),
                            'category': getattr(product, 'category', ''),
                            'metal': getattr(product, 'metal', ''),
                            'style': getattr(product, 'style', ''),
                            'gemstone': getattr(product, 'gemstone', ''),
                            'style_tags': getattr(product, 'style_tags', []),
                            'image_url': getattr(product, 'image_url', '')
                        }
                    
                    # Apply comprehensive attribute matching
                    match_score = calculate_match_score(product_dict, attributes)
                    
                    # Apply budget filter if specified
                    if budget_max and product_dict.get('price', 0) > budget_max:
                        continue
                    
                    # Only include products with good match scores
                    if match_score >= 0.3:  # Minimum 30% match
                        product_dict['match_score'] = match_score
                        clean_products.append(product_dict)
                
                # Sort by match score and price
                clean_products.sort(key=lambda x: (-x.get('match_score', 0), x.get('price', 0)))
                
                logging.info(f"Found {len(clean_products)} well-matched products within budget")
                return clean_products[:6]  # Return top 6 results
        
        # Fallback: use attribute-based filtering on PRODUCT_CATALOG
        if PRODUCT_CATALOG:
            logging.info("Using attribute-based filtering on product catalog")
            filtered_products = filter_products_by_attributes(PRODUCT_CATALOG, attributes)
            
            if filtered_products:
                # Sort by relevance and price
                budget_max = attributes.get('budget_max')
                if budget_max:
                    filtered_products.sort(key=lambda x: (x.get('price', 0), x.get('name', '')))
                
                logging.info(f"Found {len(filtered_products)} products using attribute filtering")
                return filtered_products[:6]
        
        return []
        
    except Exception as e:
        logging.error(f"Error in get_recommendations: {e}")
        return []

def calculate_match_score(product: dict, attributes: dict) -> float:
    """Calculate how well a product matches user attributes (0.0 to 1.0)"""
    score = 0.0
    total_weight = 0.0
    
    # Category matching (high weight)
    if attributes.get('category') and product.get('category'):
        if attributes['category'].lower() == product['category'].lower():
            score += 0.3
        total_weight += 0.3
    
    # Metal matching (high weight)
    if attributes.get('metal') and product.get('metal'):
        if attributes['metal'].lower() == product['metal'].lower():
            score += 0.25
        total_weight += 0.25
    
    # Style matching (medium weight)
    if attributes.get('style') and product.get('style'):
        if attributes['style'].lower() == product['style'].lower():
            score += 0.2
        total_weight += 0.2
    
    # Gemstone matching (medium weight)
    if attributes.get('gemstone') and product.get('gemstone'):
        if attributes['gemstone'].lower() == product['gemstone'].lower():
            score += 0.15
        total_weight += 0.15
    
    # Occasion and recipient matching (lower weight)
    if attributes.get('occasion') and product.get('style_tags'):
        if any(attributes['occasion'].lower() in tag.lower() for tag in product['style_tags']):
            score += 0.05
        total_weight += 0.05
    
    if attributes.get('recipient') and product.get('style_tags'):
        if any(attributes['recipient'].lower() in tag.lower() for tag in product['style_tags']):
            score += 0.05
        total_weight += 0.05
    
    # Normalize score
    if total_weight > 0:
        return score / total_weight
    return 0.0

def filter_products_by_attributes(products: List[dict], attributes: dict) -> List[dict]:
    """Filter products based on user attributes"""
    filtered = []
    budget_max = attributes.get('budget_max')
    
    for product in products:
        # Apply budget filter
        if budget_max and product.get('price', 0) > budget_max:
            continue
        
        # Apply category filter
        if attributes.get('category') and product.get('category'):
            if attributes['category'].lower() not in product['category'].lower():
                continue
        
        # Apply metal filter
        if attributes.get('metal') and product.get('metal'):
            if attributes['metal'].lower() not in product['metal'].lower():
                continue
        
        # Apply style filter
        if attributes.get('style') and product.get('style'):
            if attributes['style'].lower() not in product['style'].lower():
                continue
        
        # Apply gemstone filter
        if attributes.get('gemstone') and product.get('gemstone'):
            if attributes['gemstone'].lower() not in product['gemstone'].lower():
                continue
        
        filtered.append(product)
    
    return filtered

# --- Conversational Flow State Machine ---
def process_turn(session: Dict, user_message: str) -> Dict:
    state = session.get('state', 'AWAITING_NAME')
    attributes = session.get('attributes', {})
    response = {}

    # Log the current state and user message for debugging
    logging.info(f"Conversation state: {state}, User message: '{user_message}', Attributes: {attributes}")
    
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
            response['action_buttons'] = [
                UIOption(label="Show More", value="show_more"),
                UIOption(label="Filter by Category", value="filter_category"),
                UIOption(label="Type your answer", value="__type__")
            ]

    elif state == 'AWAITING_OCCASION':
        attributes['occasion'] = user_message.lower()
        session['state'] = 'AWAITING_RECIPIENT'
        response['reply'] = f"Perfect! A {attributes['occasion']} gift. Who is this gift for? (e.g., wife, husband, girlfriend, boyfriend, mother, father, friend)"
        response['action_buttons'] = [
            UIOption(label="Wife", value="wife"),
            UIOption(label="Husband", value="husband"),
            UIOption(label="Girlfriend", value="girlfriend"),
            UIOption(label="Boyfriend", value="boyfriend"),
            UIOption(label="Mother", value="mother"),
            UIOption(label="Type your answer", value="__type__")
        ]
    
    elif state == 'AWAITING_RECIPIENT':
        attributes['recipient'] = user_message.lower()
        session['state'] = 'AWAITING_CATEGORY'
        response['reply'] = f"Great! I'll help you find the perfect gift for your {attributes['recipient']}. What type of jewelry are you looking for? (e.g., rings, necklaces, earrings, pendants, bracelets, watches)"
        response['action_buttons'] = [
            UIOption(label="Rings", value="rings"),
            UIOption(label="Necklaces", value="necklaces"),
            UIOption(label="Earrings", value="earrings"),
            UIOption(label="Pendants", value="pendants"),
            UIOption(label="Bracelets", value="bracelets"),
            UIOption(label="Watches", value="watches"),
            UIOption(label="Type your answer", value="__type__")
        ]
    
    elif state == 'AWAITING_CATEGORY':
        attributes['category'] = user_message.lower()
        session['state'] = 'AWAITING_METAL'
        response['reply'] = f"Perfect! {attributes['category'].title()} are a great choice. What metal type would you prefer? (e.g., gold, silver, platinum, rose gold, white gold)"
        response['action_buttons'] = [
            UIOption(label="Gold", value="gold"),
            UIOption(label="Silver", value="silver"),
            UIOption(label="Platinum", value="platinum"),
            UIOption(label="Rose Gold", value="rose gold"),
            UIOption(label="White Gold", value="white gold"),
            UIOption(label="Type your answer", value="__type__")
        ]
    
    elif state == 'AWAITING_METAL':
        attributes['metal'] = user_message.lower()
        session['state'] = 'AWAITING_STYLE'
        response['reply'] = f"Great choice! {attributes['metal'].title()} is beautiful. What style are you looking for? (e.g., classic, modern, vintage, minimalist, bold, elegant)"
        response['action_buttons'] = [
            UIOption(label="Classic", value="classic"),
            UIOption(label="Modern", value="modern"),
            UIOption(label="Vintage", value="vintage"),
            UIOption(label="Minimalist", value="minimalist"),
            UIOption(label="Bold", value="bold"),
            UIOption(label="Elegant", value="elegant"),
            UIOption(label="Type your answer", value="__type__")
        ]
    
    elif state == 'AWAITING_STYLE':
        attributes['style'] = user_message.lower()
        session['state'] = 'AWAITING_BUDGET'
        response['reply'] = f"Perfect! {attributes['style'].title()} style is a great choice. What's your budget range for this gift?"
        response['action_buttons'] = [
            UIOption(label="Under $100", value="under_100"),
            UIOption(label="$100 - $500", value="100_500"),
            UIOption(label="$500 - $1000", value="500_1000"),
            UIOption(label="$1000 - $2500", value="1000_2500"),
            UIOption(label="$2500+", value="2500_plus"),
            UIOption(label="Type your answer", value="__type__")
        ]
    
    elif state == 'AWAITING_BUDGET':
        # Parse budget from user input or button selection
        budget_input = user_message.lower()
        if 'under' in budget_input or '100' in budget_input:
            attributes['budget_max'] = 100.0
        elif '500' in budget_input:
            attributes['budget_max'] = 500.0
        elif '1000' in budget_input:
            attributes['budget_max'] = 1000.0
        elif '2500' in budget_input:
            attributes['budget_max'] = 2500.0
        elif 'plus' in budget_input or '+' in budget_input:
            attributes['budget_max'] = 10000.0  # High-end budget
        else:
            # Try to extract numeric value from text
            import re
            numbers = re.findall(r'\d+', budget_input)
            if numbers:
                attributes['budget_max'] = float(numbers[-1])
            else:
                attributes['budget_max'] = 1000.0  # Default budget
        
        session['state'] = 'AWAITING_GEMSTONE'
        response['reply'] = f"Great! Budget set to ${attributes['budget_max']:.0f}. Do you have a preference for gemstones? (e.g., diamond, sapphire, ruby, emerald, pearl, none)"
        response['action_buttons'] = [
            UIOption(label="Diamond", value="diamond"),
            UIOption(label="Sapphire", value="sapphire"),
            UIOption(label="Ruby", value="ruby"),
            UIOption(label="Emerald", value="emerald"),
            UIOption(label="Pearl", value="pearl"),
            UIOption(label="No Gemstone", value="none"),
            UIOption(label="Type your answer", value="__type__")
        ]
    
    elif state == 'AWAITING_GEMSTONE':
        attributes['gemstone'] = user_message.lower()
        session['state'] = 'SHOWING_SUMMARY'
        
        # Create a professional summary of all collected preferences
        summary = f"Excellent! I've collected all your preferences. Let me confirm the details:\n\n"
        summary += f"**Occasion**: {attributes.get('occasion', 'Not specified').title()}\n"
        summary += f"**Recipient**: {attributes.get('recipient', 'Not specified').title()}\n"
        summary += f"**Jewelry Type**: {attributes.get('category', 'Not specified').title()}\n"
        summary += f"**Metal**: {attributes.get('metal', 'Not specified').title()}\n"
        summary += f"**Style**: {attributes.get('style', 'Not specified').title()}\n"
        summary += f"**Budget**: ${attributes.get('budget_max', 'Not specified'):.0f}\n"
        summary += f"**Gemstone**: {attributes.get('gemstone', 'Not specified').title()}\n\n"
        summary += f"Please confirm if these details are correct, and I'll search our collection for the perfect match."
        
        response['reply'] = summary
        response['action_buttons'] = [
            UIOption(label="Confirm & Find Jewelry", value="find_jewelry"),
            UIOption(label="Adjust Preferences", value="adjust_filter"),
            UIOption(label="Start Over", value="start_over")
        ]
    
    elif state == 'SHOWING_SUMMARY':
        if 'yes' in user_message.lower() or 'find' in user_message.lower() or 'perfect' in user_message.lower() or 'confirm' in user_message.lower():
            session['state'] = 'RECOMMENDING'
            products = get_recommendations(attributes)
            if products:
                response['reply'] = f"Perfect! I've found {len(products)} excellent options that match your preferences for {attributes.get('occasion', '')} {attributes.get('category', 'jewelry')} in {attributes.get('metal', '')} with {attributes.get('style', '')} style. Here are your personalized recommendations:"
                response['products'] = products
                # Add action buttons after recommendations
                response['action_buttons'] = [
                    UIOption(label="Show Similar Items", value="similar_design"),
                    UIOption(label="Adjust Search Criteria", value="adjust_filter"),
                    UIOption(label="Type your answer", value="__type__")
                ]
            else:
                response['reply'] = f"I've searched our collection for {attributes.get('occasion', '')} {attributes.get('category', 'jewelry')} in {attributes.get('metal', '')} with {attributes.get('style', '')} style and {attributes.get('gemstone', '')} gemstone under ${attributes.get('budget_max', 0):.0f}, but couldn't find an exact match. However, here are some excellent alternatives you might consider:"
                response['products'] = random.sample(PRODUCT_CATALOG, 4) if PRODUCT_CATALOG else []
                response['action_buttons'] = [
                    UIOption(label="Show Similar Items", value="similar_design"),
                    UIOption(label="Adjust Search Criteria", value="adjust_filter"),
                    UIOption(label="Type your answer", value="__type__")
                ]
                session['state'] = 'BROWSING'
        else:
            session['state'] = 'ADJUSTING_FILTERS'
            response['reply'] = "No problem! What would you like to adjust? (occasion, recipient, category, metal, style, budget, or gemstone)"
            response['action_buttons'] = [
                UIOption(label="Change Occasion", value="change_occasion"),
                UIOption(label="Change Recipient", value="change_recipient"),
                UIOption(label="Change Category", value="change_category"),
                UIOption(label="Change Metal", value="change_metal"),
                UIOption(label="Change Style", value="change_style"),
                UIOption(label="Change Budget", value="change_budget"),
                UIOption(label="Change Gemstone", value="change_gemstone"),
                UIOption(label="Start Over", value="start_over"),
                UIOption(label="Type your answer", value="__type__")
            ]
    
    elif state == 'RECOMMENDING':
        # User can ask for similar items or adjust filters
        if any(word in user_message.lower() for word in ['similar', 'like', 'same', 'more']):
            response['reply'] = "I'll search for more items with similar design characteristics. Let me find additional options for you..."
            # Re-run recommendations with current attributes
            products = get_recommendations(attributes)
            if products:
                response['products'] = products
                response['action_buttons'] = [
                    UIOption(label="Adjust Search Criteria", value="adjust_filter"),
                    UIOption(label="Type your answer", value="__type__")
                ]
            else:
                response['reply'] = "I couldn't find additional similar items with your current criteria. Would you like to adjust your search parameters?"
                response['action_buttons'] = [
                    UIOption(label="Adjust Search Criteria", value="adjust_filter"),
                    UIOption(label="Start Over", value="start_over"),
                    UIOption(label="Type your answer", value="__type__")
                ]
        elif any(word in user_message.lower() for word in ['adjust', 'change', 'different', 'filter']):
            session['state'] = 'ADJUSTING_FILTERS'
            response['reply'] = "Let's refine your search criteria. What would you like to modify? (occasion, recipient, category, metal, style, budget, or gemstone)"
            response['action_buttons'] = [
                UIOption(label="Change Occasion", value="change_occasion"),
                UIOption(label="Change Recipient", value="change_recipient"),
                UIOption(label="Change Category", value="change_category"),
                UIOption(label="Change Metal", value="change_metal"),
                UIOption(label="Change Style", value="change_style"),
                UIOption(label="Change Budget", value="change_budget"),
                UIOption(label="Change Gemstone", value="change_gemstone"),
                UIOption(label="Start Over", value="start_over"),
                UIOption(label="Type your answer", value="__type__")
            ]
        else:
            response['reply'] = "I'm here to assist you with your jewelry search. You can request similar items, adjust your search criteria, or start a new search."
            response['action_buttons'] = [
                UIOption(label="Show Similar Items", value="similar_design"),
                UIOption(label="Adjust Search Criteria", value="adjust_filter"),
                UIOption(label="Start Over", value="start_over"),
                UIOption(label="Type your answer", value="__type__")
            ]
    
    elif state == 'BROWSING':
        # User is browsing products, can ask for more or filter
        if any(word in user_message.lower() for word in ['more', 'show', 'browse', 'explore']):
            response['reply'] = "I'll show you more products to browse through."
            # Return more random products
            if PRODUCT_CATALOG:
                response['products'] = random.sample(PRODUCT_CATALOG, 4)
                response['action_buttons'] = [
                    UIOption(label="Show More", value="show_more"),
                    UIOption(label="Filter by Category", value="filter_category"),
                    UIOption(label="Type your answer", value="__type__")
                ]
            else:
                response['reply'] = "I don't have more products to show right now. Would you like to start a new search?"
                response['action_buttons'] = [
                    UIOption(label="Start Over", value="start_over"),
                    UIOption(label="Type your answer", value="__type__")
                ]
        elif any(word in user_message.lower() for word in ['filter', 'category', 'type']):
            session['state'] = 'AWAITING_CATEGORY'
            response['reply'] = "What type of jewelry would you like to browse? (e.g., rings, necklaces, earrings, pendants, bracelets, watches)"
            response['action_buttons'] = [
                UIOption(label="Rings", value="rings"),
                UIOption(label="Necklaces", value="necklaces"),
                UIOption(label="Earrings", value="earrings"),
                UIOption(label="Pendants", value="pendants"),
                UIOption(label="Bracelets", value="bracelets"),
                UIOption(label="Watches", value="watches"),
                UIOption(label="Type your answer", value="__type__")
            ]
        else:
            response['reply'] = "I'm here to help you browse our jewelry collection. You can ask for more products, filter by category, or start a new search."
            response['action_buttons'] = [
                UIOption(label="Show More", value="show_more"),
                UIOption(label="Filter by Category", value="filter_category"),
                UIOption(label="Start Over", value="start_over"),
                UIOption(label="Type your answer", value="__type__")
            ]
    
    elif state == 'ADJUSTING_FILTERS':
        # Handle filter adjustments
        if 'occasion' in user_message.lower():
            session['state'] = 'AWAITING_OCCASION'
            response['reply'] = "What's the occasion for this gift? (e.g., birthday, anniversary, wedding, graduation, holiday)"
            response['action_buttons'] = [
                UIOption(label="Birthday", value="birthday"),
                UIOption(label="Anniversary", value="anniversary"),
                UIOption(label="Wedding", value="wedding"),
                UIOption(label="Graduation", value="graduation"),
                UIOption(label="Holiday", value="holiday"),
                UIOption(label="Type your answer", value="__type__")
            ]
        elif 'recipient' in user_message.lower():
            session['state'] = 'AWAITING_RECIPIENT'
            response['reply'] = "Who is this gift for? (e.g., wife, husband, girlfriend, boyfriend, mother, father, friend)"
            response['action_buttons'] = [
                UIOption(label="Wife", value="wife"),
                UIOption(label="Husband", value="husband"),
                UIOption(label="Girlfriend", value="girlfriend"),
                UIOption(label="Boyfriend", value="boyfriend"),
                UIOption(label="Mother", value="mother"),
                UIOption(label="Type your answer", value="__type__")
            ]
        elif 'category' in user_message.lower():
            session['state'] = 'AWAITING_CATEGORY'
            response['reply'] = "What type of jewelry are you looking for? (e.g., rings, necklaces, earrings, pendants, bracelets, watches)"
            response['action_buttons'] = [
                UIOption(label="Rings", value="rings"),
                UIOption(label="Necklaces", value="necklaces"),
                UIOption(label="Earrings", value="earrings"),
                UIOption(label="Pendants", value="pendants"),
                UIOption(label="Bracelets", value="bracelets"),
                UIOption(label="Watches", value="watches"),
                UIOption(label="Type your answer", value="__type__")
            ]
        elif 'metal' in user_message.lower():
            session['state'] = 'AWAITING_METAL'
            response['reply'] = "What metal type would you prefer? (e.g., gold, silver, platinum, rose gold, white gold)"
            response['action_buttons'] = [
                UIOption(label="Gold", value="gold"),
                UIOption(label="Silver", value="silver"),
                UIOption(label="Platinum", value="platinum"),
                UIOption(label="Rose Gold", value="rose gold"),
                UIOption(label="White Gold", value="white gold"),
                UIOption(label="Type your answer", value="__type__")
            ]
        elif 'style' in user_message.lower():
            session['state'] = 'AWAITING_STYLE'
            response['reply'] = "What style are you looking for? (e.g., classic, modern, vintage, minimalist, bold, elegant)"
            response['action_buttons'] = [
                UIOption(label="Classic", value="classic"),
                UIOption(label="Modern", value="modern"),
                UIOption(label="Vintage", value="vintage"),
                UIOption(label="Minimalist", value="minimalist"),
                UIOption(label="Bold", value="bold"),
                UIOption(label="Elegant", value="elegant"),
                UIOption(label="Type your answer", value="__type__")
            ]
        elif 'budget' in user_message.lower():
            session['state'] = 'AWAITING_BUDGET'
            response['reply'] = "What's your budget range for this gift?"
            response['action_buttons'] = [
                UIOption(label="Under $100", value="under_100"),
                UIOption(label="$100 - $500", value="100_500"),
                UIOption(label="$500 - $1000", value="500_1000"),
                UIOption(label="$1000 - $2500", value="1000_2500"),
                UIOption(label="$2500+", value="2500_plus"),
                UIOption(label="Type your answer", value="__type__")
            ]
        elif 'gemstone' in user_message.lower():
            session['state'] = 'AWAITING_GEMSTONE'
            response['reply'] = "Do you have a preference for gemstones? (e.g., diamond, sapphire, ruby, emerald, pearl, none)"
            response['action_buttons'] = [
                UIOption(label="Diamond", value="diamond"),
                UIOption(label="Sapphire", value="sapphire"),
                UIOption(label="Ruby", value="ruby"),
                UIOption(label="Emerald", value="emerald"),
                UIOption(label="Pearl", value="pearl"),
                UIOption(label="No Gemstone", value="none"),
                UIOption(label="Type your answer", value="__type__")
            ]
        else:
            response['reply'] = "I can help you adjust: occasion, recipient, category, metal, style, budget, or gemstone. What would you like to change?"
            response['action_buttons'] = [
                UIOption(label="Change Occasion", value="change_occasion"),
                UIOption(label="Change Recipient", value="change_recipient"),
                UIOption(label="Change Category", value="change_category"),
                UIOption(label="Change Metal", value="change_metal"),
                UIOption(label="Change Style", value="change_style"),
                UIOption(label="Change Budget", value="change_budget"),
                UIOption(label="Change Gemstone", value="change_gemstone"),
                UIOption(label="Start Over", value="start_over"),
                UIOption(label="Type your answer", value="__type__")
            ]
    
    else:
        # Fallback for any unexpected state
        response['reply'] = "I'm here to help you find the perfect jewelry! What would you like to do?"
        response['action_buttons'] = [
            UIOption(label="Start Over", value="start_over"),
            UIOption(label="Browse Products", value="browse"),
            UIOption(label="Type your answer", value="__type__")
        ]

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
    
    # Ensure we always have a valid reply
    if not response_data.get('reply'):
        response_data['reply'] = "I'm here to help you find the perfect jewelry! How can I assist you today?"
    
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

# --- Product API Endpoints ---
class ProductRequest(BaseModel):
    session_id: Optional[str] = None
    page: int = 1
    limit: int = 5
    category: Optional[str] = None

@app.post("/products/new-arrivals")
async def new_arrivals_handler(request: ProductRequest):
    """Get newly added products with pagination"""
    try:
        # For demo purposes, return a subset of products
        # In production, you'd query by creation date
        start_idx = (request.page - 1) * request.limit
        end_idx = start_idx + request.limit
        
        # Get products from catalog
        available_products = PRODUCT_CATALOG[start_idx:end_idx] if PRODUCT_CATALOG else []
        total_products = len(PRODUCT_CATALOG) if PRODUCT_CATALOG else 0
        total_pages = (total_products + request.limit - 1) // request.limit
        
        return {
            "products": available_products,
            "total_products": total_products,
            "total_pages": total_pages,
            "current_page": request.page,
            "limit": request.limit
        }
    except Exception as e:
        logging.error(f"Error fetching new arrivals: {e}")
        return {"error": "Failed to fetch new arrivals"}

@app.post("/products/categories")
async def categories_handler(request: ProductRequest):
    """Get jewelry categories with product counts"""
    try:
        # Define jewelry categories
        categories = [
            {
                "name": "Rings",
                "description": "Engagement rings, wedding bands, and fashion rings",
                "product_count": len([p for p in PRODUCT_CATALOG if 'ring' in p.get('category', '').lower() or 'ring' in p.get('tags', [])]),
                "icon": "diamond"
            },
            {
                "name": "Necklaces",
                "description": "Pendants, chains, and statement necklaces",
                "product_count": len([p for p in PRODUCT_CATALOG if 'necklace' in p.get('category', '').lower() or 'necklace' in p.get('tags', [])]),
                "icon": "favorite"
            },
            {
                "name": "Earrings",
                "description": "Studs, hoops, and drop earrings",
                "product_count": len([p for p in PRODUCT_CATALOG if 'earring' in p.get('category', '').lower() or 'earring' in p.get('tags', [])]),
                "icon": "star"
            },
            {
                "name": "Bracelets",
                "description": "Charm bracelets, bangles, and tennis bracelets",
                "product_count": len([p for p in PRODUCT_CATALOG if 'bracelet' in p.get('category', '').lower() or 'bracelet' in p.get('tags', [])]),
                "icon": "circle"
            },
            {
                "name": "Watches",
                "description": "Luxury timepieces and smartwatches",
                "product_count": len([p for p in PRODUCT_CATALOG if 'watch' in p.get('category', '').lower() or 'watch' in p.get('tags', [])]),
                "icon": "schedule"
            },
            {
                "name": "Pendants",
                "description": "Charm pendants and gemstone pendants",
                "product_count": len([p for p in PRODUCT_CATALOG if 'pendant' in p.get('category', '').lower() or 'pendant' in p.get('tags', [])]),
                "icon": "favorite_border"
            }
        ]
        
        return {"categories": categories}
    except Exception as e:
        logging.error(f"Error fetching categories: {e}")
        return {"error": "Failed to fetch categories"}

@app.post("/products/category")
async def category_products_handler(request: ProductRequest):
    """Get products from a specific category with pagination"""
    try:
        if not request.category:
            return {"error": "Category parameter is required"}
        
        # Filter products by category
        category_products = []
        for product in PRODUCT_CATALOG:
            category_match = (
                request.category.lower() in product.get('category', '').lower() or
                request.category.lower() in [tag.lower() for tag in product.get('tags', [])]
            )
            if category_match:
                category_products.append(product)
        
        # Apply pagination
        start_idx = (request.page - 1) * request.limit
        end_idx = start_idx + request.limit
        paginated_products = category_products[start_idx:end_idx]
        
        total_products = len(category_products)
        total_pages = (total_products + request.limit - 1) // request.limit
        
        return {
            "products": paginated_products,
            "total_products": total_products,
            "total_pages": total_pages,
            "current_page": request.page,
            "limit": request.limit,
            "category": request.category
        }
    except Exception as e:
        logging.error(f"Error fetching category products: {e}")
        return {"error": "Failed to fetch category products"}

# --- Analytics Endpoint ---
@app.post("/analytics/track")
async def analytics_track_handler(request: dict):
    """Track user interactions for analytics"""
    try:
        # Log the analytics data
        logging.info(f"Analytics: {request}")
        
        # In production, you'd store this in a database
        # For now, just log it
        
        return {"status": "success", "message": "Analytics tracked"}
    except Exception as e:
        logging.error(f"Error tracking analytics: {e}")
        return {"error": "Failed to track analytics"}

# --- Static Files & Dashboard ---
app.mount("/static", StaticFiles(directory="static"), name="static")
create_staff_dashboard_routes(app) # Add dashboard routes

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')
