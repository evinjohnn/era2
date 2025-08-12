"""
RAG (Retrieval-Augmented Generation) System
Combines vector search with LLM for enhanced product recommendations
Enhanced to understand conversational context and user responses
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from vector_db import get_vector_database, VectorDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGSystem:
    def __init__(self, vector_db: Optional[VectorDatabase] = None):
        self.vector_db = vector_db or get_vector_database()
        self.min_similarity_threshold = 0.4  # Lowered threshold for better recall
        logger.info("Enhanced RAG system initialized")

    def create_contextual_query(self, attributes: Dict[str, Any]) -> str:
        """
        Create a more intelligent query based on the conversational context.
        This method understands the relationship between different attributes.
        """
        query_parts = []
        
        # Occasion-based context
        if attributes.get('occasion'):
            occasion = attributes['occasion']
            if occasion == 'wedding':
                query_parts.extend(['wedding', 'engagement', 'bridal', 'formal', 'romantic'])
            elif occasion == 'birthday':
                query_parts.extend(['birthday', 'celebration', 'gift', 'personal'])
            elif occasion == 'anniversary':
                query_parts.extend(['anniversary', 'romantic', 'love', 'celebration'])
            elif occasion == 'other':
                query_parts.extend(['special', 'unique', 'memorable'])
        
        # Recipient-based context
        if attributes.get('recipient'):
            recipient = attributes['recipient']
            if recipient == 'wife':
                query_parts.extend(['wife', 'spouse', 'romantic', 'elegant', 'sophisticated'])
            elif recipient == 'girlfriend':
                query_parts.extend(['girlfriend', 'romantic', 'young', 'trendy', 'stylish'])
            elif recipient == 'mother':
                query_parts.extend(['mother', 'parent', 'family', 'classic', 'timeless'])
            elif recipient == 'friend':
                query_parts.extend(['friend', 'casual', 'stylish', 'modern', 'fun'])
            elif recipient == 'myself':
                query_parts.extend(['self', 'personal', 'individual', 'unique'])
        
        # Category-based context
        if attributes.get('category'):
            category = attributes['category']
            if category == 'rings':
                query_parts.extend(['ring', 'band', 'finger'])
            elif category == 'necklaces':
                query_parts.extend(['necklace', 'pendant', 'chain'])
            elif category == 'earrings':
                query_parts.extend(['earring', 'stud', 'hoop'])
            elif category == 'bracelets':
                query_parts.extend(['bracelet', 'wrist', 'bangle'])
        
        # Intent-based context
        if attributes.get('intent') == 'special':
            query_parts.extend(['gift', 'special', 'meaningful', 'memorable'])
        elif attributes.get('intent') == 'browse':
            query_parts.extend(['jewelry', 'accessories', 'fashion'])
        
        # Combine all parts into a meaningful query
        if query_parts:
            # Remove duplicates while preserving order
            unique_parts = []
            for part in query_parts:
                if part not in unique_parts:
                    unique_parts.append(part)
            
            query = " ".join(unique_parts)
        else:
            query = "jewelry gift"
        
        logger.info(f"Generated contextual query: '{query}' from attributes: {attributes}")
        return query

    def retrieve_relevant_products(
        self, query: str, preferences: Dict[str, Any], top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Enhanced product retrieval that uses contextual understanding.
        """
        # Create a more intelligent query if we have preferences
        if preferences and any(preferences.values()):
            contextual_query = self.create_contextual_query(preferences)
            # Combine original query with contextual query
            enhanced_query = f"{query} {contextual_query}"
        else:
            enhanced_query = query
        
        logger.info(f"Retrieving products with enhanced query: '{enhanced_query}'")
        
        try:
            # Use the enhanced query for vector search
            products = self.vector_db.hybrid_search(enhanced_query, preferences, top_k * 2)
            
            # Apply similarity threshold and additional filtering
            filtered_products = []
            for product in products:
                similarity_score = product.get('similarity_score', 0)
                if similarity_score >= self.min_similarity_threshold:
                    # Add relevance score based on attribute matching
                    relevance_score = self._calculate_relevance_score(product, preferences)
                    product['relevance_score'] = relevance_score
                    filtered_products.append(product)
            
            # Sort by relevance score (combination of similarity and attribute matching)
            filtered_products.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            logger.info(f"Retrieved {len(filtered_products)} relevant products after filtering")
            return filtered_products[:top_k]
            
        except Exception as e:
            logger.error(f"Error in product retrieval: {e}")
            return []

    def _calculate_relevance_score(self, product: Dict[str, Any], preferences: Dict[str, Any]) -> float:
        """
        Calculate a relevance score based on how well the product matches user preferences.
        """
        base_score = product.get('similarity_score', 0.5)
        attribute_bonus = 0.0
        
        # Check occasion matching
        if preferences.get('occasion') and product.get('occasion_tags'):
            if preferences['occasion'] in product['occasion_tags']:
                attribute_bonus += 0.3
        
        # Check recipient matching
        if preferences.get('recipient') and product.get('recipient_tags'):
            if preferences['recipient'] in product['recipient_tags']:
                attribute_bonus += 0.3
        
        # Check category matching
        if preferences.get('category') and product.get('category'):
            if preferences['category'] == product['category']:
                attribute_bonus += 0.2
        
        # Check style preferences
        if preferences.get('intent') == 'special' and product.get('style_tags'):
            if any(style in ['elegant', 'romantic', 'sophisticated'] for style in product['style_tags']):
                attribute_bonus += 0.1
        
        # Combine base similarity with attribute bonus
        final_score = min(1.0, base_score + attribute_bonus)
        return final_score

    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        vector_stats = self.vector_db.get_collection_stats()
        return {
            'rag_system': {
                'min_similarity_threshold': self.min_similarity_threshold,
                'vector_database': vector_stats,
                'status': 'active',
                'enhanced_features': [
                    'contextual_query_generation',
                    'attribute_based_scoring',
                    'intelligent_filtering'
                ]
            }
        }

    def get_recommendation_explanation(self, product: Dict[str, Any], preferences: Dict[str, Any]) -> str:
        """
        Generate an explanation for why a product was recommended.
        """
        reasons = []
        
        if preferences.get('occasion'):
            if product.get('occasion_tags') and preferences['occasion'] in product['occasion_tags']:
                reasons.append(f"Perfect for {preferences['occasion']} occasions")
        
        if preferences.get('recipient'):
            if product.get('recipient_tags') and preferences['recipient'] in product['recipient_tags']:
                reasons.append(f"Ideal for {preferences['recipient']}")
        
        if product.get('style_tags'):
            style_desc = ", ".join(product['style_tags'][:2])
            reasons.append(f"Features a {style_desc} style")
        
        if reasons:
            return " | ".join(reasons)
        else:
            return "Selected based on your preferences"

rag_system = None

def get_rag_system() -> RAGSystem:
    global rag_system
    if rag_system is None:
        rag_system = RAGSystem()
    return rag_system