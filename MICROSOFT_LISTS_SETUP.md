# Microsoft Lists Dynamic Integration Setup Guide

This guide will help you set up **real-time, dynamic data fetching** from Microsoft Lists to your Employee Utilization Dashboard using MCP (Model Context Protocol) - **without requiring Microsoft Graph API access**.

## 🚀 What This Achieves

✅ **Real-time Updates**: Dashboard automatically reflects changes in your Microsoft List  
✅ **No Graph API Required**: Works with any Microsoft 365 license  
✅ **Dynamic Data Fetching**: Uses MCP server for intelligent data synchronization  
✅ **Change Detection**: Tracks additions, modifications, and deletions  
✅ **Background Updates**: Automatic polling every 5 minutes (configurable)  
✅ **Live Notifications**: Shows when data changes in real-time  

## 📋 Prerequisites

- Microsoft 365 account with SharePoint access
- Microsoft List containing your employee utilization data
- Python environment with required packages

## 🛠️ Setup Steps

### Step 1: Configure Your Microsoft List

1. **Go to your Microsoft List** in SharePoint
2. **Ensure your list has the required columns**:
   - Employee Name
   - Project Code/ID
   - Actual Hours
   - Week Number
   - Quarter
   - Financial Year
   - (Optional) Email, Overtime, Sick Leave, etc.

### Step 2: Get Your List Data URL

Choose **one** of these methods:

#### Method A: Direct Export URL (Recommended)
1. Go to your Microsoft List
2. Click **"Export"** → **"Export to CSV"**
3. **Copy the download URL** from your browser
4. The URL should look like:
   ```
   https://yourcompany.sharepoint.com/_layouts/15/export.aspx?ListId=your-list-id&Type=CSV
   ```

#### Method B: SharePoint Direct Access
1. Go to your Microsoft List
2. Click **"Share"** → Set to **"Anyone with the link can view"**
3. Copy the SharePoint URL:
   ```
   https://yourcompany.sharepoint.com/sites/team/lists/listname/AllItems.aspx
   ```

#### Method C: Local File with Auto-Refresh
1. Export your list to CSV/Excel
2. Upload to OneDrive/SharePoint
3. Make it publicly accessible
4. Use the direct file URL

### Step 3: Update Configuration

1. **Open `microsoft_lists_config.py`**
2. **Update the configuration**:

```python
LISTS_CONFIG = {
    # Choose your data source method
    "data_source": "export_url",  # or "sharepoint_url" or "local_file_path"
    
    # For Method A (Export URL)
    "export_url": "https://yourcompany.sharepoint.com/_layouts/15/export.aspx?ListId=your-list-id&Type=CSV",
    
    # For Method B (SharePoint URL)
    "sharepoint_url": "https://yourcompany.sharepoint.com/sites/team/lists/listname/AllItems.aspx",
    
    # For Method C (Local File)
    "local_file_path": "/path/to/your/file.csv",
}

# Update column mapping to match your list
LIST_COLUMN_MAPPING = {
    "employee_name": "Name",  # Your actual column name
    "project_id": "Project Code",  # Your actual column name
    "actual_hours": "Actual Hrs",  # Your actual column name
    "week_number": "Week",  # Your actual column name
    "quarter": "Quarter",  # Your actual column name
    "financial_year": "Financial Year",  # Your actual column name
    # Add more mappings as needed
}

# Configure update frequency
REALTIME_CONFIG = {
    "enable_auto_refresh": True,
    "refresh_interval": 300,  # 5 minutes (adjust as needed)
    "enable_notifications": True,
}
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Run the Dynamic Dashboard

```bash
# Option 1: Run the dynamic dashboard directly
streamlit run dynamic_dashboard.py

# Option 2: Run with MCP server in background
python mcp_server.py &
streamlit run dynamic_dashboard.py
```

## 🔄 How Dynamic Updates Work

### MCP Server Architecture
```
Microsoft Lists → MCP Server → Dashboard Components
     ↓              ↓              ↓
  Data Changes → Change Detection → Real-time Updates
```

### Update Process
1. **Background Polling**: MCP server checks for changes every 5 minutes
2. **Change Detection**: Compares data hashes to detect modifications
3. **Event Processing**: Categorizes changes (added/modified/deleted)
4. **Live Notifications**: Dashboard shows real-time update notifications
5. **Automatic Refresh**: Dashboard components update automatically

### Change Types Detected
- ➕ **Added**: New records in the list
- ✏️ **Modified**: Existing records that changed
- 🗑️ **Deleted**: Records removed from the list

## 🎛️ Dashboard Features

### Real-time Status Panel
- ✅ Connection status indicator
- 🕐 Last update timestamp
- 📊 Current record count
- 🔄 Change event counter
- ⚙️ Configuration display

### Manual Controls
- 🔄 **Force Update**: Manually trigger data refresh
- ▶️ **Start Updates**: Begin automatic polling
- ⏹️ **Stop Updates**: Pause automatic updates

### Live Data Visualization
- 📈 **Weekly Utilization Trends**: Auto-updating charts
- 🔥 **Employee-Project Heatmap**: Real-time heatmap
- 🏆 **Top Performers**: Live ranking updates
- 📋 **Recent Changes**: Shows what changed and when

## 🔧 Configuration Options

### Update Frequency
```python
REALTIME_CONFIG = {
    "refresh_interval": 300,  # Seconds between checks (5 minutes)
    "max_retries": 3,         # Retry attempts for failed requests
    "retry_delay": 5,         # Delay between retries
}
```

### Notification Settings
```python
REALTIME_CONFIG = {
    "enable_notifications": True,  # Show update notifications
    "enable_auto_refresh": True,   # Enable automatic updates
}
```

### Column Mapping
```python
LIST_COLUMN_MAPPING = {
    # Dashboard Field: Microsoft List Column
    "employee_name": "Employee Name",
    "project_id": "Project Code",
    "actual_hours": "Hours Worked",
    # ... add more as needed
}
```

## 🚨 Troubleshooting

### Connection Issues
```bash
# Test your configuration
python -c "
from microsoft_lists_client import MicrosoftListsClient
from microsoft_lists_config import LISTS_CONFIG
client = MicrosoftListsClient(LISTS_CONFIG)
result = client.test_connection()
print('Success:', result['success'])
print('Message:', result['message'])
"
```

### Common Problems

**"Connection failed"**
- ✅ Check if your URL is correct
- ✅ Verify the list is accessible
- ✅ Ensure proper permissions are set

**"No data retrieved"**
- ✅ Check column mapping in configuration
- ✅ Verify your list has data
- ✅ Test the URL manually in browser

**"Updates not working"**
- ✅ Check if MCP server is running
- ✅ Verify refresh interval setting
- ✅ Look at server logs for errors

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Performance Optimization

### For Large Lists
```python
REALTIME_CONFIG = {
    "refresh_interval": 600,  # Check every 10 minutes for large lists
    "max_retries": 5,         # More retries for reliability
}
```

### For High-Frequency Updates
```python
REALTIME_CONFIG = {
    "refresh_interval": 60,   # Check every minute
    "enable_notifications": False,  # Reduce UI updates
}
```

## 🔒 Security Considerations

- ✅ Use read-only access to your Microsoft List
- ✅ Don't expose sensitive data in URLs
- ✅ Regularly rotate access permissions
- ✅ Monitor access logs in SharePoint

## 🆘 Need Help?

1. **Check the dashboard sidebar** for connection status
2. **Use the "Test Connection" button** to verify setup
3. **Check server logs** for detailed error messages
4. **Verify your Microsoft List structure** matches the expected format

## 🎉 You're All Set!

Once configured, your dashboard will:
- 🔄 **Automatically fetch** the latest data from Microsoft Lists
- 📊 **Display real-time** utilization metrics and charts
- 🔔 **Notify you** when data changes
- 📈 **Update visualizations** without manual refresh

**No more manual data exports or updates needed!**
