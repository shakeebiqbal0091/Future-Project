#!/usr/bin/env python3
"""
Database initialization script for AI Agent Orchestration Platform
"""

import os
import sys
from pathlib import Path

def main():
    """Main function to initialize the database"""
    print("Initializing database for AI Agent Orchestration Platform...")

    # Add backend to Python path
    backend_dir = Path(__file__).parent.parent / "backend"
    if backend_dir not in sys.path:
        sys.path.insert(0, str(backend_dir))

    try:
        # Import FastAPI app to trigger database initialization
        from app.main import app
        from app.database import get_db
        from app.models import Agent, Workflow, Execution

        print("Connecting to database...")

        # Get database connection
        with get_db() as db:
            # Check if database is initialized
            print("Checking database initialization...")

            # Check if tables exist
            tables = db.get_tables()  # This is a placeholder, actual implementation depends on your ORM
            print(f"Found tables: {tables}")

            # Create default agents if they don't exist
            print("Creating default agents...")

            # Add default agents
            default_agents = [
                {
                    "name": "Default Agent",
                    "description": "Basic agent for simple tasks",
                    "type": "basic",
                    "config": {"max_concurrency": 1}
                },
                {
                    "name": "Data Processing Agent",
                    "description": "Agent specialized in data processing",
                    "type": "data",
                    "config": {"max_concurrency": 3}
                },
                {
                    "name": "Analysis Agent",
                    "description": "Agent for complex analysis",
                    "type": "analysis",
                    "config": {"max_concurrency": 2}
                }
            ]

            for agent_data in default_agents:
                agent = db.query(Agent).filter(Agent.name == agent_data["name"]).first()
                if not agent:
                    new_agent = Agent(**agent_data)
                    db.add(new_agent)
                    print(f"Created agent: {agent_data['name']}")

            # Commit changes
            db.commit()
            print("Database initialization completed successfully!")

            # Show summary
            print("\nDatabase Summary:")
            print(f"Total agents: {db.query(Agent).count()}")
            print(f"Total workflows: {db.query(Workflow).count()}")
            print(f"Total executions: {db.query(Execution).count()}")

    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()