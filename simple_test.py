#!/usr/bin/env python3
"""
Simple test script for the dynamic scheduling system
Tests endpoints that don't require authentication
"""

import httpx
import json
import asyncio

async def test_endpoints():
    """Test the scheduling system endpoints"""
    
    print("🧪 Testing Dynamic Scheduling System")
    print("=" * 50)
    
    # Test 1: Check if backend is running
    print("\n1. Testing Backend Health...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/")
            if response.status_code == 200:
                print("✅ Backend is running")
            else:
                print(f"❌ Backend returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")
    
    # Test 2: Check OpenAPI docs
    print("\n2. Testing API Documentation...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/docs")
            if response.status_code == 200:
                print("✅ API docs available")
            else:
                print(f"❌ API docs returned status {response.status_code}")
    except Exception as e:
        print(f"❌ API docs failed: {e}")
    
    # Test 3: Check if automation endpoints exist
    print("\n3. Testing Automation Endpoints...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/v1/openapi.json")
            if response.status_code == 200:
                openapi_spec = response.json()
                paths = openapi_spec.get("paths", {})
                
                # Check for our automation endpoints
                automation_endpoints = [
                    "/api/v1/automation/todos",
                    "/api/v1/automation/timetable", 
                    "/api/v1/automation/study-schedule",
                    "/api/v1/automation/delayed-automation"
                ]
                
                for endpoint in automation_endpoints:
                    if endpoint in paths:
                        print(f"✅ {endpoint} - Available")
                    else:
                        print(f"❌ {endpoint} - Missing")
                        
            else:
                print(f"❌ OpenAPI spec returned status {response.status_code}")
    except Exception as e:
        print(f"❌ OpenAPI spec failed: {e}")
    
    # Test 4: Check reminder server
    print("\n4. Testing Reminder Server...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8003/health")
            if response.status_code == 200:
                print("✅ Reminder server is running")
            else:
                print(f"❌ Reminder server returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Reminder server connection failed: {e}")
    
    # Test 5: Check orchestrator
    print("\n5. Testing Orchestrator...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8010/health")
            if response.status_code == 200:
                print("✅ Orchestrator is running")
            else:
                print(f"❌ Orchestrator returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Orchestrator connection failed: {e}")
    
    # Test 6: Test reminder creation (this should work without auth)
    print("\n6. Testing Reminder Creation...")
    try:
        async with httpx.AsyncClient() as client:
            reminder_data = {
                "time_str": "in 1 minute",
                "message": "Test reminder from integration test",
                "user_id": "test-user-123"
            }
            response = await client.post(
                "http://localhost:8003/execute/set_reminder",
                json=reminder_data,
                timeout=10
            )
            if response.status_code == 200:
                print("✅ Reminder created successfully")
                result = response.json()
                print(f"   Job ID: {result.get('job_id', 'N/A')}")
            else:
                print(f"❌ Reminder creation failed: {response.status_code}")
                print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Reminder creation failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Simple test completed!")

if __name__ == "__main__":
    asyncio.run(test_endpoints())
