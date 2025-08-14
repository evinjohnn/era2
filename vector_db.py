# /vector_db.py (NEW VERSION)
import os
import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global product catalog - will be updated by main application
PRODUCT_CATALOG = []

class VectorDatabase:
    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.environment = os.getenv("PINECONE_ENVIRONMENT")
        self.index_name = "joxy-retail"
        self.pinecone = None
        self.index = None
        
        if not self.api_key or not self.environment:
            logger.error("PINECONE_API_KEY and PINECONE_ENVIRONMENT must be set.")
            return

        try:
            self.pinecone = Pinecone(api_key=self.api_key)
            if self.index_name not in self.pinecone.list_indexes().names():
                logger.warning(f"Pinecone index '{self.index_name}' not found. Please create it in the Pinecone console.")
                # Optionally, you can create it here, but manual creation is safer for free tier.
            self.index = self.pinecone.Index(self.index_name)
            logger.info(f"Pinecone client initialized. Index stats: {self.index.describe_index_stats()}")
            logger.info("Loading embedding model...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")

    def create_product_text_for_embedding(self, product: Dict[str, Any]) -> str:
        tags = " ".join(product.get('tags', []))
        return f"Product: {product.get('name', '')}. Description: {product.get('description', '')}. Tags: {tags}"

    def add_products(self, products: List[Dict[str, Any]]):
        if not self.index or not products:
            logger.warning("Pinecone index not available or no products to add.")
            return
        
        # Check if products already exist to avoid re-indexing
        if self.index.describe_index_stats().get('total_vector_count', 0) >= len(products):
            logger.info("Vector database already appears to be populated. Skipping addition.")
            return

        logger.info(f"Adding {len(products)} products to Pinecone...")
        vectors_to_upsert = []
        for product in products:
            if not product.get('id'): continue
            
            doc_text = self.create_product_text_for_embedding(product)
            embedding = self.embedding_model.encode(doc_text).tolist()
            
            metadata = {
                'name': product.get('name', ''),
                'category': product.get('category', ''),
                'price': product.get('price', 0.0),
                'metal': product.get('metal', '')
            }
            vectors_to_upsert.append((product['id'], embedding, metadata))

        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i + batch_size]
            self.index.upsert(vectors=batch)
            logger.info(f"Upserted batch {i//batch_size + 1}")
        
        logger.info(f"Successfully added {len(vectors_to_upsert)} products.")

    def hybrid_search(self, query: str, preferences: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.index:
            return []
            
        filters = {}
        if preferences.get('category'): filters['category'] = preferences['category']
        if preferences.get('metal'): filters['metal'] = preferences['metal']
        if preferences.get('budget_max'): filters['price'] = {"$lte": preferences['budget_max']}
        
        query_embedding = self.embedding_model.encode(query).tolist()
        
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            filter=filters if filters else None,
            include_metadata=False # We only need the ID to look up in our catalog
        )
        
        products = []
        if results and results['matches']:
            for match in results['matches']:
                product_id = match['id']
                original_product = next((p for p in PRODUCT_CATALOG if p.get('id') == product_id), None)
                if original_product:
                    clean_product = {k: v for k, v in original_product.items() if not k.startswith('_')}
                    clean_product['similarity_score'] = match['score']
                    products.append(clean_product)
        return products

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
    if vdb and vdb.index:
        vdb.add_products(PRODUCT_CATALOG)
    return vdb
