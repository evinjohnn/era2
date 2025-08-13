# /database.py
"""
PostgreSQL Database Setup and Models for Retail AI Assistant
Handles product catalog, conversation history, sessions, and analytics
"""
import os
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Integer
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

class ConversationSession(Base):
    __tablename__ = "conversation_sessions"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    current_state = Column(String, default="initial")
    preferences = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    messages = relationship("ConversationMessage", back_populates="session", cascade="all, delete-orphan")
    recommendations = relationship("ProductRecommendation", back_populates="session", cascade="all, delete-orphan")
    analytics_events = relationship("ConversationAnalytics", back_populates="session", cascade="all, delete-orphan")

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("conversation_sessions.id"), index=True)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    preferences_at_turn = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("ConversationSession", back_populates="messages")

class ProductRecommendation(Base):
    __tablename__ = "product_recommendations"
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("conversation_sessions.id"), index=True)
    product_id = Column(String, ForeignKey("products.id"), index=True)
    similarity_score = Column(Float, nullable=False)
    confidence_level = Column(String, default="medium")  # "low", "medium", "high"
    recommendation_type = Column(String, default="general")  # "general", "personalized", "trending"
    user_interaction = Column(String, nullable=True)  # "viewed", "liked", "disliked", "purchased"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("ConversationSession", back_populates="recommendations")
    product = relationship("Product")

class ConversationAnalytics(Base):
    __tablename__ = "conversation_analytics"
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("conversation_sessions.id"), index=True)
    event_type = Column(String, nullable=False)  # "session_start", "message_sent", "product_viewed", etc.
    event_data = Column(JSON, default={})
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("ConversationSession", back_populates="analytics_events")

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

    def create_sample_conversation_data(self) -> bool:
        """Create sample conversation data for testing analytics"""
        db = next(self.get_db())
        try:
            # Check if we already have conversation data
            if db.query(ConversationSession).count() > 0:
                logger.info("Conversation data already exists. Skipping sample data creation.")
                return True
            
            logger.info("Creating sample conversation data for analytics testing...")
            
            # First, ensure we have some products to reference
            existing_products = db.query(Product).limit(10).all()
            if not existing_products:
                # Create some sample products if none exist
                sample_products = [
                    Product(
                        id=f"sample_product_{i}",
                        name=f"Sample Jewelry {i}",
                        category="rings" if i % 3 == 0 else "necklaces" if i % 3 == 1 else "earrings",
                        price=1000.0 + (i * 100),
                        metal="gold" if i % 2 == 0 else "silver",
                        description=f"Beautiful sample jewelry piece {i}",
                        image_url=f"https://via.placeholder.com/300x200/cccccc/FFFFFF?text=Sample+{i}"
                    )
                    for i in range(1, 11)
                ]
                
                for product in sample_products:
                    db.add(product)
                db.commit()
                logger.info(f"Created {len(sample_products)} sample products")
                
                # Refresh the products list
                existing_products = db.query(Product).limit(10).all()
            
            # Create sample sessions
            sample_sessions = [
                ConversationSession(
                    id=f"session_{i}",
                    user_id=f"user_{i}",
                    current_state="completed" if i % 3 == 0 else "active",
                    preferences={"style": "modern", "budget": "1000-2000"},
                    created_at=datetime.utcnow() - timedelta(hours=i),
                    ended_at=datetime.utcnow() - timedelta(hours=i-1) if i % 3 == 0 else None,
                    is_active=i % 3 != 0
                )
                for i in range(1, 21)  # Create 20 sample sessions
            ]
            
            for session in sample_sessions:
                db.add(session)
            
            # Create sample messages
            sample_messages = []
            for session in sample_sessions:
                # Add user message
                sample_messages.append(ConversationMessage(
                    id=f"msg_{session.id}_1",
                    session_id=session.id,
                    role="user",
                    content="I'm looking for an engagement ring",
                    created_at=session.created_at
                ))
                
                # Add assistant message
                sample_messages.append(ConversationMessage(
                    id=f"msg_{session.id}_2",
                    session_id=session.id,
                    role="assistant",
                    content="I'd be happy to help you find the perfect engagement ring!",
                    created_at=session.created_at + timedelta(minutes=1)
                ))
            
            for message in sample_messages:
                db.add(message)
            
            # Create sample recommendations using existing products
            sample_recommendations = []
            for i, session in enumerate(sample_sessions):
                if i < len(existing_products):  # Only create recommendations for sessions with available products
                    sample_recommendations.append(ProductRecommendation(
                        id=f"rec_{session.id}_1",
                        session_id=session.id,
                        product_id=existing_products[i].id,  # Use actual product ID
                        similarity_score=0.85 + (i * 0.01),
                        confidence_level="high" if i % 2 == 0 else "medium",
                        recommendation_type="personalized",
                        created_at=session.created_at + timedelta(minutes=2)
                    ))
            
            for recommendation in sample_recommendations:
                db.add(recommendation)
            
            # Create sample analytics events
            sample_events = []
            for session in sample_sessions:
                sample_events.append(ConversationAnalytics(
                    id=f"event_{session.id}_1",
                    session_id=session.id,
                    event_type="session_start",
                    event_data={"source": "web"},
                    timestamp=session.created_at
                ))
                
                if session.ended_at:
                    sample_events.append(ConversationAnalytics(
                        id=f"event_{session.id}_2",
                        session_id=session.id,
                        event_type="session_end",
                        event_data={"duration": "5 minutes"},
                        timestamp=session.ended_at
                    ))
            
            for event in sample_events:
                db.add(event)
            
            db.commit()
            logger.info(f"Successfully created sample conversation data: {len(sample_sessions)} sessions, {len(sample_messages)} messages, {len(sample_recommendations)} recommendations")
            return True
            
        except Exception as e:
            logger.error(f"Error creating sample conversation data: {e}")
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