"""
RAG (Retrieval-Augmented Generation) System
Combines vector search with LLM for enhanced product recommendations
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
        self.min_similarity_threshold = 0.5
        logger.info("RAG system initialized")

    def retrieve_relevant_products(
        self, query: str, preferences: Dict[str, Any], top_k: int = 10
    ) -> List[Dict[str, Any]]:
        logger.info(f"Retrieving products for query: '{query}'")
        products = self.vector_db.hybrid_search(query, preferences, top_k)
        filtered_products = [
            product for product in products
            if product.get('similarity_score', 0) >= self.min_similarity_threshold
        ]
        logger.info(f"Retrieved {len(filtered_products)} relevant products")
        return filtered_products

    def get_system_stats(self) -> Dict[str, Any]:
        vector_stats = self.vector_db.get_collection_stats()
        return {
            'rag_system': {
                'min_similarity_threshold': self.min_similarity_threshold,
                'vector_database': vector_stats,
                'status': 'active'
            }
        }

rag_system = None

def get_rag_system() -> RAGSystem:
    global rag_system
    if rag_system is None:
        rag_system = RAGSystem()
    return rag_system