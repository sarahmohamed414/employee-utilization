"""
MCP Server for Microsoft Lists Dynamic Data Fetching

This MCP server provides real-time data synchronization between Microsoft Lists
and your Employee Utilization Dashboard without requiring Graph API access.
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import hashlib
from dataclasses import dataclass
from microsoft_lists_client import MicrosoftListsClient
from microsoft_lists_config import LISTS_CONFIG, REALTIME_CONFIG, LIST_COLUMN_MAPPING

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DataChangeEvent:
    """Represents a change in the Microsoft Lists data."""
    timestamp: datetime
    change_type: str  # 'added', 'modified', 'deleted', 'updated'
    record_id: str
    old_data: Optional[Dict] = None
    new_data: Optional[Dict] = None

class MCPListsServer:
    """MCP Server for Microsoft Lists dynamic data fetching."""
    
    def __init__(self):
        """Initialize the MCP server."""
        self.config = LISTS_CONFIG
        self.realtime_config = REALTIME_CONFIG
        self.column_mapping = LIST_COLUMN_MAPPING
        
        # Initialize Microsoft Lists client
        self.lists_client = MicrosoftListsClient(self.config)
        
        # Data tracking
        self.current_data = None
        self.data_hash = None
        self.last_update_time = None
        self.change_events = []
        
        # Threading for background updates
        self.update_thread = None
        self.stop_thread = False
        self.update_lock = threading.Lock()
        
        # Subscribers (dashboard components that need updates)
        self.subscribers = []
        
        logger.info("MCP Lists Server initialized")
    
    def start_background_updates(self):
        """Start background thread for automatic data updates."""
        if self.update_thread and self.update_thread.is_alive():
            logger.warning("Background updates already running")
            return
        
        self.stop_thread = False
        self.update_thread = threading.Thread(target=self._background_update_loop, daemon=True)
        self.update_thread.start()
        logger.info("Background data updates started")
    
    def stop_background_updates(self):
        """Stop background thread for automatic data updates."""
        self.stop_thread = True
        if self.update_thread:
            self.update_thread.join(timeout=5)
        logger.info("Background data updates stopped")
    
    def _background_update_loop(self):
        """Background loop for checking data updates."""
        while not self.stop_thread:
            try:
                self._check_for_updates()
                
                # Wait for next update cycle
                interval = self.realtime_config.get("refresh_interval", 300)  # 5 minutes default
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in background update loop: {str(e)}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _check_for_updates(self):
        """Check for updates in Microsoft Lists data."""
        try:
            with self.update_lock:
                # Fetch latest data
                new_data = self.lists_client.fetch_latest_data(force_refresh=True)
                
                if new_data is None:
                    logger.warning("Failed to fetch new data")
                    return
                
                # Calculate hash to detect changes
                new_hash = self._calculate_data_hash(new_data)
                
                # Check if data has changed
                if self.data_hash is None or new_hash != self.data_hash:
                    logger.info("Data change detected, processing updates...")
                    
                    # Detect specific changes
                    changes = self._detect_changes(self.current_data, new_data)
                    
                    # Update stored data
                    self.current_data = new_data
                    self.data_hash = new_hash
                    self.last_update_time = datetime.now()
                    
                    # Process and notify subscribers
                    self._process_changes(changes)
                    
                    logger.info(f"Data updated successfully. {len(changes)} changes detected.")
                else:
                    logger.debug("No data changes detected")
                    
        except Exception as e:
            logger.error(f"Error checking for updates: {str(e)}")
    
    def _calculate_data_hash(self, data: pd.DataFrame) -> str:
        """Calculate hash of data to detect changes."""
        try:
            # Convert DataFrame to JSON string and hash it
            data_str = data.to_json(orient='records', date_format='iso')
            return hashlib.md5(data_str.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating data hash: {str(e)}")
            return ""
    
    def _detect_changes(self, old_data: Optional[pd.DataFrame], new_data: pd.DataFrame) -> List[DataChangeEvent]:
        """Detect changes between old and new data."""
        changes = []
        
        if old_data is None:
            # First time loading data - all records are new
            for _, row in new_data.iterrows():
                event = DataChangeEvent(
                    timestamp=datetime.now(),
                    change_type='added',
                    record_id=str(row.get('_id', len(changes))),
                    new_data=row.to_dict()
                )
                changes.append(event)
            return changes
        
        # Convert to dictionaries for easier comparison
        old_dict = {str(row.get('_id', i)): row.to_dict() for i, row in old_data.iterrows()}
        new_dict = {str(row.get('_id', i)): row.to_dict() for i, row in new_data.iterrows()}
        
        # Find added records
        for record_id in new_dict:
            if record_id not in old_dict:
                event = DataChangeEvent(
                    timestamp=datetime.now(),
                    change_type='added',
                    record_id=record_id,
                    new_data=new_dict[record_id]
                )
                changes.append(event)
        
        # Find modified records
        for record_id in old_dict:
            if record_id in new_dict:
                if old_dict[record_id] != new_dict[record_id]:
                    event = DataChangeEvent(
                        timestamp=datetime.now(),
                        change_type='modified',
                        record_id=record_id,
                        old_data=old_dict[record_id],
                        new_data=new_dict[record_id]
                    )
                    changes.append(event)
        
        # Find deleted records
        for record_id in old_dict:
            if record_id not in new_dict:
                event = DataChangeEvent(
                    timestamp=datetime.now(),
                    change_type='deleted',
                    record_id=record_id,
                    old_data=old_dict[record_id]
                )
                changes.append(event)
        
        return changes
    
    def _process_changes(self, changes: List[DataChangeEvent]):
        """Process detected changes and notify subscribers."""
        try:
            # Store change events
            self.change_events.extend(changes)
            
            # Keep only recent events (last 100)
            if len(self.change_events) > 100:
                self.change_events = self.change_events[-100:]
            
            # Notify subscribers
            self._notify_subscribers(changes)
            
            # Log changes
            for change in changes:
                logger.info(f"Change detected: {change.change_type} - Record {change.record_id}")
                
        except Exception as e:
            logger.error(f"Error processing changes: {str(e)}")
    
    def _notify_subscribers(self, changes: List[DataChangeEvent]):
        """Notify all subscribers about data changes."""
        for subscriber in self.subscribers:
            try:
                if hasattr(subscriber, 'on_data_change'):
                    subscriber.on_data_change(changes)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {str(e)}")
    
    def subscribe(self, subscriber):
        """Subscribe to data change notifications."""
        if subscriber not in self.subscribers:
            self.subscribers.append(subscriber)
            logger.info(f"New subscriber added. Total subscribers: {len(self.subscribers)}")
    
    def unsubscribe(self, subscriber):
        """Unsubscribe from data change notifications."""
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)
            logger.info(f"Subscriber removed. Total subscribers: {len(self.subscribers)}")
    
    def get_current_data(self, force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """Get current data from Microsoft Lists."""
        try:
            if force_refresh or self.current_data is None:
                with self.update_lock:
                    self.current_data = self.lists_client.fetch_latest_data(force_refresh=True)
                    if self.current_data is not None:
                        self.data_hash = self._calculate_data_hash(self.current_data)
                        self.last_update_time = datetime.now()
            
            return self.current_data
            
        except Exception as e:
            logger.error(f"Error getting current data: {str(e)}")
            return None
    
    def get_change_events(self, since: Optional[datetime] = None) -> List[DataChangeEvent]:
        """Get change events since a specific time."""
        if since is None:
            return self.change_events.copy()
        
        return [event for event in self.change_events if event.timestamp >= since]
    
    def get_status(self) -> Dict[str, Any]:
        """Get server status information."""
        return {
            "is_running": self.update_thread and self.update_thread.is_alive(),
            "last_update": self.last_update_time.isoformat() if self.last_update_time else None,
            "data_records": len(self.current_data) if self.current_data is not None else 0,
            "change_events_count": len(self.change_events),
            "subscribers_count": len(self.subscribers),
            "config": {
                "data_source": self.config.get("data_source"),
                "refresh_interval": self.realtime_config.get("refresh_interval"),
                "auto_refresh": self.realtime_config.get("enable_auto_refresh")
            }
        }
    
    def force_update(self):
        """Force an immediate data update."""
        logger.info("Forcing data update...")
        self._check_for_updates()
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Microsoft Lists."""
        return self.lists_client.test_connection()


# Global MCP server instance
mcp_server = None

def get_mcp_server() -> MCPListsServer:
    """Get or create the global MCP server instance."""
    global mcp_server
    if mcp_server is None:
        mcp_server = MCPListsServer()
    return mcp_server

def start_dynamic_updates():
    """Start dynamic data updates."""
    server = get_mcp_server()
    server.start_background_updates()
    return server

def stop_dynamic_updates():
    """Stop dynamic data updates."""
    global mcp_server
    if mcp_server:
        mcp_server.stop_background_updates()

def get_latest_data(force_refresh: bool = False) -> Optional[pd.DataFrame]:
    """Get the latest data from Microsoft Lists."""
    server = get_mcp_server()
    return server.get_current_data(force_refresh)

def get_recent_changes(hours: int = 1) -> List[DataChangeEvent]:
    """Get recent changes in the specified time window."""
    server = get_mcp_server()
    since = datetime.now() - timedelta(hours=hours)
    return server.get_change_events(since)

if __name__ == "__main__":
    print("MCP Server for Microsoft Lists Dynamic Data Fetching")
    print("Starting server...")
    
    # Start the server
    server = start_dynamic_updates()
    
    try:
        # Keep the server running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        stop_dynamic_updates()
        print("Server stopped.")
