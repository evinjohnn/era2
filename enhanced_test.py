#!/usr/bin/env python3
"""
Enhanced Retail AI Assistant Test Suite
Tests PostgreSQL, enhanced conversation engine, analytics, and staff dashboard
"""

import requests
import json
import time
import sys
from datetime import datetime

class EnhancedRetailAITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.session_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            start_time = time.time()
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            
            elapsed_time = (time.time() - start_time) * 1000
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}, Time: {elapsed_time:.2f}ms")
                result = {"status": "passed", "name": name, "response_time": elapsed_time}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                result = {"status": "failed", "name": name, "error": f"Expected {expected_status}, got {response.status_code}"}
            
            try:
                response_data = response.json()
                result["response"] = response_data
                return success, response_data, result
            except:
                result["response"] = response.text
                return success, response.text, result

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            result = {"status": "error", "name": name, "error": str(e)}
            self.test_results.append(result)
            return False, None, result

    def test_enhanced_stats(self):
        """Test enhanced system statistics"""
        success, response, result = self.run_test(
            "Enhanced System Stats",
            "GET",
            "admin/enhanced-stats",
            200
        )
        
        if success and response:
            system_status = response.get("system_status")
            database = response.get("database")
            print(f"  System Status: {system_status}")
            print(f"  Database: {database}")
            
            if response.get("database_stats"):
                db_stats = response.get("database_stats")
                print(f"  Products: {db_stats.get('products', 0)}")
                print(f"  Sessions: {db_stats.get('sessions', 0)}")
                print(f"  Messages: {db_stats.get('messages', 0)}")
            
            if response.get("vector_database"):
                vector_db = response.get("vector_database")
                print(f"  Vector DB Products: {vector_db.get('total_products', 0)}")
        
        self.test_results.append(result)
        return success, response

    def test_enhanced_chat(self, message):
        """Test enhanced chat endpoint"""
        data = {"session_id": self.session_id, "message": message}
        success, response, result = self.run_test(
            f"Enhanced Chat: '{message}'",
            "POST",
            "chat",
            200,
            data=data
        )
        
        if success and response:
            self.session_id = response.get("session_id")
            print(f"  Response: '{response.get('reply')}'")
            print(f"  Enhanced Mode: {response.get('metadata', {}).get('enhanced_mode', False)}")
            print(f"  Database Enabled: {response.get('metadata', {}).get('database_enabled', False)}")
            print(f"  Conversation Tracking: {response.get('metadata', {}).get('conversation_tracking', False)}")
            
            if response.get("products"):
                print(f"  Products returned: {len(response.get('products'))}")
        
        self.test_results.append(result)
        return success, response

    def test_staff_dashboard(self):
        """Test staff dashboard endpoints"""
        # Test metrics
        success1, response1, result1 = self.run_test(
            "Staff Dashboard Metrics",
            "GET",
            "staff/api/metrics",
            200
        )
        
        if success1 and response1:
            conv_perf = response1.get("conversation_performance", {})
            print(f"  Total Sessions: {conv_perf.get('total_sessions', 0)}")
            print(f"  Active Sessions: {conv_perf.get('active_sessions', 0)}")
            print(f"  Messages per Session: {conv_perf.get('messages_per_session', 0)}")
        
        # Test health
        success2, response2, result2 = self.run_test(
            "Staff Dashboard Health",
            "GET",
            "staff/api/health",
            200
        )
        
        if success2 and response2:
            status = response2.get("status", "unknown")
            print(f"  System Health: {status}")
        
        self.test_results.extend([result1, result2])
        return success1 and success2

    def test_conversation_flow(self):
        """Test enhanced conversation flow"""
        print("\n🔄 Testing Enhanced Conversation Flow...")
        
        # Start conversation
        success1, response1 = self.test_enhanced_chat("hi_ai_assistant")
        if not success1:
            return False
        
        # Express interest
        success2, response2 = self.test_enhanced_chat("I'm looking for an elegant engagement ring")
        if not success2:
            return False
        
        # Provide preferences
        success3, response3 = self.test_enhanced_chat("I want gold with diamonds, budget around 2000")
        if not success3:
            return False
        
        # Request recommendations
        success4, response4 = self.test_enhanced_chat("show me some options")
        if not success4:
            return False
        
        # Check if we got products in any response
        has_products = any([
            response.get("products") and len(response.get("products")) > 0
            for response in [response1, response2, response3, response4]
            if response
        ])
        
        if has_products:
            print("✅ Enhanced conversation flow test passed with product recommendations")
            return True
        else:
            print("❌ Enhanced conversation flow test failed - no product recommendations received")
            return False

    def test_analytics_metrics(self):
        """Test analytics and metrics"""
        success, response, result = self.run_test(
            "Analytics Metrics",
            "GET",
            "admin/conversation-metrics",
            200,
            params={"period": "last_day"}
        )
        
        if success and response:
            metrics = response.get("metrics", {})
            print(f"  Total Sessions: {metrics.get('total_sessions', 0)}")
            print(f"  Active Sessions: {metrics.get('active_sessions', 0)}")
            print(f"  Average Duration: {metrics.get('average_session_duration', 0):.2f}s")
            print(f"  Handoff Rate: {metrics.get('handoff_rate', 0):.2%}")
        
        self.test_results.append(result)
        return success

    def run_comprehensive_tests(self):
        """Run comprehensive test suite"""
        print("=" * 60)
        print("Enhanced Retail AI Assistant Test Suite")
        print(f"Testing Enhanced System at: {self.base_url}")
        print("=" * 60)
        
        # Test enhanced system
        self.test_enhanced_stats()
        
        # Test conversation flow
        self.test_conversation_flow()
        
        # Test staff dashboard
        self.test_staff_dashboard()
        
        # Test analytics
        self.test_analytics_metrics()
        
        # Test vector search compatibility
        success, response, result = self.run_test(
            "Vector Search Test",
            "GET",
            "admin/test-vector-search",
            200,
            params={"query": "elegant engagement ring"}
        )
        
        if success and response:
            results_count = response.get("results_count", 0)
            print(f"  Vector Search Results: {results_count}")
        
        self.test_results.append(result)

    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n📊 Enhanced Test Summary:")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run) * 100:.1f}%")
        
        # Check enhanced features
        enhanced_working = any(
            result.get("name") == "Enhanced System Stats" and 
            result.get("status") == "passed" and
            result.get("response", {}).get("system_status") == "enhanced_with_postgresql"
            for result in self.test_results
        )
        
        if enhanced_working:
            print("✅ Enhanced PostgreSQL System: Working")
        else:
            print("❌ Enhanced PostgreSQL System: Not working")
        
        # Check conversation engine
        conversation_working = any(
            result.get("name", "").startswith("Enhanced Chat") and 
            result.get("status") == "passed" and
            result.get("response", {}).get("metadata", {}).get("enhanced_mode") == True
            for result in self.test_results
        )
        
        if conversation_working:
            print("✅ Enhanced Conversation Engine: Working")
        else:
            print("❌ Enhanced Conversation Engine: Not working")
        
        # Check staff dashboard
        dashboard_working = any(
            result.get("name", "").startswith("Staff Dashboard") and 
            result.get("status") == "passed"
            for result in self.test_results
        )
        
        if dashboard_working:
            print("✅ Staff Dashboard: Working")
        else:
            print("❌ Staff Dashboard: Not working")

def main():
    print("🚀 Starting Enhanced Retail AI Assistant Tests...")
    
    tester = EnhancedRetailAITester()
    
    # Run comprehensive tests
    tester.run_comprehensive_tests()
    
    # Print summary
    tester.print_summary()
    
    # Return success if most tests passed
    success_rate = (tester.tests_passed / tester.tests_run) * 100 if tester.tests_run > 0 else 0
    return 0 if success_rate >= 80 else 1

if __name__ == "__main__":
    sys.exit(main())