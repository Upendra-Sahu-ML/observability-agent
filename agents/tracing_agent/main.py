"""
Main entry point for the tracing agent
"""
import os
import json
import logging
import asyncio
import threading
from datetime import datetime, timedelta

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from agent import TracingAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Tracing Agent", description="API for analyzing distributed traces")

# Initialize the agent
agent = TracingAgent(
    tempo_url=os.environ.get("TEMPO_URL"),
    services_to_monitor=os.environ.get("SERVICES_TO_MONITOR", "").split(",")
)

# Models for API requests and responses
class TimeRange(BaseModel):
    start: str
    end: str
    
class TraceSearchRequest(BaseModel):
    service: Optional[str] = None
    operation: Optional[str] = None
    min_duration: Optional[str] = None
    limit: Optional[int] = 50
    time_range: TimeRange
    
class TraceAnalysisRequest(BaseModel):
    trace_id: str
    
class ServiceBaselineRequest(BaseModel):
    service: str
    duration_hours: Optional[int] = 24
    
class RelatedTracesRequest(BaseModel):
    alert_time: str
    service: Optional[str] = None
    error_type: Optional[str] = None
    window_minutes: Optional[int] = 15

# API endpoints
@app.get("/")
async def root():
    return {"status": "healthy", "service": "tracing-agent"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/traces/search")
async def search_traces(request: TraceSearchRequest):
    try:
        result = await agent.find_traces_for_timerange(
            start=request.time_range.start,
            end=request.time_range.end,
            service=request.service,
            operation=request.operation,
            min_duration=request.min_duration,
            limit=request.limit
        )
        return result
    except Exception as e:
        logger.error(f"Error searching traces: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/traces/analyze")
async def analyze_trace(request: TraceAnalysisRequest):
    try:
        result = await agent.analyze_trace(request.trace_id)
        return result
    except Exception as e:
        logger.error(f"Error analyzing trace: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/services/baseline")
async def build_service_baseline(request: ServiceBaselineRequest):
    try:
        result = await agent.build_service_baseline(
            service=request.service,
            duration_hours=request.duration_hours
        )
        return result
    except Exception as e:
        logger.error(f"Error building service baseline: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/traces/related-to-alert")
async def find_related_traces(request: RelatedTracesRequest):
    try:
        result = await agent.find_related_traces(
            alert_time=request.alert_time,
            service=request.service,
            error_type=request.error_type,
            window_minutes=request.window_minutes
        )
        return result
    except Exception as e:
        logger.error(f"Error finding related traces: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/services/monitored")
async def get_monitored_services():
    return {
        "services": agent.services_to_monitor,
        "count": len(agent.services_to_monitor)
    }

# Start background monitoring task
@app.on_event("startup")
async def start_monitoring():
    # Start service monitoring
    asyncio.create_task(agent.monitor_services())
    
    # Start Redis listener in a separate thread
    def start_redis_listener():
        logger.info("Starting Redis listener for tracing agent")
        agent.listen()
    
    redis_thread = threading.Thread(target=start_redis_listener)
    redis_thread.daemon = True
    redis_thread.start()
    logger.info("Redis listener thread started")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8003))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)