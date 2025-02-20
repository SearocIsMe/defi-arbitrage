import os
import json
from typing import Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import prometheus_client

from logger_config import get_logger

# Prometheus Metrics
ARBITRAGE_OPPORTUNITIES = prometheus_client.Counter(
    'arbitrage_opportunities_total', 
    'Total number of arbitrage opportunities detected'
)
ARBITRAGE_PROFITS = prometheus_client.Gauge(
    'arbitrage_profit_percentage', 
    'Profit percentage of arbitrage opportunities'
)
TRADING_PAIRS = prometheus_client.Gauge(
    'trading_pairs_tracked', 
    'Number of trading pairs being monitored'
)

class ArbitrageAPIService:
    """
    API Service for Arbitrage Bot
    Provides real-time monitoring, metrics, and WebSocket updates
    """
    
    def __init__(self):
        """
        Initialize API Service
        """
        self.logger = get_logger('arbitrage_api')
        self.app = FastAPI(
            title="DeFi Arbitrage Bot API",
            description="Real-time arbitrage opportunity monitoring",
            version="0.1.0"
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # WebSocket connections
        self.active_connections: List[WebSocket] = []
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """
        Configure API routes
        """
        @self.app.get("/health")
        async def health_check():
            """
            Basic health check endpoint
            """
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/metrics")
        async def get_metrics():
            """
            Expose Prometheus metrics
            """
            return prometheus_client.generate_latest()
        
        @self.app.websocket("/ws/opportunities")
        async def websocket_opportunities(websocket: WebSocket):
            """
            WebSocket endpoint for real-time arbitrage opportunities
            """
            await websocket.accept()
            self.active_connections.append(websocket)
            
            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
    
    async def broadcast_opportunity(self, opportunity: Dict[str, Any]):
        """
        Broadcast arbitrage opportunity to all connected WebSocket clients
        
        Args:
            opportunity (Dict[str, Any]): Arbitrage opportunity details
        """
        for connection in self.active_connections:
            try:
                await connection.send_json(opportunity)
            except Exception as e:
                self.logger.error(f"WebSocket broadcast error: {e}")

def store_arbitrage_opportunity(opportunity: Dict[str, Any]):
    """
    Store and process arbitrage opportunity
    
    Args:
        opportunity (Dict[str, Any]): Arbitrage opportunity details
    """
    try:
        # Update Prometheus metrics
        ARBITRAGE_OPPORTUNITIES.inc()
        ARBITRAGE_PROFITS.set(opportunity.get('profit_percentage', 0))
        
        # Log opportunity
        logger = get_logger('arbitrage_storage')
        logger.info(f"Arbitrage Opportunity: {opportunity}")
        
        # Optional: Store in database or file
        opportunities_dir = os.path.join(os.getcwd(), 'opportunities')
        os.makedirs(opportunities_dir, exist_ok=True)
        
        filename = f"opportunity_{datetime.now().isoformat().replace(':', '-')}.json"
        filepath = os.path.join(opportunities_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(opportunity, f, indent=2)
        
    except Exception as e:
        logger.error(f"Error storing arbitrage opportunity: {e}")

def store_top_trading_pairs(pairs: Dict[str, Any]):
    """
    Store top trading pairs for monitoring
    
    Args:
        pairs (Dict[str, Any]): Top trading pairs data
    """
    try:
        # Update Prometheus metrics
        TRADING_PAIRS.set(len(pairs))
        
        # Log pairs
        logger = get_logger('trading_pairs')
        logger.info(f"Top Trading Pairs: {pairs}")
        
        # Store pairs
        pairs_dir = os.path.join(os.getcwd(), 'trading_pairs')
        os.makedirs(pairs_dir, exist_ok=True)
        
        filename = f"pairs_{datetime.now().isoformat().replace(':', '-')}.json"
        filepath = os.path.join(pairs_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(pairs, f, indent=2)
        
    except Exception as e:
        logger.error(f"Error storing trading pairs: {e}")

# Utility function to run API service
def run_api_service(host: str = '0.0.0.0', port: int = 8000):
    """
    Run the Arbitrage Bot API Service
    
    Args:
        host (str): Host to bind the service
        port (int): Port to run the service
    """
    import uvicorn
    
    uvicorn.run(
        "api_service:app", 
        host=host, 
        port=port, 
        reload=True
    )

# Expose FastAPI app for ASGI servers
app = ArbitrageAPIService().app
