"""
Vector Database Setup with ChromaDB
"""
import chromadb
from chromadb.config import Settings
import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global product catalog - will be updated by main application
PRODUCT_CATALOG = []

class VectorDatabase:
    
    def __init__(self, persist_directory: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")):
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
        tags = " ".join(product.get('tags', []))
        return f"Product: {product.get('name', '')}. Description: {product.get('description', '')}. Tags: {tags}"

    def add_products(self, products: List[Dict[str, Any]]):
        if not products:
            logger.warning("No products provided to add to the vector database.")
            return
        logger.info(f"Adding {len(products)} products to vector database...")
        ids, documents, metadatas = [], [], []
        for product in products:
            if not product.get('id'): continue
            ids.append(product['id'])
            documents.append(self.create_product_text_for_embedding(product))
            metadata = {
                'name': product.get('name', ''),
                'category': product.get('category', ''),
                'price': product.get('price', 0.0),
                'metal': product.get('metal', '')
            }
            metadatas.append(metadata)
        
        if ids:
            embeddings = self.embedding_model.encode(documents, show_progress_bar=True).tolist()
            self.collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
            logger.info(f"Successfully added {len(ids)} products.")

    def hybrid_search(self, query: str, preferences: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
        filters = {}
        if preferences.get('category'): filters['category'] = preferences['category']
        if preferences.get('metal'): filters['metal'] = preferences['metal']
        if preferences.get('budget_max'): filters['price'] = {"$lte": preferences['budget_max']}
        
        results = self.collection.query(query_texts=[query], n_results=top_k, where=filters if filters else None)
        
        products = []
        if results['ids'] and results['ids'][0]:
            for i, product_id in enumerate(results['ids'][0]):
                # Find the original product from the current catalog
                original_product = next((p for p in PRODUCT_CATALOG if p.get('id') == product_id), None)
                if original_product:
                    distance = results['distances'][0][i]
                    # Create a clean copy to avoid SQLAlchemy issues
                    clean_product = {k: v for k, v in original_product.items() if not k.startswith('_')}
                    clean_product['similarity_score'] = 1 - distance
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
    # Update the global catalog with clean dictionaries
    PRODUCT_CATALOG = []
    for product in products:
        if hasattr(product, '__dict__'):
            # Remove SQLAlchemy internal state
            clean_product = {k: v for k, v in product.__dict__.items() 
                           if not k.startswith('_')}
            PRODUCT_CATALOG.append(clean_product)
        else:
            PRODUCT_CATALOG.append(product)
    
    vdb = get_vector_database()
    if vdb.collection.count() == 0 and PRODUCT_CATALOG:
        vdb.add_products(PRODUCT_CATALOG)
    return vdb
