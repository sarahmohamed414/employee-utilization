# Employee Project Utilization Dashboard

A comprehensive dashboard for analyzing employee project utilization with Neo4j graph database, AI-powered insights using Ollama, and **dynamic data fetching from Microsoft Lists using MCP (Model Context Protocol)**.

## 🚀 Features

### Core Dashboard Features
- **Team Utilization Overview**: Visualize all employees' hours across projects
- **Weekly Utilization Analysis**: Track utilization patterns by week with color-coded status
- **Individual Employee Dashboard**: Drill down into specific employee project assignments
- **Interactive Heatmaps**: Customizable heatmaps for selected employees
- **Project Breakdown Charts**: Detailed project-wise hour distribution

### Advanced Features
- **AI-Powered Insights**: Ask questions about utilization patterns using Ollama
- **Graph Database Integration**: Neo4j for advanced relationship analysis
- **Dynamic Data Fetching**: Real-time updates from Microsoft Lists (MCP)
- **Change Detection**: Automatic notifications when data changes
- **Background Updates**: Continuous data synchronization

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- Docker (for Neo4j and Ollama)
- Microsoft 365 account with SharePoint access (for MCP integration)

### Step 1: Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/employee-utilization-dashboard.git
cd employee-utilization-dashboard
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Start Services
```bash
# Start Neo4j container
docker run -d --name neo4j-utilization \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/utilization123 \
  neo4j:5.15

# Start Ollama (if not already running)
docker run -d --name ollama \
  -p 11434:11434 \
  ollama/ollama:latest
```

### Step 4: Initialize Database if you're using the static CSV data approach
```bash
python3 setup_graph_db.py
```

### Step 5: Run Dashboard
```bash
# Original dashboard with static CSV data
streamlit run dashboard.py

# Enhanced dashboard with MCP integration
streamlit run dashboard_with_mcp.py
```

## 📊 Data Sources

### Static CSV Data
- Place your CSV file in the project directory
- The dashboard will automatically load and process the data
- Supports the standard employee utilization format

### Dynamic Microsoft Lists (MCP)
- Real-time data fetching from Microsoft Lists
- No Microsoft Graph API required
- Automatic change detection and updates
- Background synchronization every 5 minutes

## 🔧 MCP Configuration

### Step 1: Get Microsoft List URL
1. Go to your Microsoft List in SharePoint
2. Click **Export** → **Export to CSV**
3. Copy the download URL from your browser

### Step 2: Update Configuration
Edit `microsoft_lists_config.py`:
```python
LISTS_CONFIG = {
    "data_source": "export_url",
    "export_url": "YOUR_MICROSOFT_LIST_URL_HERE"
}

# Map your list columns to dashboard fields
LIST_COLUMN_MAPPING = {
    "employee_name": "Name",           # Your actual column name
    "project_id": "Project Code",      # Your actual column name
    "actual_hours": "Actual Hrs",      # Your actual column name
    "week_number": "Week",             # Your actual column name
    "quarter": "Quarter",              # Your actual column name
    "financial_year": "Financial Year" # Your actual column name
}
```

### Step 3: Test Connection
```bash
python -c "
from microsoft_lists_client import MicrosoftListsClient
from microsoft_lists_config import LISTS_CONFIG
client = MicrosoftListsClient(LISTS_CONFIG)
result = client.test_connection()
print('Success:', result['success'])
print('Message:', result['message'])
"
```

## 🎯 Usage

### Basic Dashboard
1. Run `streamlit run dashboard.py`
2. Select data source (static CSV or dynamic MCP)
3. Explore team and individual utilization
4. Use AI assistant for insights

### MCP-Enhanced Dashboard
1. Run `streamlit run dashboard_with_mcp.py`
2. Configure Microsoft Lists connection
3. Enable automatic updates
4. Monitor real-time data changes

### AI Assistant
- Ask questions about utilization patterns
- Get insights on under/over-utilized employees
- Analyze project workload distribution
- Generate utilization reports

## 📁 Project Structure

```
├── dashboard.py                    # Original dashboard
├── dashboard_with_mcp.py          # MCP-enhanced dashboard
├── mcp_server.py                  # MCP server for data sync
├── microsoft_lists_client.py      # Microsoft Lists client
├── microsoft_lists_config.py      # Configuration settings
├── integrate_mcp.py               # MCP integration helper
├── utilization_graph.py           # Neo4j graph operations
├── setup_graph_db.py              # Database initialization
├── test_connection.py             # Connection testing
├── requirements.txt               # Python dependencies
├── README.md                      # This file
├── MICROSOFT_LISTS_SETUP.md       # Detailed MCP setup guide
└── Anonymized_Employee_Utilization.csv  # Sample data
```

## 🔄 MCP Features

### Real-time Updates
- Automatic data synchronization every 5 minutes
- Change detection for additions, modifications, and deletions
- Live notifications when data changes
- Background polling without user intervention

### Data Sources Supported
- **Export URL**: Direct CSV/Excel export from Microsoft Lists
- **SharePoint URL**: Direct access to list view
- **Local File**: Manual export with auto-refresh
- **Power Automate**: Scheduled exports (if available)

### Benefits
- ✅ No Microsoft Graph API required
- ✅ No Azure AD setup needed
- ✅ Works with any Microsoft 365 license
- ✅ Real-time updates possible
- ✅ Simple to implement and maintain
- ✅ No additional costs

## 🚨 Troubleshooting

### Common Issues

**Dashboard won't start:**
```bash
# Check if all services are running
docker ps
python3 test_connection.py
```

**MCP connection failed:**
```bash
# Test Microsoft Lists connection
python -c "from microsoft_lists_client import *; test_connection()"
```

**Neo4j connection issues:**
```bash
# Check Neo4j container
docker logs neo4j-utilization
docker restart neo4j-utilization
```

**Ollama not responding:**
```bash
# Check Ollama container
docker logs ollama
docker restart ollama
```

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance Optimization

### For Large Datasets
- Increase refresh interval to 10-15 minutes
- Use local file method for better performance
- Enable data caching in configuration

### For High-Frequency Updates
- Set refresh interval to 1-2 minutes
- Disable notifications to reduce UI updates
- Use export URL method for fastest updates

## 🔒 Security Considerations

- Use read-only access to Microsoft Lists
- Don't expose sensitive data in URLs
- Regularly rotate access permissions
- Monitor access logs in SharePoint
- Use environment variables for sensitive configuration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is for internal use only.

## 🆘 Support

- Check the troubleshooting section above
- Review `MICROSOFT_LISTS_SETUP.md` for detailed MCP setup
- Open an issue on GitHub for bugs or feature requests
- Check the dashboard sidebar for connection status

## 🎉 What's Next

- **Enhanced AI Features**: More sophisticated utilization predictions
- **Advanced Analytics**: Trend analysis and forecasting
- **Integration Options**: Connect to more data sources
- **Mobile Support**: Responsive design for mobile devices
- **Export Features**: Generate reports and exports

---

**Built with ❤️ using Streamlit, Neo4j, Ollama, and MCP**
