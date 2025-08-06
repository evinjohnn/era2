"""
Vector Database Setup with ChromaDB
Handles product embeddings and semantic search for the retail AI assistant
"""

import chromadb
from chromadb.config import Settings
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
import numpy as np
import os
from datetime import datetime
import hashlib
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorDatabase:
    """
    ChromaDB-based vector database for product embeddings and semantic search
    """
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize ChromaDB client and embedding model
        
        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        self.persist_directory = persist_directory
        self.collection_name = "jewelry_products"
        
        # Initialize ChromaDB client with basic optimizations
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding model with optimizations
        logger.info("Loading embedding model...")
        self.embedding_model = SentenceTransformer(
            'all-MiniLM-L6-v2',
            device='cpu',  # Explicitly use CPU for consistency
            cache_folder="./.sentence_transformers_cache"
        )
        
        # Optimize model for inference
        self.embedding_model.eval()
        
        self.embedding_dimension = 384  # Dimension for all-MiniLM-L6-v2
        
        # Initialize query cache for performance
        self.query_cache = {}
        self.max_cache_size = 100
        
        # Initialize collection
        self.collection = self._get_or_create_collection()
        
        # Warm up the embedding model
        logger.info("Warming up embedding model...")
        start_time = time.time()
        _ = self.embedding_model.encode(["test query for warmup"], show_progress_bar=False)
        warmup_time = (time.time() - start_time) * 1000
        logger.info(f"Model warmup completed in {warmup_time:.2f}ms")
        
        logger.info(f"Vector database initialized with {self.collection.count()} products")
    
    def _get_or_create_collection(self):
        """
        Get existing collection or create new one
        """
        try:
            # Try to get existing collection
            collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Found existing collection: {self.collection_name}")
            return collection
        except Exception:
            # Create new collection
            logger.info(f"Creating new collection: {self.collection_name}")
            return self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "description": "Jewelry product embeddings for semantic search",
                    "embedding_model": "all-MiniLM-L6-v2",
                    "created_at": datetime.now().isoformat()
                }
            )
    
    def create_product_text_for_embedding(self, product: Dict[str, Any]) -> str:
        """
        Create comprehensive text representation of product for embedding
        
        Args:
            product: Product dictionary
            
        Returns:
            Text representation for embedding
        """
        text_parts = []
        
        # Core product information
        text_parts.append(f"Product: {product.get('name', '')}")
        text_parts.append(f"Category: {product.get('category', '')}")
        text_parts.append(f"Metal: {product.get('metal', '')}")
        text_parts.append(f"Design: {product.get('design_type', '')}")
        
        # Gemstones
        gemstones = product.get('gemstones', [])
        if gemstones and gemstones != ['none']:
            text_parts.append(f"Gemstones: {', '.join(gemstones)}")
        
        # Style tags
        style_tags = product.get('style_tags', [])
        if style_tags:
            text_parts.append(f"Style: {', '.join(style_tags)}")
        
        # Occasion tags
        occasion_tags = product.get('occasion_tags', [])
        if occasion_tags:
            text_parts.append(f"Occasions: {', '.join(occasion_tags)}")
        
        # Recipient tags
        recipient_tags = product.get('recipient_tags', [])
        if recipient_tags:
            text_parts.append(f"For: {', '.join(recipient_tags)}")
        
        # Description
        description = product.get('description', '')
        if description:
            text_parts.append(f"Description: {description}")
        
        # Price range context
        price = product.get('price', 0)
        if price > 0:
            if price < 100:
                text_parts.append("Price range: budget-friendly affordable")
            elif price < 500:
                text_parts.append("Price range: mid-range moderate")
            elif price < 1000:
                text_parts.append("Price range: premium quality")
            else:
                text_parts.append("Price range: luxury high-end")
        
        return " | ".join(text_parts)
    
    def add_products(self, products: List[Dict[str, Any]]) -> None:
        """
        Add products to vector database with embeddings
        
        Args:
            products: List of product dictionaries
        """
        logger.info(f"Adding {len(products)} products to vector database...")
        
        # Prepare data for batch insertion
        ids = []
        documents = []
        metadatas = []
        
        for product in products:
            product_id = product.get('id', '')
            if not product_id:
                continue
                
            # Create text for embedding
            document_text = self.create_product_text_for_embedding(product)
            
            # Prepare metadata (ChromaDB will handle JSON serialization)
            metadata = {
                'product_id': product_id,
                'name': product.get('name', ''),
                'category': product.get('category', ''),
                'price': float(product.get('price', 0)),
                'metal': product.get('metal', ''),
                'design_type': product.get('design_type', ''),
                'gemstones': json.dumps(product.get('gemstones', [])),
                'style_tags': json.dumps(product.get('style_tags', [])),
                'occasion_tags': json.dumps(product.get('occasion_tags', [])),
                'recipient_tags': json.dumps(product.get('recipient_tags', [])),
                'image_url': product.get('image_url', ''),
                'description': product.get('description', '')
            }
            
            ids.append(product_id)
            documents.append(document_text)
            metadatas.append(metadata)
        
        # Batch insert to ChromaDB
        if ids:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"Successfully added {len(ids)} products to vector database")
    
    def semantic_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search with optional filters and caching
        
        Args:
            query: Search query
            filters: Optional filters (category, price range, etc.)
            top_k: Number of results to return
            
        Returns:
            List of matching products with similarity scores
        """
        # Create cache key
        cache_key = self._generate_cache_key(query, filters, top_k)
        
        # Check cache first
        if cache_key in self.query_cache:
            logger.info(f"Cache hit for query: '{query}'")
            return self.query_cache[cache_key]
        
        start_time = time.time()
        logger.info(f"Performing semantic search for: '{query}' with filters: {filters}")
        
        # Build ChromaDB where clause for filters
        where_clause = {}
        if filters:
            if 'category' in filters and filters['category']:
                where_clause['category'] = filters['category']
            
            if 'metal' in filters and filters['metal']:
                where_clause['metal'] = filters['metal']
            
            if 'max_price' in filters and filters['max_price']:
                where_clause['price'] = {"$lte": float(filters['max_price'])}
            
            if 'min_price' in filters and filters['min_price']:
                if 'price' in where_clause:
                    where_clause['price'].update({"$gte": float(filters['min_price'])})
                else:
                    where_clause['price'] = {"$gte": float(filters['min_price'])}
        
        # Perform search
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_clause if where_clause else None
            )
            
            # Parse results
            products = []
            if results['ids'] and results['ids'][0]:
                for i, product_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i] if results['distances'] else 0
                    
                    # Convert back to product format
                    product = {
                        'id': product_id,
                        'name': metadata.get('name', ''),
                        'category': metadata.get('category', ''),
                        'price': metadata.get('price', 0),
                        'metal': metadata.get('metal', ''),
                        'design_type': metadata.get('design_type', ''),
                        'gemstones': json.loads(metadata.get('gemstones', '[]')),
                        'style_tags': json.loads(metadata.get('style_tags', '[]')),
                        'occasion_tags': json.loads(metadata.get('occasion_tags', '[]')),
                        'recipient_tags': json.loads(metadata.get('recipient_tags', '[]')),
                        'image_url': metadata.get('image_url', ''),
                        'description': metadata.get('description', ''),
                        'similarity_score': 1 - distance,  # Convert distance to similarity
                        'confidence': 'high' if (1 - distance) > 0.7 else 'medium' if (1 - distance) > 0.5 else 'low'
                    }
                    products.append(product)
            
            # Cache the results
            self._cache_results(cache_key, products)
            
            elapsed_time = (time.time() - start_time) * 1000
            logger.info(f"Found {len(products)} matching products in {elapsed_time:.2f}ms")
            return products
            
        except Exception as e:
            logger.error(f"Error during semantic search: {e}")
            return []
    
    def _generate_cache_key(self, query: str, filters: Optional[Dict[str, Any]], top_k: int) -> str:
        """Generate cache key for query"""
        key_data = {
            'query': query.lower().strip(),
            'filters': filters or {},
            'top_k': top_k
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _cache_results(self, cache_key: str, results: List[Dict[str, Any]]) -> None:
        """Cache search results"""
        if len(self.query_cache) >= self.max_cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self.query_cache))
            del self.query_cache[oldest_key]
        
        self.query_cache[cache_key] = results
    
    def clear_cache(self) -> None:
        """Clear the query cache"""
        self.query_cache.clear()
        logger.info("Query cache cleared")
    
    def hybrid_search(
        self,
        query: str,
        preferences: Dict[str, Any],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Combine semantic search with traditional filtering
        
        Args:
            query: Natural language query
            preferences: User preferences from conversation
            top_k: Number of results to return
            
        Returns:
            List of matching products
        """
        # Build filters from preferences
        filters = {}
        
        if preferences.get('category'):
            filters['category'] = preferences['category']
        
        if preferences.get('metal'):
            filters['metal'] = preferences['metal']
        
        if preferences.get('budget_max'):
            filters['max_price'] = preferences['budget_max']
        
        # Enhance query with preferences context
        enhanced_query = query
        if preferences.get('occasion'):
            enhanced_query += f" for {preferences['occasion']}"
        
        if preferences.get('recipient'):
            enhanced_query += f" for {preferences['recipient']}"
        
        if preferences.get('style'):
            enhanced_query += f" {preferences['style']} style"
        
        return self.semantic_search(enhanced_query, filters, top_k)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database
        
        Returns:
            Dictionary with collection statistics
        """
        count = self.collection.count()
        return {
            'total_products': count,
            'collection_name': self.collection_name,
            'embedding_model': 'all-MiniLM-L6-v2',
            'embedding_dimension': self.embedding_dimension,
            'persist_directory': self.persist_directory
        }
    
    def reset_collection(self) -> None:
        """
        Reset the collection (delete all data)
        """
        logger.warning("Resetting vector database collection...")
        self.client.delete_collection(name=self.collection_name)
        self.collection = self._get_or_create_collection()
        logger.info("Collection reset complete")

# Global instance
vector_db = None

def get_vector_database() -> VectorDatabase:
    """
    Get or create global vector database instance
    """
    global vector_db
    if vector_db is None:
        vector_db = VectorDatabase()
    return vector_db

def initialize_vector_database_with_products(products: List[Dict[str, Any]]) -> VectorDatabase:
    """
    Initialize vector database with product catalog
    
    Args:
        products: List of product dictionaries
        
    Returns:
        Initialized VectorDatabase instance
    """
    logger.info("Initializing vector database with products...")
    
    vector_db = get_vector_database()
    
    # Check if already populated
    if vector_db.collection.count() > 0:
        logger.info("Vector database already populated")
        return vector_db
    
    # Add products
    vector_db.add_products(products)
    
    logger.info("Vector database initialization complete")
    return vector_db

if __name__ == "__main__":
    # Test the vector database
    print("Testing Vector Database...")
    
    # Load sample products
    try:
        with open("product_catalog_large.json", "r") as f:
            products = json.load(f)
        
        # Initialize database
        vdb = initialize_vector_database_with_products(products)
        
        # Test search
        results = vdb.semantic_search("elegant gold ring for engagement", top_k=3)
        
        print(f"\nFound {len(results)} products:")
        for product in results:
            print(f"- {product['name']} (Score: {product['similarity_score']:.3f})")
            
        # Show stats
        stats = vdb.get_collection_stats()
        print(f"\nDatabase Stats: {stats}")
        
    except Exception as e:
        print(f"Error: {e}")