#!/usr/bin/env python3
"""
Simple Neo4j connection test script
"""

import os
import time
from neo4j import GraphDatabase

# Configuration
NEO4J_CONFIG = {
    "url": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    "username": os.getenv("NEO4J_USER", "neo4j"),
    "password": os.getenv("NEO4J_PASSWORD", "utilization123"),
}

def test_neo4j_connection():
    """Test Neo4j connection with detailed error reporting"""
    print(f"🔗 Testing Neo4j connection...")
    print(f"   URL: {NEO4J_CONFIG['url']}")
    print(f"   Username: {NEO4J_CONFIG['username']}")
    print(f"   Password: {'*' * len(NEO4J_CONFIG['password'])}")
    
    try:
        # Create driver
        driver = GraphDatabase.driver(
            NEO4J_CONFIG["url"],
            auth=(NEO4J_CONFIG["username"], NEO4J_CONFIG["password"])
        )
        
        # Test connection
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            if record and record["test"] == 1:
                print("✅ Neo4j connection successful!")
                
                # Test database info
                db_info = session.run("CALL dbms.components() YIELD name, versions, edition")
                for record in db_info:
                    print(f"   Database: {record['name']} {record['versions'][0]} ({record['edition']})")
                
                return True
            else:
                print("❌ Neo4j connection failed: Invalid response")
                return False
                
    except Exception as e:
        print(f"❌ Neo4j connection failed: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        return False
    finally:
        if 'driver' in locals():
            driver.close()

def test_ollama_connection():
    """Test Ollama connection"""
    import requests
    
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    print(f"🤖 Testing Ollama connection...")
    print(f"   URL: {ollama_url}")
    
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ Ollama connection successful!")
            print(f"   Available models: {len(models)}")
            for model in models[:3]:  # Show first 3 models
                print(f"   - {model.get('name', 'Unknown')}")
            return True
        else:
            print(f"❌ Ollama connection failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama connection failed: {str(e)}")
        return False

def main():
    print("🧪 Testing service connections...\n")
    
    neo4j_ok = test_neo4j_connection()
    print()
    ollama_ok = test_ollama_connection()
    print()
    
    if neo4j_ok and ollama_ok:
        print("🎉 All services are working correctly!")
        return 0
    else:
        print("❌ Some services are not working. Please check the logs above.")
        return 1

if __name__ == "__main__":
    exit(main())
