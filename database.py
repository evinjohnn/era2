# /database.py
"""
PostgreSQL Database Setup and Models for Retail AI Assistant
Handles product catalog, conversation history, sessions, and analytics
"""
import os
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy import orm
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.exc import OperationalError
import uuid
import json
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/retail_ai_db")
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = orm.declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    image_url = Column(String)
    price = Column(Float, nullable=False, index=True)
    metal = Column(String, index=True)
    gemstones = Column(ARRAY(String), default=[])
    design_type = Column(String, index=True)
    style_tags = Column(ARRAY(String), default=[])
    occasion_tags = Column(ARRAY(String), default=[])
    recipient_tags = Column(ARRAY(String), default=[])
    tags = Column(ARRAY(String), default=[]) # <-- FIX: THIS LINE WAS MISSING
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        
    def get_db(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def create_tables(self):
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            return False
    
    def get_all_products(self, db: Session) -> List[Product]:
        return db.query(Product).all()

    def migrate_products_from_json(self, json_file_path: str) -> bool:
        db = next(self.get_db())
        try:
            with open(json_file_path, 'r') as f:
                products_data = json.load(f)
            
            if db.query(Product).count() > 0:
                logger.info("Products table already populated. Skipping migration.")
                return True

            logger.info("Migrating product data from JSON to PostgreSQL...")
            for product_data in products_data:
                product = Product(**product_data)
                db.add(product)
            
            db.commit()
            logger.info(f"Successfully migrated {len(products_data)} products.")
            return True
        except Exception as e:
            logger.error(f"Error migrating products: {e}")
            db.rollback()
            return False
        finally:
            db.close()

db_manager = None
def get_database_manager() -> DatabaseManager:
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager

def init_database():
    manager = get_database_manager()
    if not manager.create_tables():
        return False
    
    json_file_path = "product_catalog_large.json"
    if os.path.exists(json_file_path):
        if not manager.migrate_products_from_json(json_file_path):
            return False
    
    logger.info("Database initialized successfully")
    return True

def wait_for_db():
    logger.info("Waiting for database...")
    retries = 10
    while retries > 0:
        try:
            connection = engine.connect()
            connection.close()
            logger.info("Database is ready!")
            return True
        except OperationalError:
            retries -= 1
            logger.info(f"Database not ready, retrying in 2 seconds... ({retries} retries left)")
            time.sleep(2)
    logger.error("Could not connect to the database.")
    return False

if __name__ == "__main__":
    if wait_for_db():
        init_database()