#!/usr/bin/env python3
import requests
import json
import time
import sys
from datetime import datetime

class RetailAITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.session_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Check if we're running in a container environment
        import os
        if os.environ.get("REACT_APP_BACKEND_URL"):
            self.base_url = os.environ.get("REACT_APP_BACKEND_URL")
            print(f"Using environment backend URL: {self.base_url}")

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
            
            elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
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

    def test_chat_endpoint(self, message):
        """Test the chat endpoint with a message"""
        data = {"session_id": self.session_id, "message": message}
        success, response, result = self.run_test(
            f"Chat: '{message}'",
            "POST",
            "chat",
            200,
            data=data
        )
        
        if success and response:
            self.session_id = response.get("session_id")
            print(f"  Response: '{response.get('reply')}'")
            if response.get("products"):
                print(f"  Products returned: {len(response.get('products'))}")
        
        self.test_results.append(result)
        return success, response

    def test_vector_stats(self):
        """Test the vector stats endpoint"""
        success, response, result = self.run_test(
            "Vector Stats",
            "GET",
            "admin/vector-stats",
            200
        )
        
        if success and response:
            system_status = response.get("system_status", "unknown")
            print(f"  System Status: {system_status}")
            
            if response.get("vector_database"):
                vector_db = response.get("vector_database")
                print(f"  Vector Database: {vector_db.get('total_products', 0)} products")
                print(f"  Embedding Model: {vector_db.get('embedding_model', 'unknown')}")
        
        self.test_results.append(result)
        return success, response

    def test_vector_search(self, query):
        """Test the vector search endpoint"""
        success, response, result = self.run_test(
            f"Vector Search: '{query}'",
            "GET",
            "admin/test-vector-search",
            200,
            params={"query": query}
        )
        
        if success and response:
            results_count = response.get("results_count", 0)
            print(f"  Results Count: {results_count}")
            
            if response.get("results") and len(response.get("results")) > 0:
                top_result = response.get("results")[0]
                print(f"  Top Result: {top_result.get('name')} (Score: {top_result.get('similarity_score', 0):.3f})")
        
        self.test_results.append(result)
        return success, response

    def test_new_session_endpoint(self):
        """Test the new session endpoint"""
        # First create a session
        success1, response1 = self.test_chat_endpoint("hi_ai_assistant")
        if not success1:
            return False
        
        session_id = response1.get("session_id")
        if not session_id:
            print("❌ No session ID returned")
            return False
        
        # Add some data to the session
        success2, response2 = self.test_chat_endpoint("I'm looking for a gold ring")
        if not success2:
            return False
            
        # Test clearing the session
        data = {"session_id": session_id}
        success, response, result = self.run_test(
            "New Session Endpoint",
            "POST",
            "new-session",
            200,
            data=data
        )
        
        if success and response:
            status = response.get("status")
            print(f"  Session Clear Status: {status}")
            if status in ["cleared", "not_found"]:
                print("✅ Session clearing worked correctly")
                
                # Verify session was actually cleared by starting a new conversation
                success3, response3 = self.test_chat_endpoint("hi_ai_assistant")
                if not success3:
                    return False
                    
                new_session_id = response3.get("session_id")
                if new_session_id != session_id:
                    print(f"✅ New session created after clearing: {new_session_id}")
                else:
                    print("⚠️ Same session ID returned after clearing")
                
                self.test_results.append(result)
                return True
        
        print("❌ Session clearing failed")
        self.test_results.append(result)
        return False

    def test_redis_stats(self):
        """Test the Redis stats endpoint"""
        success, response, result = self.run_test(
            "Redis Stats",
            "GET",
            "admin/redis-stats",
            200
        )
        
        if success and response:
            redis_available = response.get("redis_available", False)
            print(f"  Redis Available: {redis_available}")
            
            if redis_available and response.get("stats"):
                stats = response.get("stats")
                print(f"  Redis Version: {stats.get('redis_version', 'unknown')}")
                print(f"  Connected Clients: {stats.get('connected_clients', 0)}")
                print(f"  Memory Used: {stats.get('used_memory_human', 'unknown')}")
        
        self.test_results.append(result)
        return success, response

    def test_item_details_functionality(self):
        """Test the item details functionality"""
        # First get some products
        success1, response1 = self.test_chat_endpoint("show me rings")
        if not success1:
            return False
        
        # Test item details request
        success2, response2 = self.test_chat_endpoint("item_details:test_product")
        if success2:
            print("✅ Item details functionality working")
            return True
        else:
            print("❌ Item details functionality failed")
            return False

    def run_conversation_flow_test(self):
        """Test a complete conversation flow"""
        print("\n🔄 Testing Conversation Flow...")
        
        # Initial greeting
        success1, response1 = self.test_chat_endpoint("hi_ai_assistant")
        if not success1:
            return False
        
        # Ask for elegant engagement ring
        success2, response2 = self.test_chat_endpoint("I'm looking for an elegant engagement ring")
        if not success2:
            return False
        
        # Specify gold material
        success3, response3 = self.test_chat_endpoint("I want it to be gold with diamonds")
        if not success3:
            return False
        
        # Specify budget
        success4, response4 = self.test_chat_endpoint("My budget is around $2000")
        if not success4:
            return False
        
        # Test staff assistance feature
        success5, response5 = self.test_chat_endpoint("request_staff_assistance_dialogue")
        if not success5:
            return False
        
        if response5 and response5.get("end_conversation") == True:
            print("✅ Staff assistance feature working correctly")
        
        # Check if we got product recommendations in earlier responses
        if response4 and response4.get("products") and len(response4.get("products")) > 0:
            print("✅ Conversation flow test passed with product recommendations")
            return True
        else:
            print("❌ Conversation flow test failed - no product recommendations received")
            return False

    def test_redis_session_persistence(self):
        """Test Redis session persistence across multiple requests"""
        print("\n🔄 Testing Redis Session Persistence...")
        
        # Step 1: Create a new session
        success1, response1 = self.test_chat_endpoint("hi_ai_assistant")
        if not success1 or not response1:
            print("❌ Failed to create initial session")
            return False
            
        session_id = response1.get("session_id")
        if not session_id:
            print("❌ No session ID returned")
            return False
            
        print(f"  Created session: {session_id}")
        
        # Step 2: Set some preferences in the session
        success2, response2 = self.test_chat_endpoint("I'm looking for a gold ring")
        if not success2:
            return False
            
        # Step 3: Check Redis stats to confirm Redis is working
        success3, response3 = self.test_redis_stats()
        if not success3 or not response3:
            print("❌ Redis stats endpoint failed")
            return False
            
        redis_available = response3.get("redis_available", False)
        if not redis_available:
            print("⚠️ Redis not available, test will check in-memory fallback")
        else:
            print("✅ Redis is available")
            
        # Step 4: Send another message to check if preferences persist
        success4, response4 = self.test_chat_endpoint("My budget is $2000")
        if not success4:
            return False
            
        # Step 5: Check if we get product recommendations based on previous preferences
        success5, response5 = self.test_chat_endpoint("Show me some options")
        if not success5:
            return False
            
        if response5 and response5.get("products") and len(response5.get("products")) > 0:
            print(f"✅ Session persistence working - received {len(response5.get('products'))} products based on preferences")
            return True
        else:
            print("❌ Session persistence test failed - no products received based on preferences")
            return False
    def run_semantic_search_tests(self):
        """Run tests for semantic search with different queries"""
        print("\n🔍 Testing Semantic Search Capabilities...")
        
        queries = [
            "elegant engagement ring",
            "gold necklace for anniversary",
            "diamond bracelet"
        ]
        
        all_passed = True
        for query in queries:
            success, response = self.test_vector_search(query)
            if not success or not response or response.get("results_count", 0) == 0:
                all_passed = False
        
        return all_passed

    def print_summary(self):
        """Print test summary"""
        print("\n📊 Test Summary:")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run) * 100:.1f}%")
        
        # Check if RAG system is working
        rag_working = any(
            result.get("name") == "Vector Stats" and 
            result.get("status") == "passed" and
            result.get("response", {}).get("system_status") == "enhanced_with_rag"
            for result in self.test_results
        )
        
        if rag_working:
            print("✅ RAG System: Working")
        else:
            print("❌ RAG System: Not working or not properly configured")
        
        # Check response times for vector search
        vector_search_times = [
            result.get("response_time", 0)
            for result in self.test_results
            if result.get("name", "").startswith("Vector Search") and result.get("status") == "passed"
        ]
        
        if vector_search_times:
            avg_time = sum(vector_search_times) / len(vector_search_times)
            print(f"Vector Search Avg Response Time: {avg_time:.2f}ms")
            if avg_time <= 200:
                print("✅ Response Time: Under 200ms target")
            else:
                print(f"❌ Response Time: Above 200ms target ({avg_time:.2f}ms)")

def main():
    # Get the base URL from environment or use default
    import os
    base_url = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
    
    print("=" * 50)
    print("Retail AI Assistant API Test Suite")
    print(f"Testing API at: {base_url}")
    print("=" * 50)
    
    tester = RetailAITester(base_url)
    
    # Test Redis functionality
    tester.test_redis_stats()
    
    # Test Redis session persistence
    tester.test_redis_session_persistence()
    
    # Test new session endpoint
    tester.test_new_session_endpoint()
    
    # Test vector database stats
    tester.test_vector_stats()
    
    # Test semantic search
    tester.test_vector_search("elegant engagement ring")
    tester.test_vector_search("gold necklace for anniversary")
    tester.test_vector_search("diamond bracelet under $1000")
    
    # Test item details functionality
    tester.test_item_details_functionality()
    
    # Test conversation flow
    tester.run_conversation_flow_test()
    
    # Run additional semantic search tests
    tester.run_semantic_search_tests()
    
    # Print summary
    tester.print_summary()
    
    # Return success if all tests passed
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())