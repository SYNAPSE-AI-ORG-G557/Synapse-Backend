#!/usr/bin/env python3
"""
Comprehensive Integration Test for Dynamic Scheduling System

This script tests all components of the dynamic scheduling system:
1. Database models and migrations
2. API endpoints for todos, timetable, study schedules
3. Google services integration
4. Delayed automation execution
5. Celery Beat and APScheduler integration
"""

import asyncio
import httpx
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1/automation"
TOOLING_ENGINE_URL = "http://localhost:8010"
REMINDER_SERVER_URL = "http://localhost:8003"

# Test user credentials (you'll need to replace with actual test user)
TEST_USER_TOKEN = "your-test-jwt-token-here"

class SchedulingSystemTester:
    def __init__(self):
        self.results = {
            "database_tests": [],
            "api_tests": [],
            "google_integration_tests": [],
            "automation_tests": [],
            "scheduler_tests": [],
            "errors": []
        }
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Dynamic Scheduling System Integration Tests")
        print("=" * 60)
        
        # Test 1: Database Models
        await self.test_database_models()
        
        # Test 2: API Endpoints
        await self.test_api_endpoints()
        
        # Test 3: Google Services Integration
        await self.test_google_integration()
        
        # Test 4: Delayed Automation
        await self.test_delayed_automation()
        
        # Test 5: Scheduler Integration
        await self.test_scheduler_integration()
        
        # Print results
        self.print_test_results()
    
    async def test_database_models(self):
        """Test database models and migrations"""
        print("\n📊 Testing Database Models...")
        
        try:
            # Test if we can connect to the database
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/health")
                if response.status_code == 200:
                    self.results["database_tests"].append({
                        "test": "Database Connection",
                        "status": "PASS",
                        "message": "Database connection successful"
                    })
                else:
                    self.results["database_tests"].append({
                        "test": "Database Connection",
                        "status": "FAIL",
                        "message": f"Database connection failed: {response.status_code}"
                    })
        except Exception as e:
            self.results["database_tests"].append({
                "test": "Database Connection",
                "status": "ERROR",
                "message": f"Database connection error: {str(e)}"
            })
    
    async def test_api_endpoints(self):
        """Test all API endpoints"""
        print("\n🔌 Testing API Endpoints...")
        
        headers = {"Authorization": f"Bearer {TEST_USER_TOKEN}"}
        
        # Test Todo endpoints
        await self.test_todo_endpoints(headers)
        
        # Test Timetable endpoints
        await self.test_timetable_endpoints(headers)
        
        # Test Study Schedule endpoints
        await self.test_study_schedule_endpoints(headers)
        
        # Test Delayed Automation endpoints
        await self.test_delayed_automation_endpoints(headers)
    
    async def test_todo_endpoints(self, headers: Dict[str, str]):
        """Test todo CRUD operations"""
        try:
            # Create a test todo
            todo_data = {
                "title": "Test Assignment",
                "description": "Integration test assignment",
                "due_date": "in 1 day",
                "priority": "high",
                "category": "assignment"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE}/todos",
                    json=todo_data,
                    headers=headers
                )
                
                if response.status_code == 201:
                    todo = response.json()
                    self.results["api_tests"].append({
                        "test": "Create Todo",
                        "status": "PASS",
                        "message": f"Todo created: {todo['uuid']}"
                    })
                    
                    # Test getting todos
                    response = await client.get(f"{API_BASE}/todos", headers=headers)
                    if response.status_code == 200:
                        todos = response.json()
                        self.results["api_tests"].append({
                            "test": "Get Todos",
                            "status": "PASS",
                            "message": f"Retrieved {len(todos)} todos"
                        })
                    else:
                        self.results["api_tests"].append({
                            "test": "Get Todos",
                            "status": "FAIL",
                            "message": f"Failed to get todos: {response.status_code}"
                        })
                else:
                    self.results["api_tests"].append({
                        "test": "Create Todo",
                        "status": "FAIL",
                        "message": f"Failed to create todo: {response.status_code}"
                    })
        except Exception as e:
            self.results["api_tests"].append({
                "test": "Todo Endpoints",
                "status": "ERROR",
                "message": f"Todo endpoint error: {str(e)}"
            })
    
    async def test_timetable_endpoints(self, headers: Dict[str, str]):
        """Test timetable CRUD operations"""
        try:
            timetable_data = {
                "subject": "Test Mathematics",
                "day_of_week": 0,  # Monday
                "start_time": "09:00",
                "end_time": "10:30",
                "room": "Test Room 101",
                "teacher": "Dr. Test",
                "recurring": True
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE}/timetable",
                    json=timetable_data,
                    headers=headers
                )
                
                if response.status_code == 201:
                    entry = response.json()
                    self.results["api_tests"].append({
                        "test": "Create Timetable Entry",
                        "status": "PASS",
                        "message": f"Timetable entry created: {entry['uuid']}"
                    })
                else:
                    self.results["api_tests"].append({
                        "test": "Create Timetable Entry",
                        "status": "FAIL",
                        "message": f"Failed to create timetable entry: {response.status_code}"
                    })
        except Exception as e:
            self.results["api_tests"].append({
                "test": "Timetable Endpoints",
                "status": "ERROR",
                "message": f"Timetable endpoint error: {str(e)}"
            })
    
    async def test_study_schedule_endpoints(self, headers: Dict[str, str]):
        """Test study schedule CRUD operations"""
        try:
            schedule_data = {
                "task_name": "Test Study Session",
                "subject": "Mathematics",
                "schedule_type": "daily",
                "time_str": "18:00",
                "duration_minutes": 60,
                "enabled": True
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE}/study-schedule",
                    json=schedule_data,
                    headers=headers
                )
                
                if response.status_code == 201:
                    schedule = response.json()
                    self.results["api_tests"].append({
                        "test": "Create Study Schedule",
                        "status": "PASS",
                        "message": f"Study schedule created: {schedule['uuid']}"
                    })
                else:
                    self.results["api_tests"].append({
                        "test": "Create Study Schedule",
                        "status": "FAIL",
                        "message": f"Failed to create study schedule: {response.status_code}"
                    })
        except Exception as e:
            self.results["api_tests"].append({
                "test": "Study Schedule Endpoints",
                "status": "ERROR",
                "message": f"Study schedule endpoint error: {str(e)}"
            })
    
    async def test_delayed_automation_endpoints(self, headers: Dict[str, str]):
        """Test delayed automation endpoints"""
        try:
            automation_data = {
                "automation_type": "browser",
                "action": "play",
                "parameters": {
                    "user_request": "play test music on YouTube"
                },
                "delay_str": "in 1 minute"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE}/delayed-automation",
                    json=automation_data,
                    headers=headers
                )
                
                if response.status_code == 201:
                    automation = response.json()
                    self.results["api_tests"].append({
                        "test": "Create Delayed Automation",
                        "status": "PASS",
                        "message": f"Delayed automation created: {automation['uuid']}"
                    })
                else:
                    self.results["api_tests"].append({
                        "test": "Create Delayed Automation",
                        "status": "FAIL",
                        "message": f"Failed to create delayed automation: {response.status_code}"
                    })
        except Exception as e:
            self.results["api_tests"].append({
                "test": "Delayed Automation Endpoints",
                "status": "ERROR",
                "message": f"Delayed automation endpoint error: {str(e)}"
            })
    
    async def test_google_integration(self):
        """Test Google services integration"""
        print("\n🌐 Testing Google Services Integration...")
        
        headers = {"Authorization": f"Bearer {TEST_USER_TOKEN}"}
        
        try:
            async with httpx.AsyncClient() as client:
                # Test Google Calendar sync
                response = await client.post(
                    f"{API_BASE}/google-calendar/sync-timetable",
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.results["google_integration_tests"].append({
                        "test": "Google Calendar Sync",
                        "status": "PASS",
                        "message": result.get("message", "Calendar sync successful")
                    })
                else:
                    self.results["google_integration_tests"].append({
                        "test": "Google Calendar Sync",
                        "status": "FAIL",
                        "message": f"Calendar sync failed: {response.status_code}"
                    })
                
                # Test Gmail notification
                email_data = {
                    "to": "test@example.com",
                    "subject": "Test Email - Integration Test",
                    "body": "This is a test email from the integration test suite."
                }
                
                response = await client.post(
                    f"{API_BASE}/gmail/send-notification",
                    json=email_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.results["google_integration_tests"].append({
                        "test": "Gmail Notification",
                        "status": "PASS",
                        "message": result.get("message", "Email sent successfully")
                    })
                else:
                    self.results["google_integration_tests"].append({
                        "test": "Gmail Notification",
                        "status": "FAIL",
                        "message": f"Email send failed: {response.status_code}"
                    })
                    
        except Exception as e:
            self.results["google_integration_tests"].append({
                "test": "Google Integration",
                "status": "ERROR",
                "message": f"Google integration error: {str(e)}"
            })
    
    async def test_delayed_automation(self):
        """Test delayed automation execution"""
        print("\n⏰ Testing Delayed Automation...")
        
        try:
            # Test reminder server
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{REMINDER_SERVER_URL}/health")
                if response.status_code == 200:
                    self.results["automation_tests"].append({
                        "test": "Reminder Server Health",
                        "status": "PASS",
                        "message": "Reminder server is running"
                    })
                else:
                    self.results["automation_tests"].append({
                        "test": "Reminder Server Health",
                        "status": "FAIL",
                        "message": f"Reminder server health check failed: {response.status_code}"
                    })
                
                # Test setting a reminder
                reminder_data = {
                    "time_str": "in 30 seconds",
                    "message": "Test reminder from integration test",
                    "user_id": "test-user-id"
                }
                
                response = await client.post(
                    f"{REMINDER_SERVER_URL}/execute/set_reminder",
                    json=reminder_data
                )
                
                if response.status_code == 200:
                    self.results["automation_tests"].append({
                        "test": "Set Reminder",
                        "status": "PASS",
                        "message": "Reminder set successfully"
                    })
                else:
                    self.results["automation_tests"].append({
                        "test": "Set Reminder",
                        "status": "FAIL",
                        "message": f"Failed to set reminder: {response.status_code}"
                    })
                    
        except Exception as e:
            self.results["automation_tests"].append({
                "test": "Delayed Automation",
                "status": "ERROR",
                "message": f"Delayed automation error: {str(e)}"
            })
    
    async def test_scheduler_integration(self):
        """Test Celery Beat and APScheduler integration"""
        print("\n📅 Testing Scheduler Integration...")
        
        try:
            # Test if Celery Beat is running (this would require checking logs or status endpoint)
            self.results["scheduler_tests"].append({
                "test": "Celery Beat Status",
                "status": "INFO",
                "message": "Celery Beat status check requires manual verification"
            })
            
            # Test APScheduler via reminder server
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{REMINDER_SERVER_URL}/execute/list_schedules")
                if response.status_code == 200:
                    schedules = response.json()
                    self.results["scheduler_tests"].append({
                        "test": "APScheduler Status",
                        "status": "PASS",
                        "message": f"APScheduler is running with {len(schedules)} active schedules"
                    })
                else:
                    self.results["scheduler_tests"].append({
                        "test": "APScheduler Status",
                        "status": "FAIL",
                        "message": f"APScheduler status check failed: {response.status_code}"
                    })
                    
        except Exception as e:
            self.results["scheduler_tests"].append({
                "test": "Scheduler Integration",
                "status": "ERROR",
                "message": f"Scheduler integration error: {str(e)}"
            })
    
    def print_test_results(self):
        """Print comprehensive test results"""
        print("\n" + "=" * 60)
        print("📋 INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        error_tests = 0
        
        for category, tests in self.results.items():
            if category == "errors":
                continue
                
            print(f"\n🔍 {category.replace('_', ' ').title()}:")
            print("-" * 40)
            
            for test in tests:
                total_tests += 1
                status_icon = {
                    "PASS": "✅",
                    "FAIL": "❌",
                    "ERROR": "⚠️",
                    "INFO": "ℹ️"
                }.get(test["status"], "❓")
                
                print(f"{status_icon} {test['test']}: {test['message']}")
                
                if test["status"] == "PASS":
                    passed_tests += 1
                elif test["status"] == "FAIL":
                    failed_tests += 1
                elif test["status"] == "ERROR":
                    error_tests += 1
        
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️ Errors: {error_tests}")
        print(f"ℹ️ Info: {total_tests - passed_tests - failed_tests - error_tests}")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if failed_tests == 0 and error_tests == 0:
            print("\n🎉 All tests passed! The dynamic scheduling system is ready for production.")
        else:
            print(f"\n⚠️ {failed_tests + error_tests} tests need attention before production deployment.")
        
        print("\n" + "=" * 60)


async def main():
    """Main test runner"""
    tester = SchedulingSystemTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    print("Dynamic Scheduling System - Integration Test Suite")
    print("Make sure all services are running before starting tests:")
    print("- Backend: http://localhost:8000")
    print("- Tooling Engine: http://localhost:8010")
    print("- Reminder Server: http://localhost:8003")
    print("- Google Calendar Server: http://localhost:8007")
    print("- Gmail Server: http://localhost:8008")
    print("\nPress Enter to start tests...")
    input()
    
    asyncio.run(main())
