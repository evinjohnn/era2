import logging
from database import get_database_manager
from vector_db import initialize_vector_database_with_products
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

def seed():
    load_dotenv()
    logging.info("Starting vector database seeding process...")
    
    db_manager = get_database_manager()
    db = next(db_manager.get_db())
    products_from_db = db_manager.get_all_products(db)
    db.close()

    if not products_from_db:
        logging.error("No products found in PostgreSQL. Cannot seed vector DB.")
        return

    PRODUCT_CATALOG = []
    for product in products_from_db:
        product_dict = {k: v for k, v in product.__dict__.items() if not k.startswith('_')}
        PRODUCT_CATALOG.append(product_dict)

    logging.info(f"Loaded {len(PRODUCT_CATALOG)} products from PostgreSQL.")
    
    # This will initialize the connection and add products if they don't exist
    initialize_vector_database_with_products(PRODUCT_CATALOG)
    
    logging.info("Vector database seeding process complete.")

if __name__ == "__main__":
    seed()
