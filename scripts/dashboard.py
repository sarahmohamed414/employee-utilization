import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import requests
import json
from datetime import datetime
import re
from utilization_graph import UtilizationGraph
from setup_graph_db import setup_database

# Add Ollama API configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral:latest"  # Explicitly using mistral:latest
MODEL_DETAILS = {
    "name": "mistral:latest",
    "size": "4.1GB",
    "parameters": "7.2B",
    "quantization": "Q4_0",
    "family": "llama"
}

def get_available_models():
    """Get list of available models from Ollama"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            return response.json()["models"]
        return []
    except Exception as e:
        st.error(f"Error connecting to Ollama: {str(e)}")
        return []

def query_ollama(prompt, context=""):
    """Query the Ollama API with a prompt and optional context"""
    try:
        # Add system prompt for better analysis
        system_prompt = """You are an AI assistant specialized in analyzing employee utilization data. 
        Your task is to provide clear, concise, and data-driven insights about employee utilization, 
        project workloads, and resource allocation. 
        
        CRITICAL RULES:
        1. ONLY use the actual data provided in the context
        2. NEVER make up or infer employee names, hours, or statistics
        3. If asked about specific employees, verify they exist in the data first
        4. Always include specific numbers and percentages from the data
        5. If data is not available for a query, state "I don't have enough data to answer that question"
        6. For utilization analysis, use the exact hours from the data
        7. When showing rankings or comparisons, use only employees that exist in the data
        8. If the data shows different numbers than what you might expect, trust the data
        9. For weekly questions, use the specific weekly summary provided in the context
        10. Remember that utilization is calculated per week, not across all weeks
        11. Only use weeks that are explicitly listed in the Available Weeks section
        12. If asked about a week not in the Available Weeks list, state that the data is not available for that week
        
        Focus on providing actionable insights based on the actual numbers in the data."""
        
        full_prompt = f"{system_prompt}\n\nContext: {context}\n\nUser: {prompt}\nAssistant:"
        
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": MODEL_NAME,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0,  # Zero temperature for most factual responses
                    "top_p": 0.9,
                    "top_k": 40
                }
            }
        )
        if response.status_code == 200:
            return response.json()["response"]
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error connecting to Ollama: {str(e)}"

def clean_overtime_value(x):
    """Clean and convert overtime values to float"""
    if pd.isna(x) or str(x).strip() == '':
        return 0.0
    
    try:
        # Try direct conversion first
        return float(x)
    except (ValueError, TypeError):
        # If direct conversion fails, try to extract numbers from text
        try:
            # Extract numbers from text like "around 16 to 24 hrs"
            numbers = re.findall(r'\d+', str(x))
            if numbers:
                # Take the average if there's a range
                return sum(float(n) for n in numbers) / len(numbers)
            return 0.0
        except:
            return 0.0

def load_and_process_data(csv_path):
    """Load and process the new CSV data."""
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    # Rename columns for easier access
    df.rename(columns={'Modified By': 'Name', 'Project Code': 'Project ID'}, inplace=True)

    # Get the week columns
    week_cols = [col for col in df.columns if col.startswith('Week')]

    # Melt the dataframe
    melted_df = df.melt(
        id_vars=['Name', 'Project ID', 'Financial Year', 'Quarter'],
        value_vars=week_cols,
        var_name='Week',
        value_name='Actual Hrs'
    )

    # Clean up the 'Week' column
    melted_df['Week'] = melted_df['Week'].str.extract(r'Week (\d+)').astype(int)

    # Convert 'Actual Hrs' to numeric, coercing errors to NaN, then fill with 0
    melted_df['Actual Hrs'] = pd.to_numeric(melted_df['Actual Hrs'], errors='coerce').fillna(0)

    # Add dummy columns that existed in the old melted_df for compatibility
    melted_df['Overtime'] = 0.0
    melted_df['Time Card'] = 'N/A'
    melted_df['Sick Leave'] = 0
    melted_df['Annual Leave'] = 0
    melted_df['Onsite Days'] = 0
    melted_df['Email'] = 'N/A' # Add a dummy email column
    melted_df['Id'] = range(len(melted_df)) # Add a dummy Id column
    melted_df['Start time'] = pd.NaT
    melted_df['Completion time'] = pd.NaT

    return melted_df

def create_weekly_tables(melted_df):
    """Create and store tables for each week's utilization data"""
    weekly_tables = {}
    
    # Get all available weeks
    available_weeks = sorted(melted_df['Week'].unique())
    
    for week in available_weeks:
        # Get data for this week
        week_data = melted_df[melted_df['Week'] == week].copy()
        
        # Clean overtime values
        week_data['Overtime'] = week_data['Overtime'].apply(clean_overtime_value)
        
        # Calculate weekly utilization for each employee
        weekly_util = week_data.groupby('Name').agg({
            'Actual Hrs': 'sum',
            'Project ID': lambda x: list(set(x)),  # List of unique projects
            'Overtime': 'sum'  # Now we can safely sum the cleaned overtime values
        }).reset_index()
        
        # Add utilization status
        weekly_util['Status'] = weekly_util['Actual Hrs'].apply(get_utilization_status)
        weekly_util['Status_Color'] = weekly_util['Status'].apply(get_status_color)
        
        # Add project details
        weekly_util['Project_Details'] = weekly_util.apply(
            lambda row: [
                {
                    'Project_ID': proj,
                    'Hours': week_data[
                        (week_data['Name'] == row['Name']) & 
                        (week_data['Project ID'] == proj)
                    ]['Actual Hrs'].sum()
                }
                for proj in row['Project ID']
            ],
            axis=1
        )
        
        # Format the table for display
        weekly_util['Projects'] = weekly_util['Project_Details'].apply(
            lambda x: '\n'.join([f"{p['Project_ID']}: {p['Hours']:.1f}hrs" for p in x])
        )
        
        # Store the table
        weekly_tables[week] = {
            'data': weekly_util,
            'summary': {
                'total_employees': len(weekly_util),
                'under_utilized': len(weekly_util[weekly_util['Status'] == 'Under-Utilized']),
                'normal': len(weekly_util[weekly_util['Status'] == 'Normal']),
                'over_utilized': len(weekly_util[weekly_util['Status'] == 'Over-Utilized']),
                'total_hours': weekly_util['Actual Hrs'].sum(),
                'avg_hours': weekly_util['Actual Hrs'].mean(),
                'total_overtime': weekly_util['Overtime'].sum()
            }
        }
    
    return weekly_tables

def generate_data_context(melted_df, weekly_tables):
    """Generate a context string with key information about the data"""
    # Get available weeks
    available_weeks = sorted(melted_df['Week'].unique())
    weeks_str = ", ".join([f"Week {week}" for week in available_weeks])
    
    # Generate weekly summaries
    weekly_summaries = []
    for week, table in weekly_tables.items():
        summary = table['summary']
        under_utilized = table['data'][table['data']['Status'] == 'Under-Utilized']
        over_utilized = table['data'][table['data']['Status'] == 'Over-Utilized']
        
        weekly_summary = f"""
        Week {week} Summary:
        - Total Employees: {summary['total_employees']}
        - Under-Utilized: {summary['under_utilized']} employees
        - Normal Utilization: {summary['normal']} employees
        - Over-Utilized: {summary['over_utilized']} employees
        - Total Hours: {summary['total_hours']:.1f}
        - Average Hours: {summary['avg_hours']:.1f}
        - Total Overtime: {summary['total_overtime']:.1f}
        
        Under-Utilized Employees:
        {chr(10).join([f"- {row['Name']}: {row['Actual Hrs']:.1f} hours" for _, row in under_utilized.iterrows()])}
        
        Over-Utilized Employees:
        {chr(10).join([f"- {row['Name']}: {row['Actual Hrs']:.1f} hours" for _, row in over_utilized.iterrows()])}
        """
        weekly_summaries.append(weekly_summary)
    
    context = f"""
    This is an employee utilization dashboard with the following information:
    
    Available Weeks: {weeks_str}
    Total Employees: {melted_df['Name'].nunique()}
    Total Projects: {melted_df['Project ID'].nunique()}
    Standard Weekly Hours: {STANDARD_WEEKLY_HOURS}
    
    Utilization Categories:
    - Under-Utilized: < {STANDARD_WEEKLY_HOURS * NORMAL_UTILIZATION_MIN} hours
    - Normal: {STANDARD_WEEKLY_HOURS * NORMAL_UTILIZATION_MIN} to {STANDARD_WEEKLY_HOURS} hours
    - Over-Utilized: > {STANDARD_WEEKLY_HOURS} hours
    
    Weekly Summaries:
    {chr(10).join(weekly_summaries)}
    
    IMPORTANT: When answering questions:
    1. Use ONLY the actual data provided above
    2. Do not make up or infer employee names or numbers
    3. If asked about specific employees, verify they exist in the data
    4. For utilization analysis, use the actual hours from the data
    5. Always include specific numbers and percentages when available
    6. If data is not available for a specific query, state that clearly
    7. For weekly questions, use the specific weekly summary provided
    8. Remember that utilization is calculated per week
    9. Only use weeks that are listed in the Available Weeks section
    10. If asked about a week not in the Available Weeks list, state that the data is not available for that week
    """
    return context

csv_path = 'Anonymized_Employee_Utilization.csv'
melted_df = load_and_process_data(csv_path)


st.title("Employee Project Utilization Dashboard")

# Constants for utilization calculation
STANDARD_WEEKLY_HOURS = 40
NORMAL_UTILIZATION_MIN = 0.8  # 80% of standard hours
NORMAL_UTILIZATION_MAX = 1.0  # 100% of standard hours

# Function to determine utilization status
def get_utilization_status(hours):
    if pd.isna(hours):
        return "No Data"
    utilization = hours / STANDARD_WEEKLY_HOURS
    if utilization < NORMAL_UTILIZATION_MIN:
        return "Under-Utilized"
    elif utilization > NORMAL_UTILIZATION_MAX:
        return "Over-Utilized"
    else:
        return "Normal"

# Function to get status color
def get_status_color(status):
    if status == "Under-Utilized":
        return "red"
    elif status == "Over-Utilized":
        return "orange"
    elif status == "Normal":
        return "green"
    else:
        return "gray"

# Create weekly tables
weekly_tables = create_weekly_tables(melted_df)

# Store weekly tables in session state for persistence
if 'weekly_tables' not in st.session_state:
    st.session_state.weekly_tables = weekly_tables

# Original Team Dashboard
st.header("Original Team Utilization Overview")
team_heatmap = melted_df.pivot_table(index='Name', columns='Project ID', values='Actual Hrs', aggfunc='sum', fill_value=0)
st.dataframe(team_heatmap)
st.write("Team Utilization Heatmap (sum of hours):")
st.dataframe(team_heatmap.style.background_gradient(cmap='YlOrRd', axis=None))

# New Weekly Utilization Dashboard
st.header("Weekly Team Utilization Dashboard")

# Create weekly summary
weekly_summary = melted_df.groupby(['Name', 'Week'])['Actual Hrs'].sum().reset_index()
weekly_summary['Status'] = weekly_summary['Actual Hrs'].apply(get_utilization_status)
weekly_summary['Status_Color'] = weekly_summary['Status'].apply(get_status_color)

# Create weekly table with status
weekly_table = weekly_summary.pivot_table(
    index='Name',
    columns='Week',
    values='Actual Hrs',
    aggfunc='sum',
    fill_value=0
)

# Rename columns to match actual weeks
weekly_table.columns = [f'Week {i}' for i in sorted(weekly_summary['Week'].unique())]

# Function to style the weekly table
def style_weekly_table(df):
    def highlight_cell(val):
        status = get_utilization_status(val)
        if status == "Under-Utilized":
            return 'background-color: #ffcdd2'  # Light red
        elif status == "Over-Utilized":
            return 'background-color: #ffe0b2'  # Light orange
        elif status == "Normal":
            return 'background-color: #c8e6c9'  # Light green
        else:
            return 'background-color: #e0e0e0'  # Light gray
    
    styled_df = df.style.map(highlight_cell)
    styled_df = styled_df.format('{:.1f}hrs')
    styled_df = styled_df.set_properties(**{
        'text-align': 'center',
        'padding': '10px',
        'border': '1px solid #ddd'
    }).set_table_styles([
        {'selector': 'th', 'props': [('background-color', '#f0f0f0'), ('padding', '10px')]},
        {'selector': 'td', 'props': [('max-width', '100px')]}
    ])
    return styled_df

st.write("Weekly Hours with Utilization Status:")
st.dataframe(style_weekly_table(weekly_table))

# Add a legend for the utilization status
st.markdown("""
**Utilization Status Legend:**
- 🟢 Green: Normal Utilization (32-40 hours)
- 🟠 Orange: Over-Utilized (> 40 hours)
- 🔴 Red: Under-Utilized (< 32 hours)
- ⚫ Gray: No Data
""")

# --- NEW: Custom Heatmap for Selected People ---
st.subheader("Custom Weekly Utilization Heatmap (Select People)")
all_people = sorted(melted_df['Name'].unique())
selected_people = st.multiselect(
    "Select people to display on the heatmap:",
    all_people,
    default=all_people[:min(5, len(all_people))],
    key="custom_heatmap_people"
)
if selected_people:
    filtered_weekly_table = weekly_table.loc[weekly_table.index.isin(selected_people)]
    st.write("Heatmap for Selected People:")
    st.dataframe(style_weekly_table(filtered_weekly_table))
else:
    st.info("Please select at least one person to display the heatmap.")

# --- END NEW SECTION ---

# New Employee Weekly Project Details Dashboard
st.header("Employee Weekly Project Details")

# Employee selector
employee = st.selectbox(
    "Select Employee",
    sorted(melted_df['Name'].unique())
)

if employee:
    # Filter data for selected employee
    emp_data = melted_df[melted_df['Name'] == employee]
    
    # Create a function to generate cell content with project details
    def create_cell_content(week_data):
        if week_data.empty:
            return "No data"
        
        total_hours = week_data['Actual Hrs'].sum()
        status = get_utilization_status(total_hours)
        
        # Create project details
        projects = []
        for _, row in week_data.iterrows():
            overtime = f" (OT: {row['Overtime']}hrs)" if pd.notna(row['Overtime']) and float(row['Overtime']) > 0 else ""
            projects.append(f"{row['Project ID']}: {row['Actual Hrs']:.1f}hrs{overtime}")
        
        # Format cell content
        cell_content = f"Total: {total_hours:.1f}hrs\nStatus: {status}\n\nProjects:\n" + "\n".join(projects)
        return cell_content, total_hours, status

    # Create a styled heatmap table
    def create_heatmap_table(emp_data):
        # Get all weeks
        weeks = sorted(emp_data['Week'].unique())
        
        # Create a DataFrame for the heatmap
        heatmap_data = []
        for week in weeks:
            week_data = emp_data[emp_data['Week'] == week]
            cell_content, total_hours, status = create_cell_content(week_data)
            
            heatmap_data.append({
                'Week': f'Week {week}',
                'Total Hours': total_hours,
                'Status': status,
                'Details': cell_content
            })
        
        # Convert to DataFrame
        heatmap_df = pd.DataFrame(heatmap_data)
        
        # Create custom colorscale with normalized values
        colorscale = [
            [0, '#ffcdd2'],                    # Under-utilized (red) at 0%
            [0.8, '#ffcdd2'],                  # Under-utilized (red) at 80%
            [0.8, '#c8e6c9'],                  # Normal (green) at 80%
            [1.0, '#c8e6c9'],                  # Normal (green) at 100%
            [1.0, '#ffe0b2'],                  # Over-utilized (orange) at 100%
            [1.2, '#ffe0b2']                   # Over-utilized (orange) at 120%
        ]
        
        # Normalize the colorscale values to be between 0 and 1
        normalized_colorscale = [[v/1.2, c] for v, c in colorscale]
        
        # Create the heatmap
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_df['Total Hours'].values.reshape(1, -1) / STANDARD_WEEKLY_HOURS,  # Convert to utilization ratio
            x=heatmap_df['Week'].values,
            y=['Hours'],
            text=heatmap_df['Details'].values,
            hoverinfo='text',
            colorscale=normalized_colorscale,
            zmin=0,
            zmax=1.2,  # 120% of standard hours
            showscale=True,
            colorbar=dict(
                title='Utilization',
                ticktext=['0%', '80%', '100%', '120%'],
                tickvals=[0, 0.8, 1.0, 1.2],
                ticks='outside'
            )
        ))
        
        # Add reference lines
        fig.add_hline(y=0.5, line_dash="dash", line_color="blue", 
                     annotation_text="80% (32hrs)", annotation_position="right")
        fig.add_hline(y=0.5, line_dash="dash", line_color="red", 
                     annotation_text="100% (40hrs)", annotation_position="right")
        
        # Update layout
        fig.update_layout(
            title=f"Weekly Utilization Heatmap for {employee}",
            xaxis_title="Week",
            yaxis_title="",
            height=200,
            showlegend=False
        )
        
        return fig, heatmap_df

    # Display the heatmap
    st.write("Weekly Utilization Heatmap with Project Details:")
    heatmap_fig, heatmap_df = create_heatmap_table(emp_data)
    st.plotly_chart(heatmap_fig, use_container_width=True)
    
    # Add a legend for the utilization status
    st.markdown("""
    **Utilization Status Legend:**
    - 🟢 Green: Normal Utilization (32-40 hours)
    - 🟠 Orange: Over-Utilized (> 40 hours)
    - 🔴 Red: Under-Utilized (< 32 hours)
    - ⚫ Gray: No Data
    """)

    # Add Weekly Project Breakdown Bar Chart
    st.subheader("Weekly Project Breakdown")
    
    # Create a figure for the bar chart
    fig = go.Figure()
    
    # Get all weeks and projects
    weeks = sorted(emp_data['Week'].unique())
    
    # Create a color palette for projects
    unique_projects = emp_data['Project ID'].unique()
    colors = px.colors.qualitative.Set3[:len(unique_projects)]
    project_colors = dict(zip(unique_projects, colors))
    
    # First aggregate the data to remove duplicates
    aggregated_data = emp_data.groupby(['Week', 'Project ID']).agg({
        'Actual Hrs': 'sum',
        'Overtime': lambda x: float(x.sum()) if pd.notna(x).any() and str(x.sum()).strip() != '' else 0
    }).reset_index()
    
    # Add bars for each project in each week
    for week in weeks:
        week_data = aggregated_data[aggregated_data['Week'] == week]
        
        # Sort projects by hours to stack them in order
        week_data = week_data.sort_values('Actual Hrs', ascending=True)
        
        # Add a bar for each project
        for _, row in week_data.iterrows():
            project = row['Project ID']
            hours = row['Actual Hrs']
            
            # Safely handle overtime value
            try:
                overtime = float(row['Overtime']) if pd.notna(row['Overtime']) and str(row['Overtime']).strip() != '' else 0
            except (ValueError, TypeError):
                overtime = 0
            
            # Create hover text
            hover_text = f"Project: {project}<br>Hours: {hours:.1f}"
            if overtime > 0:
                hover_text += f"<br>Overtime: {overtime:.1f}"
            
            fig.add_trace(go.Bar(
                x=[f'Week {week}'],
                y=[hours],
                name=project,
                text=f"{hours:.1f}hrs",
                textposition='inside',
                hovertext=hover_text,
                hoverinfo='text',
                marker_color=project_colors[project],
                showlegend=True if week == weeks[0] else False  # Show legend only for first week
            ))
    
    # Update layout
    fig.update_layout(
        title=f"Weekly Project Hours for {employee}",
        barmode='stack',
        xaxis_title="Week",
        yaxis_title="Hours",
        height=400,
        showlegend=True,
        legend_title="Projects",
        hovermode='x unified'
    )
    
    # Add reference lines for utilization thresholds
    fig.add_hline(y=STANDARD_WEEKLY_HOURS * NORMAL_UTILIZATION_MIN, 
                 line_dash="dash", 
                 line_color="blue",
                 annotation_text="80% (32hrs)",
                 annotation_position="right")
    fig.add_hline(y=STANDARD_WEEKLY_HOURS,
                 line_dash="dash",
                 line_color="red",
                 annotation_text="100% (40hrs)",
                 annotation_position="right")
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=True)

# Original Individual Employee Dashboard
st.header("Individual Employee Dashboard")
if not melted_df.empty and 'Name' in melted_df.columns:
    employee = st.selectbox("Select Employee for Detailed View", ['All'] + list(melted_df['Name'].dropna().unique()))
    if employee == 'All':
        emp_df = melted_df
    else:
        emp_df = melted_df[melted_df['Name'] == employee]

    st.write(f"Showing data for: {employee}")
    st.dataframe(emp_df)

    if not emp_df.empty:
        emp_heatmap = emp_df.pivot_table(index='Project ID', values='Actual Hrs', aggfunc='sum')
        st.write("Actual Hours per Project (Bar Chart):")
        st.bar_chart(emp_heatmap)
else:
    st.write("No data available or 'Name' column missing in melted_df.")

# Add Graph-Based Utilization Analysis Section
st.header("Graph-Based Utilization Analysis")

# Initialize Neo4j connection
try:
    util_graph = UtilizationGraph()
    util_graph.driver.verify_connectivity()
    st.success("✅ Successfully connected to Neo4j database")
    
    # Get available weeks from Neo4j
    available_weeks = util_graph.get_available_weeks()
    if available_weeks:
        st.sidebar.markdown("### Available Weeks")
        st.sidebar.write(f"Weeks: {', '.join(map(str, available_weeks))}")
        
        # Add week selector
        selected_week = st.sidebar.selectbox(
            "Select Week for Analysis",
            available_weeks,
            format_func=lambda x: f"Week {x}",
            key="week_selector"
        )
        
        # Show under-utilized employees for selected week
        if selected_week:
            st.subheader(f"Under-Utilized Employees in Week {selected_week}")
            under_utilized = util_graph.get_under_utilized_employees(selected_week)
            if under_utilized:
                for emp in under_utilized:
                    st.write(f"- {emp['employee']}: {emp['hours']:.1f} hours")
            else:
                st.info("No under-utilized employees found for this week")
    
    # Add AI Assistant for Graph Analysis
    st.subheader("Ask questions about utilization patterns")
    
    # Display example questions
    st.markdown("""
    Here are some example questions you can ask:
    
    **Utilization Analysis:**
    - Who are the most utilized employees?
    - Which employees are under-utilized in Week 5?
    - What's the average utilization across all weeks?
    - Show me employees with consistent utilization
    
    **Project Analysis:**
    - Which projects have the most overtime?
    - What's the distribution of hours across projects?
    - Which projects are taking the most resources?
    
    **Trend Analysis:**
    - Are there any utilization trends over the weeks?
    - Which employees show improving utilization?
    - Are there any concerning patterns in the data?
    
    **Resource Planning:**
    - Who might need additional project assignments?
    - Which projects are under-resourced?
    - What's the optimal resource allocation?
    """)
    
    # Initialize chat history if not exists
    if 'graph_chat_history' not in st.session_state:
        st.session_state.graph_chat_history = []
    
    # Chat input
    user_query = st.text_input(
        "Your question:",
        key="graph_query_input",
        placeholder="Type your question here... (e.g., 'Who are the most utilized employees?')"
    )
    
    if user_query:
        # Add user message to chat history
        st.session_state.graph_chat_history.append({"role": "user", "content": user_query})
        
        # Get AI response
        try:
            response = util_graph.analyze_utilization(user_query)
            st.session_state.graph_chat_history.append({"role": "assistant", "content": response})
        except Exception as e:
            st.error(f"Error getting AI response: {str(e)}")
            st.session_state.graph_chat_history.append({
                "role": "assistant",
                "content": "I apologize, but I encountered an error while analyzing the data. Please try rephrasing your question."
            })
    
    # Display chat history (latest at the top for better demo visibility)
    for message in reversed(st.session_state.graph_chat_history):
        if message["role"] == "user":
            st.markdown(f"**👤 You:** {message['content']}")
        else:
            st.markdown(f"**🤖 Assistant:** {message['content']}")
    
    # Add a clear chat button with unique key
    if st.button("Clear Chat History", key="clear_graph_chat"):
        if st.session_state.graph_chat_history:
            st.session_state.graph_chat_history = []
            st.rerun()
        else:
            st.info("Chat history is already empty")
            
except Exception as e:
    st.error(f"Error connecting to Neo4j database: {str(e)}")
    st.info("Please ensure the Neo4j database is running and accessible.")
finally:
    if 'util_graph' in locals():
        util_graph.close()