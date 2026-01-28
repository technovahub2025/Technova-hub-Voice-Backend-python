"""
Inbound Call Service
Integrates with Node.js backend for enhanced inbound call management
"""
import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from utils.logger import setup_logger

logger = setup_logger(__name__)

class InboundService:
    """Service for managing inbound calls and integration with Node.js backend"""
    
    def __init__(self):
        self.node_backend_url = "https://technova-hub-voice-backend-node-hxg7.onrender.com"  # Node.js backend URL
        self.session = None
        
    async def initialize(self):
        """Initialize HTTP session and connections"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"Content-Type": "application/json"}
        )
        logger.info("✓ Inbound Service initialized")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
    
    async def process_inbound_call(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process inbound call through Node.js backend routing
        
        Args:
            call_data: Call information from Twilio
            
        Returns:
            Routing decision and TwiML response
        """
        try:
            if not self.session:
                await self.initialize()
            
            # Send call data to Node.js backend for routing
            async with self.session.post(
                f"{self.node_backend_url}/webhook/incoming",
                json=call_data
            ) as response:
                if response.status == 200:
                    result = await response.text()
                    logger.info(f"Call routed via Node.js: {call_data.get('CallSid')}")
                    return {
                        "success": True,
                        "twiml": result,
                        "routing": "nodejs_backend"
                    }
                else:
                    logger.error(f"Node.js routing failed: {response.status}")
                    return await self._fallback_routing(call_data)
                    
        except Exception as e:
            logger.error(f"Inbound call processing error: {str(e)}")
            return await self._fallback_routing(call_data)
    
    async def _fallback_routing(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback routing if Node.js backend is unavailable
        
        Args:
            call_data: Call information
            
        Returns:
            Basic TwiML response for AI routing
        """
        call_sid = call_data.get("CallSid")
        from_phone = call_data.get("From")
        
        # Generate basic TwiML for direct AI routing
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="en-US">Connecting you to our AI assistant.</Say>
    <Connect>
        <Stream url="wss://{self.node_backend_url.replace('http://', 'ws://')}/media/{call_sid}" track="both_tracks"/>
    </Connect>
</Response>'''
        
        logger.info(f"Fallback routing for call: {call_sid}")
        
        return {
            "success": True,
            "twiml": twiml,
            "routing": "fallback_ai"
        }
    
    async def update_call_status(self, call_sid: str, status: str, metadata: Dict[str, Any] = None):
        """
        Update call status in Node.js backend
        
        Args:
            call_sid: Call session ID
            status: New call status
            metadata: Additional call metadata
        """
        try:
            if not self.session:
                await self.initialize()
            
            status_data = {
                "CallSid": call_sid,
                "CallStatus": status,
                **(metadata or {})
            }
            
            async with self.session.post(
                f"{self.node_backend_url}/webhook/status",
                json=status_data
            ) as response:
                if response.status == 200:
                    logger.info(f"Call status updated: {call_sid} -> {status}")
                else:
                    logger.error(f"Failed to update call status: {response.status}")
                    
        except Exception as e:
            logger.error(f"Update call status error: {str(e)}")
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status from Node.js backend
        
        Returns:
            Queue information and statistics
        """
        try:
            if not self.session:
                await self.initialize()
            
            async with self.session.get(
                f"{self.node_backend_url}/inbound/queues"
            ) as response:
                if response.status == 200:
                    queue_data = await response.json()
                    return queue_data
                else:
                    logger.error(f"Failed to get queue status: {response.status}")
                    return self._get_mock_queue_data()
                    
        except Exception as e:
            logger.error(f"Get queue status error: {str(e)}")
            return self._get_mock_queue_data()
    
    def _get_mock_queue_data(self) -> Dict[str, Any]:
        """Mock queue data for fallback"""
        return {
            "sales": {"length": 2, "avg_wait": 45},
            "tech": {"length": 1, "avg_wait": 30},
            "billing": {"length": 0, "avg_wait": 0},
            "priority": {"length": 1, "avg_wait": 15}
        }
    
    async def get_analytics(self, period: str = "today") -> Dict[str, Any]:
        """
        Get call analytics from Node.js backend
        
        Args:
            period: Time period for analytics
            
        Returns:
            Analytics data
        """
        try:
            if not self.session:
                await self.initialize()
            
            async with self.session.get(
                f"{self.node_backend_url}/inbound/analytics?period={period}"
            ) as response:
                if response.status == 200:
                    analytics = await response.json()
                    return analytics
                else:
                    logger.error(f"Failed to get analytics: {response.status}")
                    return self._get_mock_analytics()
                    
        except Exception as e:
            logger.error(f"Get analytics error: {str(e)}")
            return self._get_mock_analytics()
    
    def _get_mock_analytics(self) -> Dict[str, Any]:
        """Mock analytics data for fallback"""
        return {
            "summary": {
                "totalCalls": 25,
                "inboundCalls": 15,
                "outboundCalls": 10,
                "completedCalls": 20,
                "successRate": 80,
                "avgDuration": 120
            },
            "ivrAnalytics": {
                "totalIVRCalls": 12,
                "ivrUsageRate": 80,
                "routingBreakdown": {"sales": 5, "tech": 4, "billing": 2, "ai": 1}
            },
            "aiMetrics": {
                "aiCalls": 8,
                "aiEngagementRate": 53,
                "avgResponseTime": 800
            }
        }
    
    async def update_ivr_config(self, menu_name: str, config: Dict[str, Any]):
        """
        Update IVR configuration in Node.js backend
        
        Args:
            menu_name: IVR menu name
            config: IVR configuration
        """
        try:
            if not self.session:
                await self.initialize()
            
            async with self.session.post(
                f"{self.node_backend_url}/inbound/ivr/configs",
                json={"menuName": menu_name, "config": config}
            ) as response:
                if response.status == 200:
                    logger.info(f"IVR config updated: {menu_name}")
                    return await response.json()
                else:
                    logger.error(f"Failed to update IVR config: {response.status}")
                    return {"success": False}
                    
        except Exception as e:
            logger.error(f"Update IVR config error: {str(e)}")
            return {"success": False}
    
    async def test_ivr_menu(self, menu_name: str):
        """
        Test IVR menu configuration
        
        Args:
            menu_name: IVR menu name to test
        """
        try:
            if not self.session:
                await self.initialize()
            
            async with self.session.post(
                f"{self.node_backend_url}/inbound/ivr/test/{menu_name}"
            ) as response:
                if response.status == 200:
                    logger.info(f"IVR test initiated: {menu_name}")
                    return await response.json()
                else:
                    logger.error(f"Failed to test IVR: {response.status}")
                    return {"success": False}
                    
        except Exception as e:
            logger.error(f"Test IVR error: {str(e)}")
            return {"success": False}
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of Node.js backend integration
        
        Returns:
            Health status of different components
        """
        health_status = {
            "nodejs_backend": False,
            "api_connection": False
        }
        
        try:
            if not self.session:
                await self.initialize()
            
            # Test Node.js backend health
            async with self.session.get(
                f"{self.node_backend_url}/health",
                timeout=5
            ) as response:
                if response.status == 200:
                    health_status["nodejs_backend"] = True
                    health_status["api_connection"] = True
                    logger.info("✓ Node.js backend health check passed")
                else:
                    logger.warning(f"Node.js backend returned status: {response.status}")
                    health_status["api_connection"] = True
            
        except asyncio.TimeoutError:
            logger.error("Health check timeout - Node.js backend not responding")
        except Exception as e:
            error_msg = str(e).lower()
            if "connection refused" in error_msg:
                logger.error("Node.js backend is not running - Connection refused")
            elif "timeout" in error_msg:
                logger.error("Health check timeout - Node.js backend not responding")
            else:
                logger.error(f"Health check error: {str(e)}")
        
        return health_status

# Global instance
inbound_service = InboundService()

# Export functions for easy access
async def process_inbound_call(call_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process inbound call through inbound service"""
    return await inbound_service.process_inbound_call(call_data)

async def get_queue_status() -> Dict[str, Any]:
    """Get current queue status"""
    return await inbound_service.get_queue_status()

async def get_analytics(period: str = "today") -> Dict[str, Any]:
    """Get call analytics"""
    return await inbound_service.get_analytics(period)

async def health_check() -> Dict[str, bool]:
    """Check service health"""
    return await inbound_service.health_check()
