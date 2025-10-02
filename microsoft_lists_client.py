"""
Microsoft Lists Client for Employee Utilization Dashboard

This module provides functionality to fetch data from Microsoft Lists
without requiring Microsoft Graph API access.
"""

import pandas as pd
import streamlit as st
import requests
import io
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from urllib.parse import urlparse, parse_qs
import re
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MicrosoftListsClient:
    """Client for fetching data from Microsoft Lists without Graph API."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Microsoft Lists client with configuration."""
        self.config = config
        self.last_fetch_time = None
        self.cached_data = None
        self.session = requests.Session()
        
        # Set up session with proper headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_export_url(self, list_url: str) -> Optional[str]:
        """Extract export URL from Microsoft List URL."""
        try:
            # Parse the list URL to extract list ID
            parsed_url = urlparse(list_url)
            
            # Look for list ID in the URL
            list_id_match = re.search(r'ListId=([a-f0-9-]+)', list_url)
            if not list_id_match:
                # Try to extract from the path
                path_parts = parsed_url.path.split('/')
                if 'lists' in path_parts:
                    list_index = path_parts.index('lists')
                    if list_index + 1 < len(path_parts):
                        list_name = path_parts[list_index + 1]
                        # This would need to be converted to list ID
                        logger.warning(f"Found list name '{list_name}' but need list ID")
            
            list_id = list_id_match.group(1) if list_id_match else None
            
            if not list_id:
                logger.error("Could not extract list ID from URL")
                return None
            
            # Construct export URL
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            export_url = f"{base_url}/_layouts/15/export.aspx?ListId={list_id}&Type=CSV"
            
            return export_url
            
        except Exception as e:
            logger.error(f"Error extracting export URL: {str(e)}")
            return None
    
    def fetch_data_from_export_url(self, export_url: str) -> Optional[pd.DataFrame]:
        """Fetch data from Microsoft List export URL."""
        try:
            response = self.session.get(export_url, timeout=30)
            response.raise_for_status()
            
            # Check if we got CSV data
            content_type = response.headers.get('content-type', '').lower()
            if 'text/csv' in content_type or 'application/csv' in content_type:
                # Read CSV data
                csv_data = io.StringIO(response.text)
                df = pd.read_csv(csv_data)
                return df
            else:
                # Try to parse as Excel
                excel_data = io.BytesIO(response.content)
                df = pd.read_excel(excel_data)
                return df
                
        except Exception as e:
            logger.error(f"Error fetching data from export URL: {str(e)}")
            return None
    
    def fetch_data_from_sharepoint_url(self, sharepoint_url: str) -> Optional[pd.DataFrame]:
        """Fetch data from SharePoint list view (HTML parsing)."""
        try:
            response = self.session.get(sharepoint_url, timeout=30)
            response.raise_for_status()
            
            # Parse HTML to extract table data
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for data tables
            tables = soup.find_all('table')
            if not tables:
                logger.error("No tables found in SharePoint page")
                return None
            
            # Find the main data table (usually the largest one)
            main_table = max(tables, key=lambda t: len(t.find_all('tr')))
            
            # Convert HTML table to DataFrame
            df = pd.read_html(str(main_table))[0]
            
            # Clean up the DataFrame
            df = self.clean_sharepoint_data(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data from SharePoint URL: {str(e)}")
            return None
    
    def clean_sharepoint_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean data extracted from SharePoint HTML."""
        try:
            # Remove empty rows and columns
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Remove any HTML artifacts
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.strip()
                    df[col] = df[col].str.replace(r'<[^>]+>', '', regex=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error cleaning SharePoint data: {str(e)}")
            return df
    
    def fetch_data_from_local_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """Fetch data from local file."""
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                logger.error(f"Unsupported file format: {file_path}")
                return None
            
            return df
            
        except Exception as e:
            logger.error(f"Error reading local file: {str(e)}")
            return None
    
    def fetch_latest_data(self, force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """Fetch the latest data from Microsoft Lists."""
        try:
            # Check if we should use cached data
            if not force_refresh and self.cached_data is not None and self.last_fetch_time:
                refresh_interval = self.config.get("refresh_interval", 300)
                if datetime.now() - self.last_fetch_time < timedelta(seconds=refresh_interval):
                    logger.info("Using cached data")
                    return self.cached_data
            
            data_source = self.config.get("data_source", "export_url")
            
            if data_source == "export_url":
                export_url = self.config.get("export_url")
                if not export_url:
                    logger.error("Export URL not configured")
                    return None
                df = self.fetch_data_from_export_url(export_url)
                
            elif data_source == "sharepoint_url":
                sharepoint_url = self.config.get("sharepoint_url")
                if not sharepoint_url:
                    logger.error("SharePoint URL not configured")
                    return None
                df = self.fetch_data_from_sharepoint_url(sharepoint_url)
                
            elif data_source == "local_file_path":
                file_path = self.config.get("local_file_path")
                if not file_path:
                    logger.error("Local file path not configured")
                    return None
                df = self.fetch_data_from_local_file(file_path)
                
            else:
                logger.error(f"Unknown data source: {data_source}")
                return None
            
            if df is not None:
                # Process and clean the data
                df = self.process_list_data(df)
                
                # Cache the data
                self.cached_data = df
                self.last_fetch_time = datetime.now()
                
                logger.info(f"Successfully fetched {len(df)} records from Microsoft Lists")
                
                # Show notification if enabled
                if self.config.get("enable_notifications", True):
                    st.success(f"✅ Data updated! Fetched {len(df)} records from Microsoft Lists")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching latest data: {str(e)}")
            return None
    
    def process_list_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and clean Microsoft Lists data."""
        try:
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Map columns if mapping is provided
            column_mapping = self.config.get("column_mapping", {})
            if column_mapping:
                # Rename columns based on mapping
                rename_dict = {}
                for dashboard_field, list_column in column_mapping.items():
                    if list_column in df.columns:
                        rename_dict[list_column] = dashboard_field
                
                df = df.rename(columns=rename_dict)
            
            # Convert numeric columns
            numeric_columns = ["actual_hours", "overtime", "sick_leave", "annual_leave", "onsite_days", "week_number"]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Convert date columns
            date_columns = ["start_time", "completion_time"]
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Clean text columns
            text_columns = ["employee_name", "employee_email", "project_id", "project_name", "time_card"]
            for col in text_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
            
            return df
            
        except Exception as e:
            logger.error(f"Error processing list data: {str(e)}")
            return df
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to Microsoft Lists."""
        result = {
            "success": False,
            "message": "",
            "details": {}
        }
        
        try:
            data_source = self.config.get("data_source", "export_url")
            result["details"]["data_source"] = data_source
            
            if data_source == "export_url":
                export_url = self.config.get("export_url")
                if not export_url:
                    result["message"] = "Export URL not configured"
                    return result
                
                # Test the URL
                response = self.session.head(export_url, timeout=10)
                if response.status_code == 200:
                    result["success"] = True
                    result["message"] = "Export URL accessible"
                    result["details"]["url"] = export_url
                else:
                    result["message"] = f"Export URL not accessible: {response.status_code}"
                    
            elif data_source == "sharepoint_url":
                sharepoint_url = self.config.get("sharepoint_url")
                if not sharepoint_url:
                    result["message"] = "SharePoint URL not configured"
                    return result
                
                # Test the URL
                response = self.session.head(sharepoint_url, timeout=10)
                if response.status_code == 200:
                    result["success"] = True
                    result["message"] = "SharePoint URL accessible"
                    result["details"]["url"] = sharepoint_url
                else:
                    result["message"] = f"SharePoint URL not accessible: {response.status_code}"
                    
            elif data_source == "local_file_path":
                file_path = self.config.get("local_file_path")
                if not file_path:
                    result["message"] = "Local file path not configured"
                    return result
                
                import os
                if os.path.exists(file_path):
                    result["success"] = True
                    result["message"] = "Local file accessible"
                    result["details"]["file_path"] = file_path
                else:
                    result["message"] = f"Local file not found: {file_path}"
            
            # Try to fetch a small amount of data
            if result["success"]:
                df = self.fetch_latest_data(force_refresh=True)
                if df is not None:
                    result["details"]["records_count"] = len(df)
                    result["details"]["columns"] = list(df.columns)
                else:
                    result["success"] = False
                    result["message"] = "Connection test passed but no data retrieved"
            
        except Exception as e:
            result["message"] = f"Connection test failed: {str(e)}"
        
        return result


def load_data_from_microsoft_lists(config: Dict[str, Any]) -> Optional[pd.DataFrame]:
    """
    Load data from Microsoft Lists and convert to pandas DataFrame.
    
    Args:
        config: Microsoft Lists configuration
    
    Returns:
        pandas DataFrame with the list data, or None if loading fails
    """
    try:
        client = MicrosoftListsClient(config)
        
        # Test connection first
        test_result = client.test_connection()
        if not test_result["success"]:
            st.error(f"Connection failed: {test_result['message']}")
            return None
        
        # Fetch data
        df = client.fetch_latest_data(force_refresh=True)
        
        if df is not None and len(df) > 0:
            st.success(f"✅ Successfully loaded {len(df)} records from Microsoft Lists")
            return df
        else:
            st.error("No data retrieved from Microsoft Lists")
            return None
        
    except Exception as e:
        st.error(f"Error loading data from Microsoft Lists: {str(e)}")
        return None


def create_shareable_url_instructions():
    """Show instructions for creating shareable URLs from Microsoft Lists."""
    st.markdown("### How to Get Data from Microsoft Lists")
    st.markdown("""
    **Method 1: Direct Export (Recommended)**
    
    1. **Go to your Microsoft List** in SharePoint
    2. **Click on "Export"** → "Export to Excel" or "Export to CSV"
    3. **Copy the download URL** from the browser address bar
    4. **Paste this URL** in your configuration
    
    **Method 2: SharePoint Direct Access**
    
    1. **Go to your Microsoft List**
    2. **Click "Share"** and set permissions to "Anyone with the link can view"
    3. **Copy the SharePoint URL** (should look like: `https://yourcompany.sharepoint.com/sites/team/lists/listname/AllItems.aspx`)
    4. **Paste this URL** in your configuration
    
    **Method 3: Local File with Auto-Refresh**
    
    1. **Export your Microsoft List** to CSV/Excel
    2. **Save it to a shared location** (OneDrive, SharePoint, etc.)
    3. **Make it publicly accessible**
    4. **Use the direct file URL** in your configuration
    
    **Benefits:**
    - ✅ No Microsoft Graph API required
    - ✅ No Azure AD setup needed
    - ✅ Works with any Microsoft 365 license
    - ✅ Real-time updates possible
    - ✅ Simple to implement and maintain
    """)

if __name__ == "__main__":
    print("Microsoft Lists Client (No Graph API Required)")
    print("This module provides functionality to fetch data from Microsoft Lists")
