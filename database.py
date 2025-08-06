"""
PostgreSQL Database Setup and Models for Retail AI Assistant
Handles product catalog, conversation history, sessions, and analytics
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from pydantic import BaseModel, Field
import uuid
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/retail_ai_db")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Product(Base):
    """Product model for jewelry catalog"""
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
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    recommendations = relationship("ProductRecommendation", back_populates="product")

class ConversationSession(Base):
    """Session model for conversation tracking"""
    __tablename__ = "conversation_sessions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)  # Future user management
    current_state = Column(String, default="initial_greeting")
    preferences = Column(JSON, default=dict)
    last_shown_product_ids = Column(ARRAY(String), default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    messages = relationship("ConversationMessage", back_populates="session")
    recommendations = relationship("ProductRecommendation", back_populates="session")

class ConversationMessage(Base):
    """Message model for conversation history"""
    __tablename__ = "conversation_messages"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("conversation_sessions.id"), index=True)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    preferences_at_turn = Column(JSON, default=dict)
    llm_metadata = Column(JSON, default=dict)  # LLM response metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("ConversationSession", back_populates="messages")

class ProductRecommendation(Base):
    """Product recommendation tracking"""
    __tablename__ = "product_recommendations"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("conversation_sessions.id"), index=True)
    product_id = Column(String, ForeignKey("products.id"), index=True)
    similarity_score = Column(Float)
    confidence_level = Column(String)  # high, medium, low
    recommendation_type = Column(String)  # vector, legacy, hybrid
    user_interaction = Column(String)  # viewed, clicked, ignored
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("ConversationSession", back_populates="recommendations")
    product = relationship("Product", back_populates="recommendations")

class ConversationAnalytics(Base):
    """Analytics tracking for conversations"""
    __tablename__ = "conversation_analytics"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, index=True)
    event_type = Column(String, nullable=False)  # session_start, message_sent, product_viewed, etc.
    event_data = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
# Pydantic Models for API
class ProductCreate(BaseModel):
    id: str
    name: str
    category: str
    image_url: Optional[str] = None
    price: float
    metal: str
    gemstones: List[str] = []
    design_type: str
    style_tags: List[str] = []
    occasion_tags: List[str] = []
    recipient_tags: List[str] = []
    description: Optional[str] = None

class ProductResponse(BaseModel):
    id: str
    name: str
    category: str
    image_url: Optional[str] = None
    price: float
    metal: str
    gemstones: List[str] = []
    design_type: str
    style_tags: List[str] = []
    occasion_tags: List[str] = []
    recipient_tags: List[str] = []
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

class SessionCreate(BaseModel):
    id: str
    user_id: Optional[str] = None
    current_state: str = "initial_greeting"
    preferences: Dict[str, Any] = {}

class SessionResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    current_state: str
    preferences: Dict[str, Any]
    last_shown_product_ids: List[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool

class MessageCreate(BaseModel):
    session_id: str
    role: str
    content: str
    preferences_at_turn: Dict[str, Any] = {}
    llm_metadata: Dict[str, Any] = {}

class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    preferences_at_turn: Dict[str, Any]
    llm_metadata: Dict[str, Any]
    created_at: datetime

# Database Operations
class DatabaseManager:
    """Database operations manager"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        
    def get_db(self) -> Session:
        """Get database session"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            return False
    
    def migrate_products_from_json(self, json_file_path: str) -> bool:
        """Migrate products from JSON to PostgreSQL"""
        try:
            with open(json_file_path, 'r') as f:
                products_data = json.load(f)
            
            db = next(self.get_db())
            
            # Clear existing products
            db.query(Product).delete()
            
            # Insert new products
            for product_data in products_data:
                product = Product(
                    id=product_data['id'],
                    name=product_data['name'],
                    category=product_data['category'],
                    image_url=product_data.get('image_url'),
                    price=product_data['price'],
                    metal=product_data['metal'],
                    gemstones=product_data.get('gemstones', []),
                    design_type=product_data['design_type'],
                    style_tags=product_data.get('style_tags', []),
                    occasion_tags=product_data.get('occasion_tags', []),
                    recipient_tags=product_data.get('recipient_tags', []),
                    description=product_data.get('description')
                )
                db.add(product)
            
            db.commit()
            logger.info(f"Successfully migrated {len(products_data)} products to PostgreSQL")
            return True
            
        except Exception as e:
            logger.error(f"Error migrating products: {e}")
            return False
    
    def get_products(self, db: Session, skip: int = 0, limit: int = 100) -> List[Product]:
        """Get products with pagination"""
        return db.query(Product).filter(Product.is_active == True).offset(skip).limit(limit).all()
    
    def get_product_by_id(self, db: Session, product_id: str) -> Optional[Product]:
        """Get product by ID"""
        return db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    
    def search_products(self, db: Session, **filters) -> List[Product]:
        """Search products with filters"""
        query = db.query(Product).filter(Product.is_active == True)
        
        if 'category' in filters and filters['category']:
            query = query.filter(Product.category == filters['category'])
        
        if 'max_price' in filters and filters['max_price']:
            query = query.filter(Product.price <= filters['max_price'])
        
        if 'metal' in filters and filters['metal']:
            query = query.filter(Product.metal.ilike(f"%{filters['metal']}%"))
        
        return query.all()
    
    def create_session(self, db: Session, session_data: SessionCreate) -> ConversationSession:
        """Create new conversation session"""
        session = ConversationSession(
            id=session_data.id,
            user_id=session_data.user_id,
            current_state=session_data.current_state,
            preferences=session_data.preferences
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    
    def get_session(self, db: Session, session_id: str) -> Optional[ConversationSession]:
        """Get session by ID"""
        return db.query(ConversationSession).filter(
            ConversationSession.id == session_id,
            ConversationSession.is_active == True
        ).first()
    
    def update_session(self, db: Session, session_id: str, updates: Dict[str, Any]) -> Optional[ConversationSession]:
        """Update session"""
        session = self.get_session(db, session_id)
        if session:
            for key, value in updates.items():
                setattr(session, key, value)
            session.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(session)
        return session
    
    def add_message(self, db: Session, message_data: MessageCreate) -> ConversationMessage:
        """Add message to conversation"""
        message = ConversationMessage(
            session_id=message_data.session_id,
            role=message_data.role,
            content=message_data.content,
            preferences_at_turn=message_data.preferences_at_turn,
            llm_metadata=message_data.llm_metadata
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    
    def get_conversation_history(self, db: Session, session_id: str, limit: int = 10) -> List[ConversationMessage]:
        """Get conversation history"""
        return db.query(ConversationMessage).filter(
            ConversationMessage.session_id == session_id
        ).order_by(ConversationMessage.created_at.desc()).limit(limit).all()
    
    def track_recommendation(self, db: Session, session_id: str, product_id: str, 
                           similarity_score: float, confidence_level: str, 
                           recommendation_type: str) -> ProductRecommendation:
        """Track product recommendation"""
        recommendation = ProductRecommendation(
            session_id=session_id,
            product_id=product_id,
            similarity_score=similarity_score,
            confidence_level=confidence_level,
            recommendation_type=recommendation_type
        )
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)
        return recommendation
    
    def log_analytics_event(self, db: Session, session_id: str, event_type: str, event_data: Dict[str, Any]):
        """Log analytics event"""
        event = ConversationAnalytics(
            session_id=session_id,
            event_type=event_type,
            event_data=event_data
        )
        db.add(event)
        db.commit()
        return event

# Global database manager instance
db_manager = DatabaseManager()

def get_database_manager() -> DatabaseManager:
    """Get database manager instance"""
    return db_manager

def init_database():
    """Initialize database"""
    try:
        # Create tables
        db_manager.create_tables()
        
        # Migrate products from JSON if available
        import os
        json_file_path = "/app/product_catalog_large.json"
        if os.path.exists(json_file_path):
            db_manager.migrate_products_from_json(json_file_path)
        
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    # Test database connection and setup
    print("Testing database connection...")
    try:
        # Test connection
        test_db = next(db_manager.get_db())
        print("✅ Database connection successful")
        
        # Initialize database
        if init_database():
            print("✅ Database initialization successful")
        else:
            print("❌ Database initialization failed")
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")