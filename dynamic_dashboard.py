"""
Dynamic Dashboard Component for Microsoft Lists Integration

This component provides real-time updates to the Employee Utilization Dashboard
by subscribing to the MCP server for Microsoft Lists data changes.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import logging
from typing import Optional, Dict, Any, List
from mcp_server import get_mcp_server, get_latest_data, get_recent_changes, start_dynamic_updates, stop_dynamic_updates
from microsoft_lists_config import LISTS_CONFIG, REALTIME_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardSubscriber:
    """Dashboard component that subscribes to MCP server updates."""
    
    def __init__(self):
        self.last_notification_time = None
        self.update_count = 0
    
    def on_data_change(self, changes):
        """Handle data change notifications from MCP server."""
        try:
            self.last_notification_time = datetime.now()
            self.update_count += len(changes)
            
            # Show notification in Streamlit
            change_types = {}
            for change in changes:
                change_types[change.change_type] = change_types.get(change.change_type, 0) + 1
            
            change_summary = ", ".join([f"{count} {change_type}" for change_type, count in change_types.items()])
            st.success(f"🔄 Data updated! {change_summary} detected at {self.last_notification_time.strftime('%H:%M:%S')}")
            
            # Force Streamlit to rerun
            st.rerun()
            
        except Exception as e:
            logger.error(f"Error handling data change notification: {str(e)}")

def initialize_dynamic_dashboard():
    """Initialize the dynamic dashboard with MCP server connection."""
    
    # Initialize MCP server
    mcp_server = get_mcp_server()
    
    # Create and register dashboard subscriber
    if 'dashboard_subscriber' not in st.session_state:
        st.session_state.dashboard_subscriber = DashboardSubscriber()
        mcp_server.subscribe(st.session_state.dashboard_subscriber)
    
    # Start dynamic updates if not already running
    if not mcp_server.update_thread or not mcp_server.update_thread.is_alive():
        mcp_server.start_background_updates()
    
    return mcp_server

def show_dashboard_status(mcp_server):
    """Display dashboard status and connection information."""
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔄 Dynamic Updates Status")
    
    # Get server status
    status = mcp_server.get_status()
    
    # Connection status
    if status["is_running"]:
        st.sidebar.success("✅ Dynamic updates active")
    else:
        st.sidebar.error("❌ Dynamic updates inactive")
    
    # Last update time
    if status["last_update"]:
        last_update = datetime.fromisoformat(status["last_update"])
        time_diff = datetime.now() - last_update
        
        if time_diff.total_seconds() < 60:
            st.sidebar.info(f"🕐 Last update: {time_diff.seconds}s ago")
        elif time_diff.total_seconds() < 3600:
            st.sidebar.info(f"🕐 Last update: {int(time_diff.total_seconds()/60)}m ago")
        else:
            st.sidebar.info(f"🕐 Last update: {int(time_diff.total_seconds()/3600)}h ago")
    else:
        st.sidebar.warning("🕐 No updates yet")
    
    # Data statistics
    st.sidebar.metric("📊 Records", status["data_records"])
    st.sidebar.metric("🔄 Change Events", status["change_events_count"])
    
    # Configuration info
    st.sidebar.markdown("**Configuration:**")
    st.sidebar.text(f"Source: {status['config']['data_source']}")
    st.sidebar.text(f"Interval: {status['config']['refresh_interval']}s")
    
    # Manual controls
    st.sidebar.markdown("### 🎛️ Manual Controls")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("🔄 Force Update", help="Manually trigger data update"):
            mcp_server.force_update()
            st.rerun()
    
    with col2:
        if st.button("⏹️ Stop Updates", help="Stop automatic updates"):
            mcp_server.stop_background_updates()
            st.rerun()
    
    if not status["is_running"]:
        if st.sidebar.button("▶️ Start Updates", help="Start automatic updates"):
            mcp_server.start_background_updates()
            st.rerun()

def show_recent_changes():
    """Display recent changes in the Microsoft Lists data."""
    
    st.markdown("---")
    st.subheader("📋 Recent Changes")
    
    # Get recent changes (last hour)
    recent_changes = get_recent_changes(hours=1)
    
    if not recent_changes:
        st.info("No recent changes detected.")
        return
    
    # Group changes by type
    change_summary = {}
    for change in recent_changes:
        change_type = change.change_type
        if change_type not in change_summary:
            change_summary[change_type] = []
        change_summary[change_type].append(change)
    
    # Display changes
    for change_type, changes in change_summary.items():
        st.markdown(f"**{change_type.title()} ({len(changes)} items):**")
        
        for change in changes[-5:]:  # Show last 5 changes of each type
            timestamp = change.timestamp.strftime("%H:%M:%S")
            
            if change_type == "added":
                st.success(f"➕ [{timestamp}] Added record {change.record_id}")
            elif change_type == "modified":
                st.warning(f"✏️ [{timestamp}] Modified record {change.record_id}")
            elif change_type == "deleted":
                st.error(f"🗑️ [{timestamp}] Deleted record {change.record_id}")
    
    if len(recent_changes) > 15:
        st.info(f"... and {len(recent_changes) - 15} more changes")

def show_dynamic_utilization_dashboard(data: pd.DataFrame):
    """Display the dynamic utilization dashboard."""
    
    if data is None or len(data) == 0:
        st.warning("No data available from Microsoft Lists")
        return
    
    st.header("🔄 Dynamic Employee Utilization Dashboard")
    
    # Show last update time
    mcp_server = get_mcp_server()
    status = mcp_server.get_status()
    if status["last_update"]:
        last_update = datetime.fromisoformat(status["last_update"])
        st.info(f"📅 Data last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create utilization metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_employees = data['employee_name'].nunique() if 'employee_name' in data.columns else 0
        st.metric("👥 Total Employees", total_employees)
    
    with col2:
        total_hours = data['actual_hours'].sum() if 'actual_hours' in data.columns else 0
        st.metric("⏰ Total Hours", f"{total_hours:.1f}")
    
    with col3:
        total_projects = data['project_id'].nunique() if 'project_id' in data.columns else 0
        st.metric("📋 Total Projects", total_projects)
    
    with col4:
        avg_utilization = data['actual_hours'].mean() if 'actual_hours' in data.columns else 0
        st.metric("📊 Avg Hours", f"{avg_utilization:.1f}")
    
    # Weekly utilization chart
    if 'week_number' in data.columns and 'actual_hours' in data.columns:
        st.subheader("📈 Weekly Utilization Trend")
        
        weekly_data = data.groupby('week_number')['actual_hours'].sum().reset_index()
        
        fig = px.line(
            weekly_data, 
            x='week_number', 
            y='actual_hours',
            title="Total Hours by Week",
            markers=True
        )
        fig.update_layout(
            xaxis_title="Week Number",
            yaxis_title="Total Hours",
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Employee utilization heatmap
    if 'employee_name' in data.columns and 'project_id' in data.columns and 'actual_hours' in data.columns:
        st.subheader("🔥 Employee-Project Utilization Heatmap")
        
        heatmap_data = data.pivot_table(
            index='employee_name', 
            columns='project_id', 
            values='actual_hours', 
            aggfunc='sum', 
            fill_value=0
        )
        
        # Create heatmap
        fig = px.imshow(
            heatmap_data.values,
            labels=dict(x="Project ID", y="Employee", color="Hours"),
            x=heatmap_data.columns,
            y=heatmap_data.index,
            color_continuous_scale="YlOrRd",
            aspect="auto"
        )
        fig.update_layout(
            title="Employee Project Hours Distribution",
            xaxis_title="Project ID",
            yaxis_title="Employee Name"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Top performers
    if 'employee_name' in data.columns and 'actual_hours' in data.columns:
        st.subheader("🏆 Top Performers")
        
        top_performers = data.groupby('employee_name')['actual_hours'].sum().nlargest(10)
        
        fig = px.bar(
            x=top_performers.values,
            y=top_performers.index,
            orientation='h',
            title="Top 10 Employees by Total Hours"
        )
        fig.update_layout(
            xaxis_title="Total Hours",
            yaxis_title="Employee Name"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Raw data table
    with st.expander("📋 Raw Data Table"):
        st.dataframe(data, use_container_width=True)

def main():
    """Main dashboard function."""
    
    st.set_page_config(
        page_title="Dynamic Employee Utilization Dashboard",
        page_icon="🔄",
        layout="wide"
    )
    
    st.title("🔄 Dynamic Employee Utilization Dashboard")
    st.markdown("*Real-time updates from Microsoft Lists*")
    
    # Initialize dynamic dashboard
    try:
        mcp_server = initialize_dynamic_dashboard()
        
        # Show dashboard status
        show_dashboard_status(mcp_server)
        
        # Get current data
        data = get_latest_data(force_refresh=False)
        
        if data is not None:
            # Show main dashboard
            show_dynamic_utilization_dashboard(data)
            
            # Show recent changes
            show_recent_changes()
        else:
            st.error("❌ Unable to load data from Microsoft Lists")
            
            # Show connection test
            if st.button("🔍 Test Connection"):
                test_result = mcp_server.test_connection()
                if test_result["success"]:
                    st.success(f"✅ Connection successful: {test_result['message']}")
                else:
                    st.error(f"❌ Connection failed: {test_result['message']}")
    
    except Exception as e:
        st.error(f"❌ Error initializing dynamic dashboard: {str(e)}")
        logger.error(f"Dashboard initialization error: {str(e)}")

if __name__ == "__main__":
    main()
