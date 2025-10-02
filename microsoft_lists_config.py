"""
Microsoft Lists Configuration for Employee Utilization Dashboard

This file contains configuration settings for Microsoft Lists integration
without requiring Microsoft Graph API access.
"""

# Microsoft Lists Configuration
LISTS_CONFIG = {
    # Option 1: Direct URL to exported CSV/Excel file from Microsoft Lists
    "export_url": "PASTE_YOUR_EXPORT_URL_HERE",  # Direct download URL from your Microsoft List export
    
    # Option 2: Local file path (if you download the export manually)
    "local_file_path": "EG COE - ConsultingQ3.csv",  # Path to downloaded CSV/Excel file
    
    # Option 3: SharePoint direct link (if you can make it publicly accessible)
    "sharepoint_url": "PASTE_YOUR_SHAREPOINT_LIST_URL_HERE",  # Direct link to the list view
    
    # Data source preference
    "data_source": "sharepoint_url",  # Options: "export_url", "local_file_path", "sharepoint_url"
}

# Real-time Update Configuration
REALTIME_CONFIG = {
    "enable_auto_refresh": True,  # Enable automatic data refresh
    "refresh_interval": 300,  # Refresh interval in seconds (5 minutes)
    "enable_notifications": True,  # Show notifications when data updates
    "max_retries": 3,  # Maximum retry attempts for failed requests
    "retry_delay": 5,  # Delay between retries in seconds
}

# Data Mapping Configuration
# Map your Microsoft List columns to dashboard fields
LIST_COLUMN_MAPPING = {
    # Employee Information
    "employee_name": "Name",  # Column name in your Microsoft List
    "employee_email": "Email",  # Column name in your Microsoft List
    "employee_id": "Id",  # Column name in your Microsoft List
    
    # Project Information
    "project_id": "Project Code",  # Column name in your Microsoft List
    "project_name": "Project Name",  # Column name in your Microsoft List
    
    # Time Tracking
    "actual_hours": "Actual Hrs",  # Column name in your Microsoft List
    "week_number": "Week",  # Column name in your Microsoft List
    "quarter": "Quarter",  # Column name in your Microsoft List
    "financial_year": "Financial Year",  # Column name in your Microsoft List
    
    # Additional Fields
    "overtime": "Overtime",  # Column name in your Microsoft List
    "time_card": "Time Card",  # Column name in your Microsoft List
    "sick_leave": "Sick Leave",  # Column name in your Microsoft List
    "annual_leave": "Annual Leave",  # Column name in your Microsoft List
    "onsite_days": "Onsite Days",  # Column name in your Microsoft List
    
    # Timestamps
    "start_time": "Start time",  # Column name in your Microsoft List
    "completion_time": "Completion time",  # Column name in your Microsoft List
    "modified_by": "Modified By",  # Column name in your Microsoft List
}

# Example configuration:
"""
LISTS_CONFIG = {
    "export_url": "https://yourcompany.sharepoint.com/sites/team/_layouts/15/export.aspx?ListId=your-list-id&Type=CSV",
    "data_source": "export_url"
}
"""

# How to get Microsoft Lists data without Graph API:

"""
METHOD 1: DIRECT EXPORT (RECOMMENDED)
1. Go to your Microsoft List in SharePoint
2. Click on "Export" → "Export to Excel" or "Export to CSV"
3. Copy the download URL from the browser
4. Use this URL directly in your dashboard

METHOD 2: MANUAL EXPORT WITH AUTO-REFRESH
1. Export your Microsoft List to CSV/Excel
2. Save it to a shared location (OneDrive, SharePoint, etc.)
3. Make it publicly accessible
4. Use the direct file URL in your configuration
5. Set up automatic refresh to periodically check for updates

METHOD 3: SHAREPOINT DIRECT ACCESS
1. Go to your Microsoft List
2. Click "Share" and set permissions to "Anyone with the link can view"
3. Use the direct SharePoint URL
4. The system will attempt to parse the HTML table data

METHOD 4: POWER AUTOMATE (IF AVAILABLE)
1. Create a Power Automate flow that exports your list data
2. Set it to run on a schedule (every few minutes/hours)
3. Save the output to a publicly accessible location
4. Your dashboard will automatically pick up the latest data

BENEFITS OF THESE APPROACHES:
✅ No Microsoft Graph API required
✅ No Azure AD setup needed
✅ Works with any Microsoft 365 license
✅ Real-time updates possible
✅ Simple to implement and maintain
✅ No additional costs

RECOMMENDED SETUP:
1. Use Method 1 (Direct Export) for the best real-time experience
2. Set refresh interval to 5-15 minutes
3. Enable notifications for data updates
4. Configure proper column mapping for your list structure
"""
