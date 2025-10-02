# Dashboard Code Documentation

This document provides a detailed explanation of the Employee Project Utilization Dashboard implementation.

## Overview

The dashboard is built using Streamlit and Pandas to visualize employee project utilization data from a CSV file. It provides both team-wide and individual employee views of project hours and utilization.


### Data Loading and Processing


The dashboard expects a CSV file with the following structure:
- Base columns: Id, Start time, Completion time, Email, Name
- Project blocks: Each employee can have multiple projects (up to 13)
- Each project block contains:
  - Project ID
  - Actual Hours
  - Time Card status
  - Overtime hours
  - Sick Leave days
  - Annual Leave days
  - Onsite Days

### Data Transformation

The code processes the CSV data through several steps:

1. **Project Block Identification**
   - Identifies up to 13 project blocks per employee
   - Each block contains project details and associated metrics

2. **Data Melting**
   - Transforms the wide-format CSV into a long-format DataFrame
   - Creates individual records for each employee-project combination
   - Preserves all associated metrics (hours, leaves, etc.)

### Dashboard Components

#### 1. Team Overview
- Displays a heatmap of all employees' hours across projects
- Uses a pivot table to aggregate hours by employee and project
- Visualizes using a color gradient (YlOrRd) for easy interpretation

#### 2. Individual Employee Dashboard
- Interactive employee selector
- Shows detailed project hours for the selected employee
- Includes:
  - Tabular data view
  - Bar chart visualization of project hours
  - All associated metrics (leaves, onsite days, etc.)

## Key Features

1. **Interactive Selection**
   - Users can switch between team view and individual employee views
   - Real-time updates when selecting different employees

2. **Data Visualization**
   - Team heatmap for overall utilization
   - Individual bar charts for detailed project analysis
   - Color-coded heatmaps for quick pattern recognition

3. **Automatic Updates**
   - Dashboard refreshes automatically with new CSV data
   - No manual intervention needed for data updates

## Technical Implementation Details

### Dependencies
- pandas: Data manipulation and analysis
- streamlit: Web interface and visualization
- matplotlib: Additional plotting capabilities (if needed)

### Data Processing Flow
1. CSV Loading → Data Cleaning → Project Block Identification
2. Data Melting → Record Creation → DataFrame Generation
3. Visualization Generation → Interactive Display

## Usage Notes

1. **CSV Format Requirements**
   - Must follow the specified column naming convention
   - Project blocks should be numbered sequentially
   - All required columns must be present

2. **Data Updates**
   - Simply replace the CSV file to update the dashboard
   - No code changes needed for data updates


## Future Enhancements

1. **Planned Features**
   - Utilization status indicators (under/over-utilized)
   - AI-based capacity forecasting


## Troubleshooting

Common issues and solutions:
1. **CSV Loading Errors**
   - Ensure CSV file is in the correct directory
   - Verify column names match expected format

2. **Visualization Issues**
   - Check for missing or invalid data
   - Verify data types in the CSV


For additional support or feature requests, please open an issue on GitHub.

## Code Documentation

### 1. Data Loading and Initial Setup
```python
import pandas as pd
import streamlit as st

# Load the CSV file
csv_path = 'FY26-Q1-Egypt-Consulting-Actuals-Tracker-1.csv'
df = pd.read_csv(csv_path)
df.columns = df.columns.str.strip()  # Clean column names
```

### 2. Project Block Structure
```python
# Define base columns that are common for all records
base_columns = [
    'Id',
    'Start time',
    'Completion time',
    'Email',
    'Name',
]

# Define project block structure
project_blocks = []
for i in range(13):  # Support up to 13 project blocks
    suffix = '' if i == 0 else str(i)
    block = {
        'Project ID': f'Project ID in FF(Please add multiple projects on separate lines. Please consult with the project PM to confirm the project ID- Project ID starts with PR-xxxxxxx){suffix}',
        'Actual Hrs': f'Projects Actual Hrs(Please add the project actual hours in the same order of projects in question no. 1){suffix}',
        'Time Card': f'Time card submitted{suffix}',
        'Overtime': f'Total Number of Overtime hours(Must be billable hrs and recorded in FF){suffix}',
        'Sick Leave': f'Number of sick leave days(please ensure they are submitted to EAS){suffix}',
        'Annual Leave': f'Number of annual leave days(please ensure they are submitted to EAS){suffix}',
        'Onsite Days': f'Number of customer onsite days(At customer premises){suffix}',
    }
    if block['Project ID'] in df.columns:
        project_blocks.append(block)
```

### 3. Data Transformation Process
```python
# Transform data from wide to long format
records = []
for idx, row in df.iterrows():
    # Get base information for each employee
    base = {col: row.get(col, None) for col in base_columns}
    
    # Process each project block
    for block in project_blocks:
        # Split project IDs and hours (they can be multiple per block)
        project_ids = str(row.get(block['Project ID'])).split('\n') if pd.notna(row.get(block['Project ID'])) else []
        actual_hrs = str(row.get(block['Actual Hrs'])).split('\n') if pd.notna(row.get(block['Actual Hrs'])) else []
        
        # Create individual records for each project
        for proj, hrs in zip(project_ids, actual_hrs):
            if proj.strip() and hrs.strip():
                record = base.copy()
                record['Project ID'] = proj.strip()
                try:
                    record['Actual Hrs'] = float(hrs.strip())
                except ValueError:
                    record['Actual Hrs'] = None
                # Add other metrics
                record['Time Card'] = row.get(block['Time Card'])
                record['Overtime'] = row.get(block['Overtime'])
                record['Sick Leave'] = row.get(block['Sick Leave'])
                record['Annual Leave'] = row.get(block['Annual Leave'])
                record['Onsite Days'] = row.get(block['Onsite Days'])
                records.append(record)

# Create the final DataFrame
melted_df = pd.DataFrame(records)
```

### 4. Dashboard Implementation
```python
# Team Overview Section
st.header("Team Utilization Overview")
# Create pivot table for team heatmap
team_heatmap = melted_df.pivot_table(
    index='Name',
    columns='Project ID',
    values='Actual Hrs',
    aggfunc='sum',
    fill_value=0
)
# Display heatmap with color gradient (YlOrRd: Yellow to Orange to Red)
# Darker red indicates higher utilization (more hours)
# Lighter yellow indicates lower utilization (fewer hours)
st.dataframe(team_heatmap.style.background_gradient(cmap='YlOrRd', axis=None))

# Individual Employee Dashboard
st.header("Individual Employee Dashboard")
# Employee selector
employee = st.selectbox(
    "Select Employee",
    ['All'] + list(melted_df['Name'].dropna().unique())
)

# Filter data based on selection
if employee == 'All':
    emp_df = melted_df
else:
    emp_df = melted_df[melted_df['Name'] == employee]

# Display employee data
st.write(f"Showing data for: {employee}")
st.dataframe(emp_df)

# Create and display employee project hours chart
if not emp_df.empty:
    emp_heatmap = emp_df.pivot_table(
        index='Project ID',
        values='Actual Hrs',
        aggfunc='sum'
    )
    st.write("Actual Hours per Project (Bar Chart):")
    st.bar_chart(emp_heatmap)
```

### 5. Key Functions and Their Purposes

1. **Data Loading (`pd.read_csv`)**
   - Purpose: Loads the CSV file into a pandas DataFrame
   - Input: CSV file path
   - Output: Raw DataFrame with all columns

2. **Project Block Processing**
   - Purpose: Identifies and structures project-related columns
   - Input: DataFrame columns
   - Output: List of project block dictionaries

3. **Data Melting Process**
   - Purpose: Transforms wide-format data into long-format
   - Input: Raw DataFrame and project blocks
   - Output: Melted DataFrame with one row per employee-project combination

4. **Heatmap Generation (`pivot_table`)**
   - Purpose: Creates aggregated views of project hours
   - Input: Melted DataFrame
   - Output: Pivot table for visualization

5. **Streamlit Components**
   - `st.header()`: Creates section headers
   - `st.selectbox()`: Creates interactive employee selector
   - `st.dataframe()`: Displays tabular data
   - `st.bar_chart()`: Creates bar chart visualizations

### 6. Data Flow Diagram
```
CSV File
   ↓
Data Loading (pd.read_csv)
   ↓
Column Cleaning (strip whitespace)
   ↓
Project Block Identification
   ↓
Data Melting (wide to long format)
   ↓
DataFrame Creation
   ↓
Visualization Generation
   ├─→ Team Heatmap
   └─→ Individual Dashboard
       ├─→ Employee Selector
       ├─→ Data Table
       └─→ Project Hours Chart
``` 