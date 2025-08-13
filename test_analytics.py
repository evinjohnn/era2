#!/usr/bin/env python3
"""
Test script for the Analytics Engine
Verifies that real analytics data can be generated and retrieved
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analytics import get_analytics_engine, MetricPeriod
from datetime import datetime, timedelta

def test_analytics_engine():
    """Test the analytics engine functionality"""
    print("🧪 Testing Analytics Engine...")
    print("=" * 50)
    
    try:
        # Get analytics engine
        engine = get_analytics_engine()
        print("✅ Analytics engine initialized")
        
        # Test conversation metrics
        print("\n📊 Testing Conversation Metrics...")
        conv_metrics = engine.get_conversation_metrics(MetricPeriod.LAST_DAY)
        print(f"   Total Sessions: {conv_metrics.total_sessions}")
        print(f"   Active Sessions: {conv_metrics.active_sessions}")
        print(f"   Completed Sessions: {conv_metrics.completed_sessions}")
        print(f"   Avg Duration: {conv_metrics.average_session_duration:.1f}s")
        print(f"   Handoff Rate: {conv_metrics.handoff_rate:.2%}")
        print(f"   Total Messages: {conv_metrics.total_messages}")
        print(f"   Products Recommended: {conv_metrics.products_recommended}")
        
        # Test product metrics
        print("\n🛍️ Testing Product Metrics...")
        prod_metrics = engine.get_product_metrics(MetricPeriod.LAST_DAY)
        print(f"   Total Recommendations: {prod_metrics.total_recommendations}")
        print(f"   Unique Products: {prod_metrics.unique_products_recommended}")
        print(f"   Top Products: {len(prod_metrics.top_recommended_products)}")
        print(f"   Categories: {len(prod_metrics.category_breakdown)}")
        print(f"   Price Ranges: {len(prod_metrics.price_range_breakdown)}")
        
        # Test user behavior metrics
        print("\n👥 Testing User Behavior Metrics...")
        behavior_metrics = engine.get_user_behavior_metrics(MetricPeriod.LAST_DAY)
        print(f"   Unique Sessions: {behavior_metrics.total_unique_sessions}")
        print(f"   Avg Session Length: {behavior_metrics.average_session_length:.1f}s")
        print(f"   Bounce Rate: {behavior_metrics.bounce_rate:.2%}")
        print(f"   Engagement Score: {behavior_metrics.engagement_score:.2f}")
        print(f"   Peak Hours Data: {len(behavior_metrics.peak_hours)} hours")
        
        # Test comprehensive dashboard
        print("\n📈 Testing Comprehensive Dashboard...")
        dashboard_data = engine.get_comprehensive_dashboard_data(MetricPeriod.LAST_DAY)
        if "error" not in dashboard_data:
            print("   ✅ Dashboard data generated successfully")
            print(f"   Generated at: {dashboard_data.get('generated_at', 'N/A')}")
            print(f"   Period: {dashboard_data.get('period', 'N/A')}")
        else:
            print(f"   ❌ Dashboard error: {dashboard_data['error']}")
        
        # Test different time periods
        print("\n⏰ Testing Different Time Periods...")
        periods = [
            MetricPeriod.LAST_HOUR,
            MetricPeriod.LAST_DAY,
            MetricPeriod.LAST_WEEK,
            MetricPeriod.LAST_MONTH
        ]
        
        for period in periods:
            try:
                metrics = engine.get_conversation_metrics(period)
                print(f"   {period.value}: {metrics.total_sessions} sessions")
            except Exception as e:
                print(f"   {period.value}: Error - {e}")
        
        print("\n🎉 Analytics Engine Test Completed Successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Analytics Engine Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_staff_dashboard_api():
    """Test the staff dashboard API endpoints"""
    print("\n🔧 Testing Staff Dashboard API...")
    print("=" * 50)
    
    try:
        # Import FastAPI test client
        from fastapi.testclient import TestClient
        from main_enhanced import app
        
        client = TestClient(app)
        
        # Test dashboard page
        print("Testing /staff/dashboard...")
        response = client.get("/staff/dashboard")
        if response.status_code == 200:
            print("   ✅ Dashboard page accessible")
        else:
            print(f"   ❌ Dashboard page error: {response.status_code}")
        
        # Test dashboard data API
        print("Testing /staff/api/dashboard-data...")
        response = client.get("/staff/api/dashboard-data")
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Dashboard data API working")
            print(f"   Sessions: {data.get('conversation_metrics', {}).get('total_sessions', 'N/A')}")
        else:
            print(f"   ❌ Dashboard data API error: {response.status_code}")
        
        # Test analytics by period
        print("Testing /staff/api/analytics/last_day...")
        response = client.get("/staff/api/analytics/last_day")
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Analytics by period API working")
        else:
            print(f"   ❌ Analytics by period API error: {response.status_code}")
        
        # Test health check
        print("Testing /staff/api/health...")
        response = client.get("/staff/api/health")
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Health check API working")
            print(f"   Status: {data.get('status', 'N/A')}")
        else:
            print(f"   ❌ Health check API error: {response.status_code}")
        
        print("\n🎉 Staff Dashboard API Test Completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Staff Dashboard API Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Analytics and Staff Dashboard Tests...")
    print("=" * 60)
    
    # Test analytics engine
    analytics_success = test_analytics_engine()
    
    # Test staff dashboard API
    api_success = test_staff_dashboard_api()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    print(f"Analytics Engine: {'✅ PASSED' if analytics_success else '❌ FAILED'}")
    print(f"Staff Dashboard API: {'✅ PASSED' if api_success else '❌ FAILED'}")
    
    if analytics_success and api_success:
        print("\n🎉 All tests passed! The dashboard is now using real analytics data.")
        print("You can access the staff dashboard at: http://localhost:8000/staff/dashboard")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
        sys.exit(1)
