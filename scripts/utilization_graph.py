
"""
Employee Utilization Graph Database Integration
Author: Your Name
Date: 2024
Version: 1.0
Description: Graph database integration for employee utilization analysis using Neo4j and Ollama
"""
import os
import json
from datetime import datetime
import pandas as pd
from neo4j import GraphDatabase
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_neo4j import Neo4jGraph
from langchain_community.vectorstores import Neo4jVector
# Configuration
import os

NEO4J_CONFIG = {
    "url": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    "username": os.getenv("NEO4J_USER", "neo4j"),
    "password": os.getenv("NEO4J_PASSWORD", "utilization123"),
    "database": "neo4j"  # Use default database instead of custom "utilization" database
}
OLLAMA_CONFIG = {
    "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    "model": "mistral:latest",
    "embedding_model": "nomic-embed-text:latest"
}
class UtilizationGraph:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_CONFIG["url"],
            auth=(NEO4J_CONFIG["username"], NEO4J_CONFIG["password"])
        )
        
        # Initialize Neo4jGraph with error handling
        try:
            self.graph = Neo4jGraph(
                url=NEO4J_CONFIG["url"],
                username=NEO4J_CONFIG["username"],
                password=NEO4J_CONFIG["password"]
            )
        except Exception as e:
            print(f"Warning: Could not initialize Neo4jGraph: {e}")
            self.graph = None
        
        # Initialize Ollama components with error handling
        try:
            self.embeddings = OllamaEmbeddings(
                model=OLLAMA_CONFIG["embedding_model"],
                base_url=OLLAMA_CONFIG["base_url"]
            )
        except Exception as e:
            print(f"Warning: Could not initialize OllamaEmbeddings: {e}")
            self.embeddings = None
            
        try:
            self.llm = ChatOllama(
                model=OLLAMA_CONFIG["model"],
                base_url=OLLAMA_CONFIG["base_url"]
            )
        except Exception as e:
            print(f"Warning: Could not initialize ChatOllama: {e}")
            self.llm = None
        # Comment out RAG vectorstore setup for now
        # self.vectorstore = Neo4jVector.from_existing_index(
        #     url=NEO4J_CONFIG["url"],
        #     username=NEO4J_CONFIG["username"],
        #     password=NEO4J_CONFIG["password"],
        #     index_name="document_embedding",
        #     embedding=self.embeddings
        # )
    def initialize_database(self):
        """Initialize the database with constraints and indexes"""
        with self.driver.session() as session:
            # Create constraints
            session.run("""
                CREATE CONSTRAINT employee_name IF NOT EXISTS
                FOR (e:Employee) REQUIRE e.name IS UNIQUE
            """)
            session.run("""
                CREATE CONSTRAINT project_id IF NOT EXISTS
                FOR (p:Project) REQUIRE p.project_id IS UNIQUE
            """)
            
            # Comment out vector indexes for now
            # session.run("""
            #     CREATE VECTOR INDEX employee_embedding IF NOT EXISTS
            #     FOR (e:Employee) ON (e.embedding)
            #     OPTIONS {indexConfig: {
            #         `vector.dimensions`: 768,
            #         `vector.similarity_function`: 'cosine'
            #     }}
            # """)
            
            # session.run("""
            #     CREATE VECTOR INDEX project_embedding IF NOT EXISTS
            #     FOR (p:Project) ON (p.embedding)
            #     OPTIONS {indexConfig: {
            #         `vector.dimensions`: 768,
            #         `vector.similarity_function`: 'cosine'
            #     }}
            # """)
    def verify_data_loading(self):
        """Verify that data was loaded correctly"""
        with self.driver.session() as session:
            # Check employee count
            employee_count = session.run("MATCH (e:Employee) RETURN count(e) as count").single()["count"]
            print(f"\nFound {employee_count} employees in the database")
            
            # Check project count
            project_count = session.run("MATCH (p:Project) RETURN count(p) as count").single()["count"]
            print(f"Found {project_count} projects in the database")
            
            # Check relationship count
            rel_count = session.run("MATCH ()-[r:WORKS_ON]->() RETURN count(r) as count").single()["count"]
            print(f"Found {rel_count} WORKS_ON relationships")
            
            # Sample some data
            print("\nSample data:")
            result = session.run("""
                MATCH (e:Employee)-[w:WORKS_ON]->(p:Project)
                RETURN e.name as employee, p.project_id as project, 
                       w.hours as hours, w.week as week, w.overtime as overtime
                LIMIT 5
            """)
            for record in result:
                print(f"Employee: {record['employee']}, Project: {record['project']}, "
                      f"Hours: {record['hours']}, Week: {record['week']}, "
                      f"Overtime: {record['overtime']}")
    def load_utilization_data(self, csv_path):
        """Load utilization data from the new CSV format into Neo4j"""
        print(f"\nLoading data from {csv_path}...")
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()
        print(f"Read {len(df)} rows from CSV")
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
        # Clean up the 'Week' column to get just the number
        melted_df['Week'] = melted_df['Week'].str.extract(r'Week (\d+)').astype(int)
        # Convert 'Actual Hrs' to numeric, coercing errors to NaN, then fill with 0
        melted_df['Actual Hrs'] = pd.to_numeric(melted_df['Actual Hrs'], errors='coerce').fillna(0)
        # Filter out rows where hours are 0
        melted_df = melted_df[melted_df['Actual Hrs'] > 0].dropna(subset=['Name', 'Project ID'])
        print(f"\nAfter processing, {len(melted_df)} valid records to load.")
        with self.driver.session() as session:
            # Clear existing data
            session.run("MATCH (n) DETACH DELETE n")
            print("Cleared existing data")
            # Create nodes and relationships
            for _, row in melted_df.iterrows():
                # Create Employee node
                session.run("MERGE (e:Employee {name: $name})", name=row['Name'])
                # Create Project node
                session.run("""
                    MERGE (p:Project {project_id: $project_id})
                    ON CREATE SET p.description = $project_id
                """, project_id=row['Project ID'])
                # Create WORKS_ON relationship
                session.run("""
                    MATCH (e:Employee {name: $name})
                    MATCH (p:Project {project_id: $project_id})
                    MERGE (e)-[w:WORKS_ON {week: $week}]->(p)
                    SET w.hours = $hours,
                        w.overtime = 0
                """, name=row['Name'], project_id=row['Project ID'], hours=row['Actual Hrs'], week=row['Week'])
        
        print("\nData loading complete.")
    def query_utilization(self, query_text):
        """Query the utilization data using natural language"""
        # For now, we'll use a simpler query approach without vector similarity
        with self.driver.session() as session:
            # Basic query to get utilization data
            result = session.run("""
                MATCH (e:Employee)-[w:WORKS_ON]->(p:Project)
                WITH e, p, w, 
                     sum(w.hours) as total_hours,
                     sum(w.overtime) as total_overtime
                RETURN e.name AS employee,
                       p.project_id AS project,
                       total_hours AS hours,
                       w.week AS week,
                       total_overtime AS overtime
                ORDER BY total_hours DESC
                LIMIT 10
            """)
            
            return [dict(record) for record in result]
    def analyze_utilization(self, query_text):
        """Analyze utilization patterns using the LLM"""
        try:
            # Check if the query is about a specific week
            import re
            week_match = re.search(r'week\s+(\d+)', query_text.lower())
            
            if week_match:
                week = int(week_match.group(1))
                # Get data for the specific week
                with self.driver.session() as session:
                    # First verify if the week exists and get exact data
                    week_data = session.run("""
                        MATCH (e:Employee)-[w:WORKS_ON]->(p:Project)
                        WHERE w.week = $week
                        WITH e, 
                             sum(w.hours) as total_hours,
                             collect({
                                 project: p.project_id,
                                 description: p.description,
                                 hours: w.hours
                             }) as projects
                        RETURN e.name as employee,
                               total_hours as hours,
                               projects as project_details
                        ORDER BY total_hours DESC
                    """, {"week": week})
                    
                    data = [dict(record) for record in week_data]
                    
                    if not data:
                        # Get available weeks to show in the response
                        available_weeks = session.run("""
                            MATCH (e:Employee)-[w:WORKS_ON]->(p:Project)
                            RETURN DISTINCT w.week as week
                            ORDER BY w.week
                        """)
                        weeks = [str(record["week"]) for record in available_weeks]
                        return f"I apologize, but there is no data available for Week {week} in the database. Available weeks are: {', '.join(weeks)}"
                    
                    # Determine what type of analysis is requested
                    query_lower = query_text.lower()
                    is_most_utilized = any(word in query_lower for word in ['most utilized', 'highest utilization', 'top utilized'])
                    is_least_utilized = any(word in query_lower for word in ['least utilized', 'lowest utilization', 'under utilized', 'under-utilized'])
                    
                    # Prepare response based on query type
                    if is_most_utilized:
                        # Show most utilized employees (top 5)
                        top_utilized = data[:5]
                        response = f"## 📊 Most Utilized Employees in Week {week}\n\n"
                        
                        for i, emp in enumerate(top_utilized, 1):
                            response += f"**{i}. {emp['employee']}**: {emp['hours']:.1f} hours\n"
                            response += "   **Projects:**\n"
                            for proj in emp['project_details']:
                                response += f"   • {proj['project']}: {proj['hours']:.1f} hours\n"
                            response += "\n"
                        
                        # Add summary
                        total_employees = len(data)
                        avg_hours = sum(emp['hours'] for emp in data) / total_employees if total_employees > 0 else 0
                        response += f"**Summary:**\n"
                        response += f"• Total employees in Week {week}: {total_employees}\n"
                        response += f"• Average hours: {avg_hours:.1f}\n"
                        response += f"• Highest utilization: {top_utilized[0]['employee']} with {top_utilized[0]['hours']:.1f} hours\n"
                        
                    elif is_least_utilized:
                        # Show under-utilized employees
                        under_utilized = [emp for emp in data if emp['hours'] < 32]
                        response = f"## 📊 Under-Utilized Employees in Week {week}\n\n"
                        
                        if under_utilized:
                            for emp in under_utilized:
                                response += f"**{emp['employee']}**: {emp['hours']:.1f} hours\n"
                                response += "   **Projects:**\n"
                                for proj in emp['project_details']:
                                    response += f"   • {proj['project']}: {proj['hours']:.1f} hours\n"
                                response += "\n"
                        else:
                            response += f"No under-utilized employees found in Week {week}.\n"
                            response += "All employees are working 32 hours or more.\n\n"
                        
                        # Add summary
                        total_employees = len(data)
                        avg_hours = sum(emp['hours'] for emp in data) / total_employees if total_employees > 0 else 0
                        response += f"**Summary:**\n"
                        response += f"• Total employees: {total_employees}\n"
                        response += f"• Average hours: {avg_hours:.1f}\n"
                        response += f"• Under-utilized employees: {len(under_utilized)}\n"
                        
                    else:
                        # Show general analysis with both top and bottom
                        top_utilized = data[:3]
                        under_utilized = [emp for emp in data if emp['hours'] < 32][:3]
                        
                        response = f"## 📊 Week {week} Utilization Analysis\n\n"
                        
                        response += "**Top 3 Most Utilized:**\n"
                        for i, emp in enumerate(top_utilized, 1):
                            response += f"{i}. {emp['employee']}: {emp['hours']:.1f} hours\n"
                        
                        response += f"\n**Under-Utilized (< 32 hours):**\n"
                        if under_utilized:
                            for emp in under_utilized:
                                response += f"• {emp['employee']}: {emp['hours']:.1f} hours\n"
                        else:
                            response += "• None found\n"
                        
                        # Add summary
                        total_employees = len(data)
                        avg_hours = sum(emp['hours'] for emp in data) / total_employees if total_employees > 0 else 0
                        response += f"\n**Summary:**\n"
                        response += f"• Total employees: {total_employees}\n"
                        response += f"• Average hours: {avg_hours:.1f}\n"
                        response += f"• Highest: {top_utilized[0]['employee']} ({top_utilized[0]['hours']:.1f} hours)\n"
                        if under_utilized:
                            response += f"• Lowest: {under_utilized[0]['employee']} ({under_utilized[0]['hours']:.1f} hours)\n"
                    
                    return response
            else:
                # Use the general query approach for non-week-specific queries
                data = self.query_utilization(query_text)
                
                # Get more comprehensive data for analysis
                with self.driver.session() as session:
                    # Get total employee count
                    employee_count = session.run("MATCH (e:Employee) RETURN count(e) as count").single()["count"]
                    
                    # Get total project count
                    project_count = session.run("MATCH (p:Project) RETURN count(p) as count").single()["count"]
                    
                    # Get average hours per week per employee
                    avg_hours_result = session.run("""
                        MATCH (e:Employee)-[w:WORKS_ON]->(p:Project)
                        WITH e, sum(w.hours) as total_hours, count(DISTINCT w.week) as weeks_worked
                        WHERE weeks_worked > 0
                        WITH e, total_hours, weeks_worked, total_hours/weeks_worked as avg_weekly_hours
                        RETURN avg(avg_weekly_hours) as avg_hours
                    """).single()
                    avg_hours = avg_hours_result["avg_hours"] if avg_hours_result["avg_hours"] else 0
                    
                    # Get highest utilization (average per week)
                    highest_util = session.run("""
                        MATCH (e:Employee)-[w:WORKS_ON]->(p:Project)
                        WITH e, sum(w.hours) as total_hours, count(DISTINCT w.week) as weeks_worked
                        WHERE weeks_worked > 0
                        WITH e, total_hours, weeks_worked, total_hours/weeks_worked as avg_weekly_hours
                        ORDER BY avg_weekly_hours DESC
                        LIMIT 1
                        RETURN e.name as employee, avg_weekly_hours as hours
                    """).single()
                    
                    # Get lowest utilization (average per week)
                    lowest_util = session.run("""
                        MATCH (e:Employee)-[w:WORKS_ON]->(p:Project)
                        WITH e, sum(w.hours) as total_hours, count(DISTINCT w.week) as weeks_worked
                        WHERE weeks_worked > 0
                        WITH e, total_hours, weeks_worked, total_hours/weeks_worked as avg_weekly_hours
                        ORDER BY avg_weekly_hours ASC
                        LIMIT 1
                        RETURN e.name as employee, avg_weekly_hours as hours
                    """).single()
                    
                    # Get employees with low utilization (< 32 hours/week average)
                    low_utilization_employees = session.run("""
                        MATCH (e:Employee)-[w:WORKS_ON]->(p:Project)
                        WITH e, sum(w.hours) as total_hours, count(DISTINCT w.week) as weeks_worked
                        WHERE weeks_worked > 0
                        WITH e, total_hours, weeks_worked, total_hours/weeks_worked as avg_weekly_hours
                        WHERE avg_weekly_hours < 32
                        RETURN e.name as employee, avg_weekly_hours as hours
                        ORDER BY avg_weekly_hours ASC
                    """)
                    low_util_employees = [dict(record) for record in low_utilization_employees]
                
                # Prepare context for the LLM with accurate data
                highest_employee = highest_util['employee'] if highest_util else 'N/A'
                highest_hours = f"{highest_util['hours']:.1f}" if highest_util and highest_util['hours'] else '0'
                lowest_employee = lowest_util['employee'] if lowest_util else 'N/A'
                lowest_hours = f"{lowest_util['hours']:.1f}" if lowest_util and lowest_util['hours'] else '0'
                
                # Format low utilization employees for context
                low_util_text = ""
                if low_util_employees:
                    low_util_text = "\nEmployees with low utilization (< 32 hours/week average):\n"
                    for emp in low_util_employees[:5]:  # Show top 5
                        low_util_text += f"- {emp['employee']}: {emp['hours']:.1f} hours/week average\n"
                
                context = f"""
                Utilization Data (from Neo4j database):
                {json.dumps(data, indent=2)}
                
                Database Statistics:
                - Total Employees: {employee_count}
                - Total Projects: {project_count}
                - Average Hours per Week per Employee: {avg_hours:.1f}
                - Highest Utilization (weekly average): {highest_employee} with {highest_hours} hours/week
                - Lowest Utilization (weekly average): {lowest_employee} with {lowest_hours} hours/week
                {low_util_text}
                
                Analysis Guidelines:
                1. Focus on utilization patterns and trends
                2. Identify under/over utilization (consider 40 hours/week as standard)
                3. Consider project distribution
                4. Look for overtime patterns
                5. Highlight any employees with significantly high or low utilization
                6. Use ONLY the data provided above
                7. Do not make assumptions about data not shown
                8. For "additional project assignments" questions, focus on employees with low utilization (< 32 hours/week average)
                9. All hours are calculated as weekly averages, not total hours across all weeks
                """
                
                # Get LLM analysis
                response = self.llm.invoke(f"""
                Based on the following utilization data, provide a precise analysis:
                
                {context}
                
                User Query: {query_text}
                
                Provide a clear, structured analysis following these rules:
                1. ONLY use the data provided above
                2. Use exact numbers from the data
                3. Do not make assumptions about data not shown
                4. Focus on patterns and trends in the actual data
                5. Provide specific recommendations based on the data
                6. For questions about additional assignments, identify employees with low utilization (< 32 hours/week)
                
                Format your response EXACTLY as follows (use proper line breaks and spacing):
                ## 📊 Key Findings
                • [List 3-4 key findings with specific numbers from the data - use weekly averages]
                ## 📈 Patterns & Trends
                • [List 2-3 specific patterns observed in the actual data]
                ## 💡 Recommendations
                • [List 2-3 actionable recommendations based on the data - focus on employees with < 32 hours/week average]
                ## 📋 Data Summary
                • Total Employees: {employee_count}
                • Total Projects: {project_count}
                • Average Hours per Week per Employee: {avg_hours:.1f}
                • Highest Utilization (weekly average): {highest_employee} with {highest_hours} hours/week
                • Lowest Utilization (weekly average): {lowest_employee} with {lowest_hours} hours/week
                """)
                
                # Clean up the response formatting
                cleaned_response = response.content.replace('\\n', '\n').replace('\n\n', '\n')
                
                # Add proper spacing and formatting
                formatted_response = f"""
{cleaned_response}
---
*Analysis generated by AI based on utilization data*
                """.strip()
                
                return formatted_response
        except Exception as e:
            return f"I apologize, but I encountered an error while analyzing the data: {str(e)}. Please try rephrasing your question or check if the database is properly connected."
    # def rag_query(self, query_text, k=3, min_score=0.2):
    #     """RAG: Retrieve relevant docs from Neo4j and answer with LLM.
    #     If no relevant docs (by similarity), let LLM answer as itself or return a fallback message.
    #     """
    #     # Get embedding for the query
    #     query_embedding = self.embeddings.embed_query(query_text)
    #     # Custom Cypher query for top-k similar docs with scores
    #     with self.driver.session() as session:
    #         cypher = """
    #         MATCH (d:Document)
    #         WITH d, gds.similarity.cosine(d.embedding, $query_embedding) AS score
    #         ORDER BY score DESC
    #         LIMIT $k
    #         RETURN d.text AS text, score
    #         """
    #         results = session.run(cypher, {"query_embedding": query_embedding, "k": k})
    #         docs_and_scores = [(record["text"], record["score"]) for record in results]
    #     # Filter by min_score
    #     relevant_docs = [text for text, score in docs_and_scores if score and score >= min_score]
    #     if not relevant_docs:
    #         # Out of domain: instruct LLM to refuse unrelated questions
    #         fallback_prompt = (
    #             f"You are an AI assistant for an employee utilization dashboard. "
    #             f"The user asked: '{query_text}'. "
    #             "If the question is NOT about employee utilization, projects, or resource allocation, "
    #             "politely respond: 'Sorry, I can only answer questions about employee utilization, projects, or resource allocation.' "
    #             "Do NOT answer any other type of question."
    #         )
    #         response = self.llm.invoke(fallback_prompt)
    #         return response.content
    #     # Otherwise, answer as usual with context
    #     context = "\n".join(relevant_docs)
    #     prompt = (
    #         f"Based on the following data, answer the user's question.\n\n"
    #         f"Data:\n{context}\n\nQuestion: {query_text}\nAnswer:"
    #     )
    #     response = self.llm.invoke(prompt)
    #     return response.content
    def get_available_weeks(self):
        """Get list of available weeks in the database"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Employee)-[w:WORKS_ON]->(p:Project)
                RETURN DISTINCT w.week as week
                ORDER BY w.week
            """)
            weeks = [record["week"] for record in result]
            return weeks
    def get_under_utilized_employees(self, week):
        """Get under-utilized employees for a specific week"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Employee)-[w:WORKS_ON]->(p:Project)
                WHERE w.week = $week
                WITH e, sum(w.hours) as total_hours
                WHERE total_hours < 32  // Under-utilized is less than 80% of 40 hours
                RETURN e.name as employee, total_hours as hours
                ORDER BY total_hours ASC
            """, {"week": week})
            return [dict(record) for record in result]
    def close(self):
        """Close the database connection"""
        self.driver.close()
# Example usage
if __name__ == "__main__":
    try:
        # Initialize the graph database
        util_graph = UtilizationGraph()
        util_graph.initialize_database()
        
        # Load data
        util_graph.load_utilization_data('Anonymized_Employee_Utilization.csv')
        
        # Verify data loading
        util_graph.verify_data_loading()
        
        # Example queries
        queries = [
            "Who are the most utilized employees?",
            "Which projects have the most overtime?",
            "Show me under-utilized employees in Week 5"
        ]
        
        for query in queries:
            print(f"\nQuery: {query}")
            analysis = util_graph.analyze_utilization(query)
            print(f"Analysis: {analysis}")
    finally:
        if 'util_graph' in locals():
            util_graph.close() 
