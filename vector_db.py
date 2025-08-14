# /vector_db.py (CORRECTED to use Pinecone Client)
import os
import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Load the model only ONCE when the module is imported ---
try:
    logger.info("Loading embedding model globally...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
    logger.info("Embedding model loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load SentenceTransformer model: {e}")
    embedding_model = None
# --------------------------------------------------------------------

PRODUCT_CATALOG = []

class VectorDatabase:
    def __init__(self):
        if embedding_model is None:
            raise RuntimeError("Embedding model could not be loaded.")

        self.embedding_model = embedding_model
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = "joxy-retail"
        
        if not self.api_key:
            logger.error("PINECONE_API_KEY environment variable must be set.")
            self.index = None
            return

        try:
            pinecone = Pinecone(api_key=self.api_key)
            self.index = pinecone.Index(self.index_name)
            logger.info(f"Pinecone client initialized. Index stats: {self.index.describe_index_stats()}")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            self.index = None

    def add_products(self, products: List[Dict[str, Any]]):
        if not self.index or not products:
            logger.warning("Pinecone index not available or no products to add.")
            return
        
        current_count = self.index.describe_index_stats().get('total_vector_count', 0)
        if current_count >= len(products):
            logger.info(f"Vector DB count ({current_count}) >= product catalog ({len(products)}). Skipping add.")
            return

        logger.info(f"Adding {len(products)} products to Pinecone...")
        vectors_to_upsert = []
        for product in products:
            if not product.get('id'): continue
            
            doc_text = f"Product: {product.get('name', '')}. Description: {product.get('description', '')}. Tags: {' '.join(product.get('tags', []))}"
            embedding = self.embedding_model.encode(doc_text).tolist()
            
            metadata = {key: value for key, value in product.items() if isinstance(value, (str, int, float, bool))}
            vectors_to_upsert.append({'id': product['id'], 'values': embedding, 'metadata': metadata})

        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i + batch_size]
            self.index.upsert(vectors=batch)
            logger.info(f"Upserted batch {i//batch_size + 1}")
        
        logger.info(f"Successfully added {len(vectors_to_upsert)} products.")

    def hybrid_search(self, query: str, preferences: Dict[str, Any], top_k: int = 15) -> List[Dict[str, Any]]:
        if not self.index: return []
            
        filters = {}
        if preferences.get('category'): filters['category'] = preferences['category']
        if preferences.get('metal'): filters['metal'] = preferences['metal']
        if preferences.get('budget_max'): filters['price'] = {"$lte": float(preferences['budget_max'])}
        
        query_embedding = self.embedding_model.encode(query).tolist()
        
        results = self.index.query(
            vector=query_embedding, top_k=top_k,
            filter=filters if filters else None,
            include_metadata=True
        )
        
        products = []
        if results and results.get('matches'):
            for match in results['matches']:
                product_data = match.get('metadata', {})
                product_data['id'] = match['id']
                product_data['similarity_score'] = match.get('score', 0.0)
                products.append(product_data)
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
