#!/usr/bin/env python3
"""
Debug script to check metadata structure in the vector database
"""

from vector_db import get_vector_database
import json

def debug_metadata():
    vdb = get_vector_database()
    
    # Get a sample of products to see their metadata
    print("Sample products from database:")
    results = vdb.collection.get(limit=3)
    
    print("\nMetadata structure:")
    for i, metadata in enumerate(results['metadatas']):
        print(f"Product {i+1}: {metadata}")
    
    print("\nDocument structure:")
    for i, doc in enumerate(results['documents']):
        print(f"Product {i+1}: {doc[:100]}...")
    
    # Check what categories and metals exist in metadata
    all_metadata = vdb.collection.get(limit=220)
    categories = set()
    metals = set()
    
    for metadata in all_metadata['metadatas']:
        if metadata.get('category'):
            categories.add(metadata['category'])
        if metadata.get('metal'):
            metals.add(metadata['metal'])
    
    print(f"\nAvailable categories in metadata: {sorted(categories)}")
    print(f"Available metals in metadata: {sorted(metals)}")
    
    # Test a simple filter
    print("\nTesting simple category filter:")
    try:
        simple_results = vdb.collection.query(
            query_texts=["ring"],
            n_results=3,
            where={"category": {"$eq": "ring"}}
        )
        print(f"Found {len(simple_results['ids'][0]) if simple_results['ids'] else 0} results")
    except Exception as e:
        print(f"Error with simple filter: {e}")

if __name__ == "__main__":
    debug_metadata()
