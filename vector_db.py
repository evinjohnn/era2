# /vector_db.py (CORRECTED to use ChromaDB)
import os
import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import chromadb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global product catalog - will be updated by main application
PRODUCT_CATALOG = []

class VectorDatabase:
    def __init__(self):
        # Use a persistent directory for ChromaDB. This path is crucial for Render disks.
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
        logger.info(f"Initializing ChromaDB at persistent path: {db_path}")
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection_name = "joxy_products"
        
        logger.info("Loading embedding model for ChromaDB...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        
        logger.info(f"Getting or creating ChromaDB collection: {self.collection_name}")
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
        logger.info("ChromaDB client initialized successfully.")

    def create_product_text_for_embedding(self, product: Dict[str, Any]) -> str:
        tags = " ".join(product.get('tags', []))
        return f"Product: {product.get('name', '')}. Description: {product.get('description', '')}. Tags: {tags}"

    def add_products(self, products: List[Dict[str, Any]]):
        if not products:
            logger.warning("No products to add to ChromaDB.")
            return

        if self.collection.count() >= len(products):
            logger.info("Vector database already appears to be populated. Skipping addition.")
            return

        logger.info(f"Adding {len(products)} products to ChromaDB...")
        
        ids = [p['id'] for p in products if p.get('id')]
        documents = [self.create_product_text_for_embedding(p) for p in products if p.get('id')]
        metadatas = [
            {key: value for key, value in p.items() if isinstance(value, (str, int, float, bool))}
            for p in products if p.get('id')
        ]

        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_documents = documents[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            
            self.collection.add(
                ids=batch_ids,
                documents=batch_documents,
                metadatas=batch_metadatas
            )
            logger.info(f"Upserted batch {i//batch_size + 1}")
        
        logger.info(f"Successfully added {len(ids)} products to ChromaDB.")

    def hybrid_search(self, query: str, preferences: Dict[str, Any], top_k: int = 15) -> List[Dict[str, Any]]:
        where_clause = {}
        if preferences.get('category'):
            where_clause['category'] = preferences['category']
        if preferences.get('metal'):
            where_clause['metal'] = preferences['metal']
        if preferences.get('budget_max'):
            where_clause['price'] = {"$lte": float(preferences['budget_max'])}

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_clause if where_clause else None
        )
        
        products = []
        if results and results['ids'][0]:
            for i, product_id in enumerate(results['ids'][0]):
                original_product = next((p for p in PRODUCT_CATALOG if p.get('id') == product_id), None)
                if original_product:
                    clean_product = {k: v for k, v in original_product.items() if not k.startswith('_')}
                    # Chroma uses distance; convert to similarity score (0 to 1)
                    clean_product['similarity_score'] = 1 - results['distances'][0][i] 
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
    if vdb and vdb.collection:
        vdb.add_products(PRODUCT_CATALOG)
    return vdb
