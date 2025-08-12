#!/usr/bin/env python3
"""
Database Fix Script
Adds missing columns or recreates tables to fix schema mismatches
"""
import os
import logging
from sqlalchemy import text
from database import engine, Base, get_database_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_database_schema():
    """Fix the database schema by adding missing columns or recreating tables"""
    try:
        # Check if products table exists and has the right columns
        with engine.connect() as conn:
            # Check if tags column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'products' AND column_name = 'tags'
            """))
            
            if result.fetchone():
                logger.info("Tags column already exists. Database schema is correct.")
                return True
            
            logger.info("Tags column missing. Adding it to the products table...")
            
            # Add the missing tags column
            conn.execute(text("ALTER TABLE products ADD COLUMN tags TEXT[] DEFAULT '{}'"))
            conn.commit()
            
            logger.info("Successfully added tags column to products table.")
            return True
            
    except Exception as e:
        logger.error(f"Error fixing database schema: {e}")
        
        # If adding column fails, try recreating the table
        logger.info("Attempting to recreate the products table...")
        try:
            with engine.connect() as conn:
                # Drop existing table
                conn.execute(text("DROP TABLE IF EXISTS products CASCADE"))
                conn.commit()
            
            # Recreate table with correct schema
            Base.metadata.create_all(bind=engine)
            logger.info("Successfully recreated products table with correct schema.")
            
            # Migrate data from JSON if it exists
            db_manager = get_database_manager()
            json_file_path = "product_catalog_large.json"
            if os.path.exists(json_file_path):
                if db_manager.migrate_products_from_json(json_file_path):
                    logger.info("Successfully migrated product data after table recreation.")
                    return True
                else:
                    logger.error("Failed to migrate product data after table recreation.")
                    return False
            else:
                logger.warning("No product catalog JSON found. Table recreated but empty.")
                return True
                
        except Exception as recreate_error:
            logger.error(f"Failed to recreate table: {recreate_error}")
            return False

def main():
    """Main function to fix the database"""
    logger.info("Starting database schema fix...")
    
    if fix_database_schema():
        logger.info("Database schema fix completed successfully!")
    else:
        logger.error("Database schema fix failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
