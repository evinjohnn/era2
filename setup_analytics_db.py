#!/usr/bin/env python3
"""
Setup script for Analytics Database
Creates tables and populates with sample conversation data for testing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_database_manager
from analytics import get_analytics_engine, MetricPeriod

def setup_analytics_database():
    """Set up the database with tables and sample data"""
    print("🚀 Setting up Analytics Database...")
    print("=" * 50)
    
    try:
        # Get database manager
        db_manager = get_database_manager()
        print("✅ Database manager initialized")
        
        # Create tables
        print("\n📋 Creating database tables...")
        if db_manager.create_tables():
            print("✅ Database tables created successfully")
        else:
            print("❌ Failed to create database tables")
            return False
        
        # Create sample conversation data
        print("\n📊 Creating sample conversation data...")
        if db_manager.create_sample_conversation_data():
            print("✅ Sample conversation data created successfully")
        else:
            print("❌ Failed to create sample conversation data")
            return False
        
        # Test analytics engine
        print("\n🧪 Testing analytics engine...")
        analytics_engine = get_analytics_engine()
        
        # Test conversation metrics
        conv_metrics = analytics_engine.get_conversation_metrics(MetricPeriod.LAST_DAY)
        print(f"   Total Sessions: {conv_metrics.total_sessions}")
        print(f"   Active Sessions: {conv_metrics.active_sessions}")
        print(f"   Completed Sessions: {conv_metrics.completed_sessions}")
        
        # Test product metrics
        prod_metrics = analytics_engine.get_product_metrics(MetricPeriod.LAST_DAY)
        print(f"   Total Recommendations: {prod_metrics.total_recommendations}")
        print(f"   Unique Products: {prod_metrics.unique_products_recommended}")
        
        # Test comprehensive dashboard
        dashboard_data = analytics_engine.get_comprehensive_dashboard_data(MetricPeriod.LAST_DAY)
        if "error" not in dashboard_data:
            print("✅ Analytics engine working correctly")
        else:
            print(f"❌ Analytics engine error: {dashboard_data['error']}")
            return False
        
        print("\n🎉 Analytics Database Setup Completed Successfully!")
        print("You can now access the staff dashboard with real analytics data.")
        print("Dashboard URL: http://localhost:8000/staff/dashboard")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = setup_analytics_database()
    if not success:
        sys.exit(1)
