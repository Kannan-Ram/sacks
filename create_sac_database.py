#!/usr/bin/env python3
"""Create separate Neo4j database for SAC knowledge graph."""

from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "Password1"))

def create_sac_database():
    with driver.session(database="system") as session:
        # Check if database exists
        result = session.run("SHOW DATABASES")
        databases = [record["name"] for record in result]

        if "sac-kg" in databases:
            print("Database 'sac-kg' already exists")
        else:
            try:
                session.run("CREATE DATABASE `sac-kg`")
                print("Created database 'sac-kg'")
            except Exception as e:
                print(f"Error creating database: {e}")
                print("Note: Database creation requires Neo4j Enterprise or might be restricted")
                print("Alternative: We'll use workspace property instead")

if __name__ == "__main__":
    create_sac_database()
    driver.close()
