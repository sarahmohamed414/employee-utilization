# setup_graph_db.py
"""
Setup script for Neo4j utilization database
This script initializes the database and loads the utilization data
"""

import time  # Used for retry logic and waiting for Neo4j to be ready
from utilization_graph import UtilizationGraph  # Main class for all graph DB operations
import streamlit as st  # Used for Streamlit integration (if needed)


def wait_for_neo4j(max_retries=5, delay=5):
    """Wait for Neo4j to be ready before proceeding. Tries to connect several times."""
    print("Waiting for Neo4j to be ready...")
    for i in range(max_retries):
        try:
            util_graph = UtilizationGraph()  # Try to create a connection
            util_graph.driver.verify_connectivity()  # Check if DB is reachable
            print("✅ Neo4j is ready!")
            return util_graph
        except Exception as e:
            print(f"Attempt {i+1}/{max_retries}: Neo4j not ready yet... ({str(e)})")
            if i < max_retries - 1:
                time.sleep(delay)  # Wait before retrying
    raise Exception("Could not connect to Neo4j after multiple attempts")


def setup_database():
    """Initialize and load data into Neo4j. This sets up constraints, loads CSV, and tests queries."""
    try:
        # Wait for Neo4j to be ready
        util_graph = wait_for_neo4j()
        
        # Initialize database (constraints, indexes)
        print("Initializing database...")
        util_graph.initialize_database()
        print("✅ Database initialized!")
        
        # Load data from CSV into Neo4j
        print("Loading utilization data...")
        util_graph.load_utilization_data('Anonymized_Employee_Utilization.csv')
        print("✅ Data loaded successfully!")
        
        # Test the setup with sample queries
        print("\nTesting database with sample queries...")
        test_queries = [
            "Who are the most utilized employees?",
            "Which projects have the most overtime?"
        ]
        
        for query in test_queries:
            print(f"\nTesting query: {query}")
            try:
                result = util_graph.query_utilization(query)
                print(f"✅ Query successful! Found {len(result)} results")
            except Exception as e:
                print(f"❌ Query failed: {str(e)}")
        
        print("\n🎉 Setup completed successfully!")
        return util_graph
        
    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        raise
    finally:
        if 'util_graph' in locals():
            util_graph.close()  # Always close the DB connection


# def ingest_documents_for_rag(documents):
#     """Embed and store documents in Neo4j for RAG. Used to enable retrieval-augmented generation."""
#     from langchain_ollama import OllamaEmbeddings  # For generating embeddings
#     from langchain_neo4j import Neo4jVector  # For storing embeddings in Neo4j

#     embeddings = OllamaEmbeddings(
#         model="nomic-embed-text:latest",
#         base_url="http://localhost:11434"
#     )
#     vectorstore = Neo4jVector.from_existing_index(
#         url="bolt://localhost:7687",
#         username="neo4j",
#         password="utilization123",
#         index_name="document_embedding",
#         embedding=embeddings
#     )
#     print(f"Adding {len(documents)} documents to Neo4j vector index...")
#     vectorstore.add_texts(documents)  # Store the embedded documents
#     print("✅ Documents embedded and stored for RAG!")


if __name__ == "__main__":
    print("Starting Neo4j database setup...")
    setup_database()  # Run the main setup
    # Example: ingest documents for RAG (uncomment and provide your data)
    # docs = [
    #     "Omar Hassan worked on Project Alpha for 10 weeks.",
    #     "Laila Samir contributed to Project Beta and Project Gamma.",
    #     "Mahmoud Tarek led the migration to Project Delta.",
    # ]
    # ingest_documents_for_rag(docs) ``