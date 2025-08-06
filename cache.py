"""
Redis Cache Client for Retail AI Assistant
Handles session storage and conversation history with Redis persistence
"""

import redis
import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client for session and conversation history management"""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis client
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client = None
        self.connected = False
        
        try:
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            self.client.ping()
            self.connected = True
            logger.info(f"Redis connected successfully at {self.redis_url}")
            
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.connected = False
            self.client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self.connected and self.client is not None
    
    def get_session_key(self, session_id: str) -> str:
        """Get Redis key for session data"""
        return f"session:{session_id}"
    
    def get_history_key(self, session_id: str) -> str:
        """Get Redis key for conversation history"""
        return f"history:{session_id}"
    
    def set_session(self, session_id: str, session_data: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        Store session data in Redis
        
        Args:
            session_id: Session identifier
            session_data: Session data dictionary
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            logger.warning("Redis not connected, cannot set session")
            return False
        
        try:
            key = self.get_session_key(session_id)
            serialized_data = json.dumps(session_data)
            
            # Set with TTL
            result = self.client.setex(key, ttl, serialized_data)
            
            if result:
                logger.debug(f"Session {session_id} stored successfully")
                return True
            else:
                logger.error(f"Failed to store session {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting session {session_id}: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data from Redis
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data dictionary or None if not found
        """
        if not self.is_connected():
            logger.warning("Redis not connected, cannot get session")
            return None
        
        try:
            key = self.get_session_key(session_id)
            data = self.client.get(key)
            
            if data:
                session_data = json.loads(data)
                logger.debug(f"Session {session_id} retrieved successfully")
                return session_data
            else:
                logger.debug(f"Session {session_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete session data from Redis
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            logger.warning("Redis not connected, cannot delete session")
            return False
        
        try:
            session_key = self.get_session_key(session_id)
            history_key = self.get_history_key(session_id)
            
            # Delete both session and history
            result = self.client.delete(session_key, history_key)
            
            if result > 0:
                logger.info(f"Session {session_id} deleted successfully")
                return True
            else:
                logger.warning(f"Session {session_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    def add_to_conversation_history(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        preferences: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add message to conversation history
        
        Args:
            session_id: Session identifier
            role: Message role (user/assistant)
            content: Message content
            preferences: User preferences at this turn
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            logger.warning("Redis not connected, cannot add to conversation history")
            return False
        
        try:
            key = self.get_history_key(session_id)
            
            # Create message entry
            message = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "role": role,
                "content": content,
                "preferences_at_turn": preferences or {}
            }
            
            # Add to Redis list (RPUSH adds to end)
            self.client.rpush(key, json.dumps(message))
            
            # Set TTL for history (longer than session)
            self.client.expire(key, 7200)  # 2 hours
            
            logger.debug(f"Added message to history for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding to conversation history for session {session_id}: {e}")
            return False
    
    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent conversation history
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of conversation messages
        """
        if not self.is_connected():
            logger.warning("Redis not connected, cannot get conversation history")
            return []
        
        try:
            key = self.get_history_key(session_id)
            
            # Get last 'limit' messages
            messages = self.client.lrange(key, -limit, -1)
            
            # Parse JSON messages
            parsed_messages = []
            for msg_str in messages:
                try:
                    msg = json.loads(msg_str)
                    parsed_messages.append(msg)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse message: {msg_str}")
            
            logger.debug(f"Retrieved {len(parsed_messages)} messages for session {session_id}")
            return parsed_messages
            
        except Exception as e:
            logger.error(f"Error getting conversation history for session {session_id}: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis connection and usage statistics
        
        Returns:
            Dictionary with Redis stats
        """
        if not self.is_connected():
            return {
                "connected": False,
                "error": "Redis not connected"
            }
        
        try:
            info = self.client.info()
            
            return {
                "connected": True,
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "url": self.redis_url
            }
            
        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")
            return {
                "connected": False,
                "error": str(e)
            }

# Global Redis client instance
redis_client = None

def get_redis_client() -> RedisClient:
    """
    Get or create global Redis client instance
    
    Returns:
        RedisClient instance
    """
    global redis_client
    if redis_client is None:
        redis_client = RedisClient()
    return redis_client

def is_redis_available() -> bool:
    """
    Check if Redis is available
    
    Returns:
        True if Redis is connected, False otherwise
    """
    client = get_redis_client()
    return client.is_connected()

if __name__ == "__main__":
    # Test Redis connection
    print("Testing Redis connection...")
    
    client = get_redis_client()
    
    if client.is_connected():
        print("✅ Redis connection successful")
        
        # Test session operations
        test_session_id = "test_session_123"
        test_data = {
            "current_conversational_state": "initial_greeting",
            "preferences": {"category": "ring", "budget_max": 1000}
        }
        
        # Test set/get
        if client.set_session(test_session_id, test_data):
            print("✅ Session set successfully")
            
            retrieved = client.get_session(test_session_id)
            if retrieved == test_data:
                print("✅ Session retrieved successfully")
            else:
                print("❌ Session data mismatch")
        
        # Test conversation history
        client.add_to_conversation_history(
            test_session_id, 
            "user", 
            "Hello, I'm looking for a ring"
        )
        
        history = client.get_conversation_history(test_session_id)
        if history:
            print(f"✅ Conversation history: {len(history)} messages")
        
        # Cleanup
        client.delete_session(test_session_id)
        print("✅ Test session cleaned up")
        
        # Show stats
        stats = client.get_stats()
        print(f"Redis Stats: {stats}")
        
    else:
        print("❌ Redis connection failed")