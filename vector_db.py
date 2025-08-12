"""
Vector Database Setup with ChromaDB
Handles product embeddings and semantic search for the retail AI assistant
"""

import chromadb
from chromadb.config import Settings
import json
import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global product catalog to store original product data
PRODUCT_CATALOG = []

class VectorDatabase:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.collection_name = "jewelry_products"
        self.client = chromadb.PersistentClient(path=persist_directory, settings=Settings(anonymized_telemetry=False))
        logger.info("Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        self.collection = self._get_or_create_collection()
        logger.info(f"Vector database initialized with {self.collection.count()} products")

    def _get_or_create_collection(self):
        try:
            return self.client.get_collection(name=self.collection_name)
        except Exception:
            logger.info(f"Creating new collection: {self.collection_name}")
            return self.client.create_collection(name=self.collection_name)

    def create_product_text_for_embedding(self, product: Dict[str, Any]) -> str:
        # This function is crucial for creating meaningful embeddings.
        # It combines the most important text fields into a single string.
        tags = " ".join(product.get('tags', []))
        return f"Product: {product.get('name', '')}. Description: {product.get('description', '')}. Tags: {tags}"

    def add_products(self, products: List[Dict[str, Any]]):
        logger.info(f"Adding {len(products)} products to vector database...")
        ids, documents, metadatas = [], [], []
        for product in products:
            if not product.get('id'): continue
            ids.append(product['id'])
            documents.append(self.create_product_text_for_embedding(product))
            # Metadata must be JSON serializable and contain simple types
            metadata = {
                'name': product.get('name', ''),
                'category': product.get('category', ''),  # Fixed: category is at top level
                'price': product.get('price', 0.0),
                'metal': product.get('metal', '')  # Fixed: metal is at top level
            }
            metadatas.append(metadata)
        
        if ids:
            # Batch embedding generation for efficiency
            embeddings = self.embedding_model.encode(documents, show_progress_bar=True).tolist()
            self.collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
            logger.info(f"Successfully added {len(ids)} products.")

    def semantic_search(self, query: str, filters: Optional[Dict[str, Any]] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        start_time = time.time()
        results = self.collection.query(query_texts=[query], n_results=top_k, where=filters)
        products = []
        if results['ids'] and results['ids'][0]:
            for i, product_id in enumerate(results['ids'][0]):
                # Reconstruct the product from the original catalog for full details
                original_product = next((p for p in PRODUCT_CATALOG if p['id'] == product_id), None)
                if original_product:
                    distance = results['distances'][0][i]
                    original_product['similarity_score'] = 1 - distance
                    products.append(original_product)
        elapsed_time = (time.time() - start_time) * 1000
        logger.info(f"Semantic search completed in {elapsed_time:.2f}ms, found {len(products)} results.")
        return products

    def hybrid_search(self, query: str, preferences: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
        # Build ChromaDB compatible filters
        where_conditions = []
        if preferences.get('category'): 
            where_conditions.append({"category": {"$eq": preferences['category']}})
        if preferences.get('metal'): 
            where_conditions.append({"metal": {"$eq": preferences['metal']}})
        if preferences.get('budget_max'): 
            where_conditions.append({"price": {"$lte": preferences['budget_max']}})
        
        # Use $and operator to combine multiple conditions
        filters = {"$and": where_conditions} if len(where_conditions) > 1 else where_conditions[0] if where_conditions else None
        
        # Convert all preference values to strings before joining
        preference_text = ' '.join(str(v) for v in preferences.values())
        enhanced_query = f"{query} {preference_text}"
        return self.semantic_search(enhanced_query, filters, top_k)

    def get_collection_stats(self) -> Dict[str, Any]:
        return {'total_products': self.collection.count(), 'collection_name': self.collection_name}

vector_db = None

def get_vector_database() -> VectorDatabase:
    global vector_db
    if vector_db is None:
        vector_db = VectorDatabase()
    return vector_db

def initialize_vector_database_with_products(products: List[Dict[str, Any]]) -> VectorDatabase:
    global PRODUCT_CATALOG
    PRODUCT_CATALOG = products
    vdb = get_vector_database()
    vdb.add_products(products)
    return vdb