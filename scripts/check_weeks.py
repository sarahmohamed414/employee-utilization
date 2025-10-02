from utilization_graph import UtilizationGraph
import sys

def main():
    try:
        # Initialize the graph database connection
        print("Connecting to Neo4j database...")
        util_graph = UtilizationGraph()
        
        # Verify connection
        util_graph.driver.verify_connectivity()
        print("✅ Successfully connected to Neo4j database")
        
        # Get available weeks
        print("\nFetching available weeks...")
        weeks = util_graph.get_available_weeks()
        if not weeks:
            print("No weeks found in the database. Please check if data was loaded properly.")
            return
            
        print("\nAvailable weeks in the database:")
        print(f"Weeks: {', '.join(map(str, weeks))}")
        
        # For each week, show under-utilized employees
        for week in weeks:
            print(f"\nUnder-utilized employees in Week {week}:")
            under_utilized = util_graph.get_under_utilized_employees(week)
            if under_utilized:
                for emp in under_utilized:
                    print(f"- {emp['employee']}: {emp['hours']:.1f} hours")
            else:
                print("No under-utilized employees found")
    
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'util_graph' in locals():
            util_graph.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    main() 