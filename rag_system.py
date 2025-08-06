"""
RAG (Retrieval-Augmented Generation) System
Combines vector search with LLM for enhanced product recommendations
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import json

# Import vector database
try:
    from vector_db import get_vector_database, VectorDatabase
except ImportError:
    # Fallback for standalone testing
    from .vector_db import get_vector_database, VectorDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGSystem:
    """
    RAG system for enhanced product recommendations and responses
    """
    
    def __init__(self, vector_db: Optional[VectorDatabase] = None):
        """
        Initialize RAG system
        
        Args:
            vector_db: Optional VectorDatabase instance
        """
        self.vector_db = vector_db or get_vector_database()
        self.min_similarity_threshold = 0.5  # Minimum similarity for recommendations
        
        logger.info("RAG system initialized")
    
    def retrieve_relevant_products(
        self,
        query: str,
        preferences: Dict[str, Any],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant products based on query and preferences
        
        Args:
            query: User query or conversation context
            preferences: User preferences from conversation
            top_k: Number of products to retrieve
            
        Returns:
            List of relevant products with similarity scores
        """
        logger.info(f"Retrieving products for query: '{query}'")
        
        # Use hybrid search for better results
        products = self.vector_db.hybrid_search(query, preferences, top_k)
        
        # Filter by similarity threshold
        filtered_products = [
            product for product in products
            if product.get('similarity_score', 0) >= self.min_similarity_threshold
        ]
        
        logger.info(f"Retrieved {len(filtered_products)} relevant products")
        return filtered_products
    
    def generate_product_context(
        self,
        products: List[Dict[str, Any]],
        max_products: int = 5
    ) -> str:
        """
        Generate context string from retrieved products for LLM
        
        Args:
            products: List of product dictionaries
            max_products: Maximum number of products to include
            
        Returns:
            Formatted context string
        """
        if not products:
            return "No relevant products found in the catalog."
        
        context_parts = ["RELEVANT PRODUCTS FROM CATALOG:"]
        
        for i, product in enumerate(products[:max_products]):
            context_parts.append(f"\n{i+1}. {product['name']}")
            context_parts.append(f"   - Category: {product['category']}")
            context_parts.append(f"   - Price: ${product['price']:.2f}")
            context_parts.append(f"   - Metal: {product['metal']}")
            context_parts.append(f"   - Design: {product['design_type']}")
            
            # Add gemstones if present
            gemstones = product.get('gemstones', [])
            if gemstones and gemstones != ['none']:
                context_parts.append(f"   - Gemstones: {', '.join(gemstones)}")
            
            # Add style tags
            style_tags = product.get('style_tags', [])
            if style_tags:
                context_parts.append(f"   - Style: {', '.join(style_tags)}")
            
            # Add occasion tags
            occasion_tags = product.get('occasion_tags', [])
            if occasion_tags:
                context_parts.append(f"   - Occasions: {', '.join(occasion_tags)}")
            
            # Add similarity score
            similarity = product.get('similarity_score', 0)
            context_parts.append(f"   - Relevance: {similarity:.2f}")
        
        return "\n".join(context_parts)
    
    def enhance_llm_prompt(
        self,
        original_prompt: str,
        user_message: str,
        preferences: Dict[str, Any]
    ) -> str:
        """
        Enhance LLM prompt with retrieved product context
        
        Args:
            original_prompt: Original system prompt
            user_message: User's current message
            preferences: User preferences
            
        Returns:
            Enhanced prompt with product context
        """
        # Create query for product retrieval
        query = user_message
        
        # Add preference context to query
        query_parts = [user_message]
        if preferences.get('category'):
            query_parts.append(f"looking for {preferences['category']}")
        if preferences.get('occasion'):
            query_parts.append(f"for {preferences['occasion']}")
        if preferences.get('recipient'):
            query_parts.append(f"for {preferences['recipient']}")
        
        enhanced_query = " ".join(query_parts)
        
        # Retrieve relevant products
        relevant_products = self.retrieve_relevant_products(
            enhanced_query, 
            preferences, 
            top_k=8
        )
        
        # Generate product context
        product_context = self.generate_product_context(relevant_products)
        
        # Enhance the prompt
        enhanced_prompt = f"""{original_prompt}

**PRODUCT CONTEXT FOR THIS CONVERSATION:**
{product_context}

**INSTRUCTIONS FOR USING PRODUCT CONTEXT:**
1. Use the above product information to make specific recommendations
2. Reference actual product names, prices, and features when suggesting items
3. If the user's request matches well with available products, recommend them confidently
4. If no good matches are found, acknowledge this and suggest alternatives or adjustments
5. Always consider the similarity/relevance scores when making recommendations
6. Provide specific product details (name, price, features) rather than generic descriptions

**CURRENT USER MESSAGE:** {user_message}"""
        
        return enhanced_prompt
    
    def get_recommendation_confidence(
        self,
        products: List[Dict[str, Any]],
        preferences: Dict[str, Any]
    ) -> str:
        """
        Determine confidence level for recommendations
        
        Args:
            products: Retrieved products
            preferences: User preferences
            
        Returns:
            Confidence level: 'high', 'medium', or 'low'
        """
        if not products:
            return 'low'
        
        # Check average similarity score
        avg_similarity = sum(p.get('similarity_score', 0) for p in products) / len(products)
        
        # Check if we have products that match core preferences
        has_category_match = any(
            p.get('category') == preferences.get('category') 
            for p in products
        ) if preferences.get('category') else True
        
        has_budget_match = any(
            p.get('price', 0) <= preferences.get('budget_max', float('inf'))
            for p in products
        ) if preferences.get('budget_max') else True
        
        # Determine confidence
        if avg_similarity > 0.7 and has_category_match and has_budget_match:
            return 'high'
        elif avg_similarity > 0.5 and (has_category_match or has_budget_match):
            return 'medium'
        else:
            return 'low'
    
    def generate_enhanced_response(
        self,
        user_message: str,
        preferences: Dict[str, Any],
        llm_response: str
    ) -> Dict[str, Any]:
        """
        Generate enhanced response with product recommendations
        
        Args:
            user_message: User's message
            preferences: User preferences
            llm_response: LLM's response
            
        Returns:
            Enhanced response with products and metadata
        """
        # Get relevant products
        relevant_products = self.retrieve_relevant_products(
            user_message, 
            preferences, 
            top_k=5
        )
        
        # Get confidence level
        confidence = self.get_recommendation_confidence(relevant_products, preferences)
        
        # Prepare enhanced response
        response = {
            'llm_response': llm_response,
            'products': relevant_products,
            'confidence': confidence,
            'product_count': len(relevant_products),
            'has_high_confidence_matches': confidence == 'high',
            'retrieval_metadata': {
                'query': user_message,
                'preferences_used': preferences,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return response
    
    def should_recommend_products(
        self,
        user_message: str,
        preferences: Dict[str, Any],
        conversation_state: str
    ) -> bool:
        """
        Determine if we should recommend products based on current context
        
        Args:
            user_message: User's message
            preferences: User preferences
            conversation_state: Current conversation state
            
        Returns:
            True if we should recommend products
        """
        # Always recommend if explicitly asked
        recommendation_keywords = [
            'show me', 'recommend', 'suggest', 'looking for',
            'want to see', 'find', 'search', 'browse'
        ]
        
        if any(keyword in user_message.lower() for keyword in recommendation_keywords):
            return True
        
        # Recommend if we have enough preferences
        key_preferences = ['category', 'occasion', 'recipient']
        has_key_preferences = sum(1 for key in key_preferences if preferences.get(key)) >= 1
        
        if has_key_preferences and conversation_state in [
            'ready_for_recommendation', 
            'gathering_preferences',
            'refining_recommendation'
        ]:
            return True
        
        return False
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get RAG system statistics
        
        Returns:
            Dictionary with system stats
        """
        vector_stats = self.vector_db.get_collection_stats()
        
        return {
            'rag_system': {
                'min_similarity_threshold': self.min_similarity_threshold,
                'vector_database': vector_stats,
                'status': 'active'
            }
        }

# Global instance
rag_system = None

def get_rag_system() -> RAGSystem:
    """
    Get or create global RAG system instance
    """
    global rag_system
    if rag_system is None:
        rag_system = RAGSystem()
    return rag_system

if __name__ == "__main__":
    # Test the RAG system
    print("Testing RAG System...")
    
    # Load sample products to initialize vector DB
    try:
        with open("product_catalog_large.json", "r") as f:
            products = json.load(f)
        
        # Initialize vector database
        from vector_db import initialize_vector_database_with_products
        vdb = initialize_vector_database_with_products(products)
        
        # Initialize RAG system
        rag = RAGSystem(vdb)
        
        # Test product retrieval
        preferences = {
            'category': 'ring',
            'occasion': 'engagement',
            'budget_max': 5000
        }
        
        user_message = "I'm looking for an elegant engagement ring"
        
        # Test retrieval
        products = rag.retrieve_relevant_products(user_message, preferences, top_k=3)
        
        print(f"\nRetrieved {len(products)} products:")
        for product in products:
            print(f"- {product['name']} (${product['price']:.2f}, Score: {product['similarity_score']:.3f})")
        
        # Test context generation
        context = rag.generate_product_context(products)
        print(f"\nGenerated context:\n{context}")
        
        # Test confidence
        confidence = rag.get_recommendation_confidence(products, preferences)
        print(f"\nRecommendation confidence: {confidence}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()