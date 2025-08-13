#!/usr/bin/env python3
"""
Run the comprehensive product generator to create new products with proper tags
"""

import subprocess
import sys
import os

def main():
    print("🚀 Starting Comprehensive Product Generation...")
    
    try:
        # Run the product generator
        print("📦 Generating new products with comprehensive tags...")
        result = subprocess.run([sys.executable, 'generate_product_data.py'], 
                              capture_output=True, text=True, check=True)
        
        print("✅ Product generation completed successfully!")
        print(result.stdout)
        
        # Check if the file was created
        if os.path.exists('product_catalog_comprehensive.json'):
            print(f"📁 New product catalog created: product_catalog_comprehensive.json")
            
            # Show file size
            file_size = os.path.getsize('product_catalog_comprehensive.json')
            print(f"📊 File size: {file_size / 1024:.1f} KB")
            
            print("\n🎯 Next steps:")
            print("1. Copy the new products to your database")
            print("2. Restart your backend to load the new catalog")
            print("3. Test the improved RAG matching system")
            
        else:
            print("❌ Product catalog file not found")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running product generator: {e}")
        print(f"Error output: {e.stderr}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
