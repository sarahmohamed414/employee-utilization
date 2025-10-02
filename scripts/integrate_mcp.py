#!/usr/bin/env python3
"""
MCP Integration Script for Employee Utilization Dashboard

This script integrates the MCP (Model Context Protocol) server for dynamic
data fetching from Microsoft Lists into your existing dashboard.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time
import logging

# Import MCP components
try:
    from mcp_server import get_mcp_server, get_latest_data, start_dynamic_updates, stop_dynamic_updates
    from microsoft_lists_client import MicrosoftListsClient
    from microsoft_lists_config import LISTS_CONFIG, REALTIME_CONFIG
    MCP_AVAILABLE = True
except ImportError as e:
    st.error(f"MCP components not available: {e}")
    MCP_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def show_mcp_status():
    """Show MCP server status in the sidebar."""
    if not MCP_AVAILABLE:
        st.sidebar.error("❌ MCP not available")
        return False
    
    st.sidebar.markdown("### 🔄 Dynamic Data Status")
    
    try:
        server = get_mcp_server()
        status = server.get_status()
        
        # Connection status
        if status["is_running"]:
            st.sidebar.success("✅ MCP Server Running")
        else:
            st.sidebar.warning("⚠️ MCP Server Stopped")
        
        # Last update
        if status["last_update"]:
            last_update = datetime.fromisoformat(status["last_update"])
            st.sidebar.info(f"🕐 Last Update: {last_update.strftime('%H:%M:%S')}")
        else:
            st.sidebar.info("🕐 No updates yet")
        
        # Data count
        st.sidebar.metric("📊 Records", status["data_records"])
        st.sidebar.metric("🔄 Changes", status["change_events_count"])
        
        # Configuration
        with st.sidebar.expander("⚙️ Configuration"):
            st.write(f"**Data Source:** {status['config']['data_source']}")
            st.write(f"**Refresh Interval:** {status['config']['refresh_interval']}s")
            st.write(f"**Auto Refresh:** {status['config']['auto_refresh']}")
        
        return True
        
    except Exception as e:
        st.sidebar.error(f"❌ MCP Error: {str(e)}")
        return False

def show_mcp_controls():
    """Show MCP control buttons."""
    if not MCP_AVAILABLE:
        return
    
    st.sidebar.markdown("### 🎛️ MCP Controls")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("🔄 Force Update", help="Manually trigger data refresh"):
            try:
                server = get_mcp_server()
                server.force_update()
                st.sidebar.success("Update triggered!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Update failed: {str(e)}")
    
    with col2:
        if st.button("▶️ Start Updates", help="Start automatic updates"):
            try:
                start_dynamic_updates()
                st.sidebar.success("Updates started!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Start failed: {str(e)}")
    
    if st.sidebar.button("⏹️ Stop Updates", help="Stop automatic updates"):
        try:
            stop_dynamic_updates()
            st.sidebar.success("Updates stopped!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Stop failed: {str(e)}")

def get_dynamic_data():
    """Get data from MCP server if available, otherwise return None."""
    if not MCP_AVAILABLE:
        return None
    
    try:
        data = get_latest_data(force_refresh=False)
        if data is not None and len(data) > 0:
            st.success(f"✅ Loaded {len(data)} records from Microsoft Lists")
            return data
        else:
            st.warning("⚠️ No data available from Microsoft Lists")
            return None
    except Exception as e:
        st.error(f"❌ Error loading MCP data: {str(e)}")
        return None

def show_mcp_setup_instructions():
    """Show setup instructions for MCP integration."""
    st.markdown("### 🔧 MCP Setup Instructions")
    
    st.markdown("""
    To enable dynamic data fetching from Microsoft Lists:
    
    1. **Configure Microsoft Lists** in `microsoft_lists_config.py`
    2. **Set up your list URL** (export URL, SharePoint URL, or local file)
    3. **Map your columns** to match your data structure
    4. **Start the MCP server** using the controls above
    
    **Benefits:**
    - 🔄 Real-time updates from Microsoft Lists
    - 📊 Automatic data synchronization
    - 🔔 Live change notifications
    - ⚡ No manual data exports needed
    
    **No Microsoft Graph API required!**
    """)
    
    if st.button("📖 View Setup Guide"):
        st.info("Check MICROSOFT_LISTS_SETUP.md for detailed instructions")

def integrate_mcp_with_dashboard():
    """Main function to integrate MCP with the existing dashboard."""
    
    # Show MCP status and controls in sidebar
    mcp_available = show_mcp_status()
    show_mcp_controls()
    
    # Add MCP section to main dashboard
    st.markdown("---")
    st.markdown("## 🔄 Dynamic Data Integration (MCP)")
    
    if not mcp_available:
        show_mcp_setup_instructions()
        return None
    
    # Try to get dynamic data
    dynamic_data = get_dynamic_data()
    
    if dynamic_data is not None:
        st.markdown("### 📊 Live Data from Microsoft Lists")
        
        # Show data preview
        with st.expander("👀 Preview Live Data"):
            st.dataframe(dynamic_data.head(10))
        
        # Show data info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", len(dynamic_data))
        with col2:
            st.metric("Columns", len(dynamic_data.columns))
        with col3:
            st.metric("Last Updated", datetime.now().strftime("%H:%M:%S"))
        
        return dynamic_data
    else:
        st.info("💡 Configure MCP to enable dynamic data fetching")
        show_mcp_setup_instructions()
        return None

# Example usage in your existing dashboard
if __name__ == "__main__":
    st.title("MCP Integration Test")
    
    # Test the integration
    dynamic_data = integrate_mcp_with_dashboard()
    
    if dynamic_data is not None:
        st.success("✅ MCP integration working!")
        st.dataframe(dynamic_data)
    else:
        st.info("ℹ️ MCP not configured or no data available")
