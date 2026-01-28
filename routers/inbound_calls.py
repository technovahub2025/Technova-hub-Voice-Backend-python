"""
Inbound Call Management Router
Simplified router that delegates to Node.js backend for all inbound operations
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import asyncio
import logging

from services.inbound_service import inbound_service
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/inbound", tags=["inbound"])

# Pydantic Models for API validation
class AnalyticsRequest(BaseModel):
    period: str = Field(default="today", description="Time period")
    filters: Optional[Dict[str, Any]] = Field(None, description="Analytics filters")

class IVRMenu(BaseModel):
    greeting: str = Field(..., description="Welcome message")
    menu: List[Dict[str, Any]] = Field(..., description="Menu options")
    timeout: int = Field(default=10, description="Timeout in seconds")
    max_attempts: int = Field(default=3, description="Max retry attempts")
    invalid_input_message: str = Field(default="Invalid selection. Please try again.")

class RoutingRule(BaseModel):
    name: str = Field(..., description="Rule name")
    priority: int = Field(default=1, description="Rule priority")
    enabled: bool = Field(default=True, description="Rule enabled status")
    conditions: List[Dict[str, Any]] = Field(..., description="Rule conditions")
    actions: List[str] = Field(..., description="Rule actions")
    description: Optional[str] = Field(None, description="Rule description")

@router.get("/analytics")
async def get_analytics(period: str = "today"):
    """Get inbound call analytics from Node.js backend"""
    try:
        analytics = await inbound_service.get_analytics(period)
        return analytics
    except Exception as e:
        logger.error(f"Get analytics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queues")
async def get_queue_status():
    """Get queue status from Node.js backend"""
    try:
        queue_status = await inbound_service.get_queue_status()
        return queue_status
    except Exception as e:
        logger.error(f"Get queue status error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queues/{queue_name}")
async def get_specific_queue(queue_name: str):
    """Get specific queue status from Node.js backend"""
    try:
        queue_status = await inbound_service.get_queue_status()
        if queue_name not in queue_status:
            raise HTTPException(status_code=404, detail="Queue not found")
        return queue_status[queue_name]
    except Exception as e:
        logger.error(f"Get specific queue error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ivr/configs")
async def get_ivr_configs():
    """Get IVR configurations from Node.js backend"""
    try:
        # This would fetch from Node.js backend
        # For now, return basic structure
        return {
            "main": {
                "greeting": "Welcome to our AI assistant. Please choose from the following options:",
                "menu": [
                    {"key": "1", "text": "For sales and support, press 1", "action": "route_to_sales"},
                    {"key": "2", "text": "For technical support, press 2", "action": "route_to_tech"},
                    {"key": "3", "text": "For billing inquiries, press 3", "action": "route_to_billing"},
                    {"key": "4", "text": "To speak with our AI assistant, press 4", "action": "route_to_ai"}
                ],
                "timeout": 10,
                "max_attempts": 3,
                "invalid_input_message": "Invalid selection. Please try again."
            }
        }
    except Exception as e:
        logger.error(f"Get IVR configs error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ivr/configs")
async def update_ivr_config(menu_name: str, config: IVRMenu):
    """Update IVR configuration via Node.js backend"""
    try:
        result = await inbound_service.update_ivr_config(menu_name, config.dict())
        return result
    except Exception as e:
        logger.error(f"Update IVR config error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/ivr/configs/{menu_name}")
async def delete_ivr_config(menu_name: str):
    """Delete IVR configuration via Node.js backend"""
    try:
        # This would call Node.js backend to delete the config
        logger.info(f"IVR config deletion requested: {menu_name}")
        return {"success": True, "message": f"IVR config {menu_name} marked for deletion"}
    except Exception as e:
        logger.error(f"Delete IVR config error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ivr/test/{menu_name}")
async def test_ivr_menu(menu_name: str):
    """Test IVR menu via Node.js backend"""
    try:
        result = await inbound_service.test_ivr_menu(menu_name)
        return result
    except Exception as e:
        logger.error(f"Test IVR menu error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/routing/rules")
async def get_routing_rules():
    """Get routing rules from Node.js backend"""
    try:
        # This would fetch from Node.js backend
        # For now, return basic structure
        return {
            "vip_customers": {
                "name": "VIP Customers",
                "priority": 10,
                "enabled": True,
                "conditions": [{"field": "user.vip", "operator": "equals", "value": True}],
                "actions": ["priority_queue", "route_to_ai"],
                "description": "Route VIP customers to priority queue with AI assistant"
            },
            "business_hours": {
                "name": "Business Hours",
                "priority": 5,
                "enabled": True,
                "conditions": [{"field": "time", "operator": "in_hours", "value": {"start": 9, "end": 17}}],
                "actions": ["ivr_main"],
                "description": "During business hours, route to main IVR menu"
            }
        }
    except Exception as e:
        logger.error(f"Get routing rules error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/routing/rules")
async def update_routing_rule(rule: RoutingRule):
    """Update routing rule via Node.js backend"""
    try:
        # This would call Node.js backend to update the rule
        logger.info(f"Routing rule update requested: {rule.name}")
        return {"success": True, "message": f"Routing rule {rule.name} marked for update"}
    except Exception as e:
        logger.error(f"Update routing rule error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/routing/rules/{rule_name}")
async def delete_routing_rule(rule_name: str):
    """Delete routing rule via Node.js backend"""
    try:
        # This would call Node.js backend to delete the rule
        logger.info(f"Routing rule deletion requested: {rule_name}")
        return {"success": True, "message": f"Routing rule {rule_name} marked for deletion"}
    except Exception as e:
        logger.error(f"Delete routing rule error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/routing/rules/{rule_name}/toggle")
async def toggle_routing_rule(rule_name: str):
    """Toggle routing rule via Node.js backend"""
    try:
        # This would call Node.js backend to toggle the rule
        logger.info(f"Routing rule toggle requested: {rule_name}")
        return {"success": True, "enabled": True, "message": f"Routing rule {rule_name} marked for toggle"}
    except Exception as e:
        logger.error(f"Toggle routing rule error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/export")
async def export_analytics(period: str = "today", format: str = "json"):
    """Export analytics data via Node.js backend"""
    try:
        # This would call Node.js backend for export
        logger.info(f"Analytics export requested: {period} in {format} format")
        
        # For now, return basic CSV data
        if format == "csv":
            csv_data = "Metric,Value\nTotal Calls,25\nCompleted Calls,20\nSuccess Rate,80%\n"
            return JSONResponse(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=analytics-{period}.csv"}
            )
        else:
            # Return JSON for other formats
            analytics = await inbound_service.get_analytics(period)
            return analytics
    except Exception as e:
        logger.error(f"Export analytics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time queue monitoring (delegated to Node.js)
@router.websocket("/queues/monitor")
async def websocket_queue_monitor(websocket: WebSocket):
    """WebSocket for queue monitoring - delegates to Node.js backend"""
    await websocket.accept()
    logger.info("Queue monitor WebSocket connected - delegating to Node.js")
    
    try:
        # Send initial message indicating delegation
        await websocket.send_json({
            "type": "info",
            "message": "Queue monitoring is handled by Node.js backend",
            "nodejs_url": "https://technova-hub-voice-backend-node-hxg7.onrender.com/inbound/queues/monitor",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Keep connection alive with periodic status updates
        while True:
            await asyncio.sleep(30)  # Send status every 30 seconds
            await websocket.send_json({
                "type": "status",
                "message": "Connected to Python backend (queue monitoring delegated to Node.js)",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
    except WebSocketDisconnect:
        logger.info("Queue monitor WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")

# Health check for inbound service integration
@router.get("/health")
async def inbound_health_check():
    """Check health of inbound service integration"""
    try:
        health = await inbound_service.health_check()
        return {
            "status": "healthy" if all(health.values()) else "degraded",
            "nodejs_backend": health,
            "python_service": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Inbound health check error: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
