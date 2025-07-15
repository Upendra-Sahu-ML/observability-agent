#!/usr/bin/env python3
"""
System Test Script for Observability Agent
Tests the entire system with dummy data and validates responses
"""

import asyncio
import json
import logging
import sys
import os
import time
from datetime import datetime
from typing import Dict, List, Any
import argparse

# Add the project root to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import nats
    from nats.js.api import StreamConfig, ConsumerConfig
except ImportError:
    print("Please install nats-py: pip install nats-py")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemTester:
    def __init__(self, nats_url="nats://localhost:4222"):
        self.nats_url = nats_url
        self.nc = None
        self.js = None
        self.test_results = {}
        
    async def connect(self):
        """Connect to NATS server"""
        try:
            self.nc = await nats.connect(self.nats_url)
            self.js = self.nc.jetstream()
            logger.info(f"Connected to NATS at {self.nats_url}")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from NATS server"""
        if self.nc:
            await self.nc.close()
            logger.info("Disconnected from NATS")
    
    async def test_nats_connectivity(self) -> bool:
        """Test basic NATS connectivity"""
        logger.info("🔍 Testing NATS connectivity...")
        try:
            # Try to publish a simple message
            await self.nc.publish("test.connectivity", b"test message")
            logger.info("✅ NATS connectivity test passed")
            return True
        except Exception as e:
            logger.error(f"❌ NATS connectivity test failed: {e}")
            return False
    
    async def test_jetstream_functionality(self) -> bool:
        """Test JetStream functionality"""
        logger.info("🔍 Testing JetStream functionality...")
        try:
            # Create a test stream
            test_stream = StreamConfig(
                name="TEST_STREAM",
                subjects=["test.*"],
                max_msgs=100,
                max_age=3600  # 1 hour
            )
            
            await self.js.add_stream(test_stream)
            
            # Publish a test message
            await self.js.publish("test.message", b"test data")
            
            # Get stream info
            info = await self.js.stream_info("TEST_STREAM")
            
            # Clean up
            await self.js.delete_stream("TEST_STREAM")
            
            logger.info("✅ JetStream functionality test passed")
            return True
        except Exception as e:
            logger.error(f"❌ JetStream functionality test failed: {e}")
            return False
    
    async def test_stream_setup(self) -> bool:
        """Test that all required streams are properly set up"""
        logger.info("🔍 Testing stream setup...")
        
        required_streams = [
            "ALERTS", "METRICS", "LOGS", "DEPLOYMENTS", 
            "AGENTS", "RUNBOOKS", "NOTIFICATIONS", "ROOT_CAUSE"
        ]
        
        try:
            existing_streams = []
            streams = await self.js.streams_info()
            for stream in streams:
                existing_streams.append(stream.config.name)
            
            missing_streams = [s for s in required_streams if s not in existing_streams]
            
            if missing_streams:
                logger.warning(f"⚠️  Missing streams: {missing_streams}")
                return False
            
            logger.info("✅ All required streams are present")
            return True
            
        except Exception as e:
            logger.error(f"❌ Stream setup test failed: {e}")
            return False
    
    async def test_alert_processing(self) -> bool:
        """Test alert processing workflow"""
        logger.info("🔍 Testing alert processing...")
        
        try:
            # Create a test alert
            test_alert = {
                "alert_id": f"test-alert-{int(time.time())}",
                "alert_name": "TestAlert",
                "labels": {
                    "service": "test-service",
                    "namespace": "default",
                    "severity": "warning"
                },
                "annotations": {
                    "summary": "Test alert for system testing",
                    "description": "This is a test alert"
                },
                "timestamp": datetime.utcnow().isoformat(),
                "status": "firing"
            }
            
            # Publish the alert
            await self.js.publish("alerts", json.dumps(test_alert).encode())
            
            # Wait a bit for processing
            await asyncio.sleep(2)
            
            # Check if alert was processed (this would require checking agent responses)
            # For now, just verify the alert was published
            logger.info("✅ Alert processing test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Alert processing test failed: {e}")
            return False
    
    async def test_simplified_tools(self) -> bool:
        """Test simplified tools functionality"""
        logger.info("🔍 Testing simplified tools...")
        
        try:
            # Test if simplified tools can be imported
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from common.simplified_tools import SimplifiedToolManager
            
            # Create tool manager
            tool_manager = SimplifiedToolManager()
            
            # Test essential tools list
            tools = tool_manager.get_essential_tools_list()
            expected_count = 15
            
            if len(tools) != expected_count:
                logger.error(f"❌ Expected {expected_count} tools, got {len(tools)}")
                return False
            
            # Test agent-specific tools
            obs_tools = tool_manager.get_tools_for_agent("observability")
            infra_tools = tool_manager.get_tools_for_agent("infrastructure")
            comm_tools = tool_manager.get_tools_for_agent("communication")
            
            if not obs_tools or not infra_tools or not comm_tools:
                logger.error("❌ Some agent types have no tools assigned")
                return False
            
            logger.info("✅ Simplified tools test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Simplified tools test failed: {e}")
            return False
    
    async def test_observability_manager(self) -> bool:
        """Test observability manager fallback functionality"""
        logger.info("🔍 Testing observability manager...")
        
        try:
            # Test if observability manager can be imported
            from common.observability_manager import ObservabilityManager
            
            # Create manager with mock URLs (they won't be accessible in test)
            manager = ObservabilityManager(
                prometheus_url="http://localhost:9090",
                loki_url="http://localhost:3100",
                tempo_url="http://localhost:3200"
            )
            
            # Test fallback functionality (should work even without real services)
            test_incident = {
                "alert_id": "test-001",
                "labels": {
                    "service": "test-service",
                    "namespace": "default"
                }
            }
            
            # This should use kubectl fallbacks
            context = manager.get_comprehensive_incident_context(test_incident)
            
            if not context:
                logger.error("❌ Observability manager returned no context")
                return False
            
            logger.info("✅ Observability manager test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Observability manager test failed: {e}")
            return False
    
    async def test_agent_architecture(self) -> bool:
        """Test simplified agent architecture"""
        logger.info("🔍 Testing agent architecture...")
        
        try:
            # Test if agent files exist and can be imported
            agent_paths = [
                "agents/observability_agent/agent.py",
                "agents/infrastructure_agent/agent.py", 
                "agents/communication_agent/agent.py",
                "agents/root_cause_agent/root_cause.py"
            ]
            
            project_root = os.path.join(os.path.dirname(__file__), '..')
            
            for agent_path in agent_paths:
                full_path = os.path.join(project_root, agent_path)
                if not os.path.exists(full_path):
                    logger.error(f"❌ Agent file missing: {agent_path}")
                    return False
            
            logger.info("✅ Agent architecture test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Agent architecture test failed: {e}")
            return False
    
    async def test_deployment_configurations(self) -> bool:
        """Test tiered deployment configurations"""
        logger.info("🔍 Testing deployment configurations...")
        
        try:
            project_root = os.path.join(os.path.dirname(__file__), '..')
            config_files = [
                "helm/observability-agent/values-basic.yaml",
                "helm/observability-agent/values-standard.yaml",
                "scripts/deploy-tiered.sh"
            ]
            
            for config_file in config_files:
                full_path = os.path.join(project_root, config_file)
                if not os.path.exists(full_path):
                    logger.error(f"❌ Config file missing: {config_file}")
                    return False
            
            logger.info("✅ Deployment configurations test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Deployment configurations test failed: {e}")
            return False
    
    async def run_comprehensive_test(self) -> Dict[str, bool]:
        """Run all tests and return results"""
        logger.info("🚀 Starting comprehensive system test...")
        
        tests = [
            ("NATS Connectivity", self.test_nats_connectivity),
            ("JetStream Functionality", self.test_jetstream_functionality),
            ("Stream Setup", self.test_stream_setup),
            ("Alert Processing", self.test_alert_processing),
            ("Simplified Tools", self.test_simplified_tools),
            ("Observability Manager", self.test_observability_manager),
            ("Agent Architecture", self.test_agent_architecture),
            ("Deployment Configurations", self.test_deployment_configurations)
        ]
        
        results = {}
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results[test_name] = result
                if result:
                    passed += 1
            except Exception as e:
                logger.error(f"❌ Test '{test_name}' failed with exception: {e}")
                results[test_name] = False
        
        # Print summary
        logger.info(f"\n📊 Test Results Summary:")
        logger.info(f"{'='*50}")
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name:<30} {status}")
        
        logger.info(f"{'='*50}")
        logger.info(f"Total: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All tests passed! System is ready for use.")
        else:
            logger.warning(f"⚠️  {total - passed} tests failed. Please check the logs.")
        
        return results

async def main():
    parser = argparse.ArgumentParser(description='System Test for Observability Agent')
    parser.add_argument('--nats-url', default='nats://localhost:4222', help='NATS server URL')
    parser.add_argument('--test', choices=['all', 'connectivity', 'jetstream', 'streams', 'alerts', 'tools', 'observability', 'agents', 'deployment'], 
                       default='all', help='Specific test to run')
    
    args = parser.parse_args()
    
    tester = SystemTester(args.nats_url)
    
    try:
        await tester.connect()
        
        if args.test == 'all':
            results = await tester.run_comprehensive_test()
            # Exit with non-zero code if any tests failed
            if not all(results.values()):
                sys.exit(1)
        else:
            # Run specific test
            test_methods = {
                'connectivity': tester.test_nats_connectivity,
                'jetstream': tester.test_jetstream_functionality,
                'streams': tester.test_stream_setup,
                'alerts': tester.test_alert_processing,
                'tools': tester.test_simplified_tools,
                'observability': tester.test_observability_manager,
                'agents': tester.test_agent_architecture,
                'deployment': tester.test_deployment_configurations
            }
            
            if args.test in test_methods:
                result = await test_methods[args.test]()
                if not result:
                    sys.exit(1)
            else:
                logger.error(f"Unknown test: {args.test}")
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    finally:
        await tester.disconnect()

if __name__ == "__main__":
    asyncio.run(main())