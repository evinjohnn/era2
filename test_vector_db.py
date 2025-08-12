#!/usr/bin/env python3
"""
Test script for the vector database functionality
"""

import json
from vector_db import initialize_vector_database_with_products, get_vector_database

def test_vector_database():
    print("Loading product data...")
    
    # Load the generated product data
    with open("product_catalog_large.json", "r") as f:
        products = json.load(f)
    
    print(f"Loaded {len(products)} products")
    
    # Initialize the vector database
    print("Initializing vector database...")
    vdb = initialize_vector_database_with_products(products)
    
    # Test basic search functionality
    print("\nTesting semantic search...")
    search_results = vdb.semantic_search("gold ring for wedding", top_k=3)
    
    print(f"Found {len(search_results)} results:")
    for i, product in enumerate(search_results, 1):
        print(f"{i}. {product['name']} - ${product['price']} (Score: {product.get('similarity_score', 'N/A'):.3f})")
    
    # Test hybrid search with filters
    print("\nTesting hybrid search with filters...")
    preferences = {
        'category': 'ring',
        'metal': 'gold',
        'budget_max': 1000
    }
    
    hybrid_results = vdb.hybrid_search("elegant wedding ring", preferences, top_k=3)
    
    print(f"Found {len(hybrid_results)} filtered results:")
    for i, product in enumerate(hybrid_results, 1):
        print(f"{i}. {product['name']} - ${product['price']} (Score: {product.get('similarity_score', 'N/A'):.3f})")
    
    # Get collection stats
    stats = vdb.get_collection_stats()
    print(f"\nCollection stats: {stats}")

if __name__ == "__main__":
    test_vector_database()
