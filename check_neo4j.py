#!/usr/bin/env python3
"""Check Neo4j SAC nodes and relationships."""

from neo4j import GraphDatabase

# Connect to Neo4j
driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "Password1"))

def check_sac_nodes():
    with driver.session(database="chunk-entity-relation") as session:
        # Check SAC workspace nodes
        result = session.run("""
            MATCH (n)
            WHERE n.workspace = 'sac-product-docs'
            RETURN n.entity_id, labels(n), n.description
            LIMIT 10
        """)

        print("=== SAC Nodes (first 10) ===")
        for record in result:
            print(f"\nID: {record['n.entity_id']}")
            print(f"Labels: {record['labels(n)']}")
            print(f"Description: {record['n.description'][:100] if record['n.description'] else 'None'}...")

        # Check relationships
        result = session.run("""
            MATCH (a)-[r]->(b)
            WHERE a.workspace = 'sac-product-docs'
            RETURN type(r) as rel_type, r.description, count(*) as count
            LIMIT 20
        """)

        print("\n\n=== SAC Relationships ===")
        for record in result:
            print(f"Type: {record['rel_type']}, Count: {record['count']}")
            print(f"Description: {record['r.description'][:100] if record['r.description'] else 'None'}...")

        # Check for [THINK] nodes
        result = session.run("""
            MATCH (n)
            WHERE n.entity_id CONTAINS '[THINK]' OR n.description CONTAINS '[THINK]'
            RETURN count(n) as think_count
        """)

        record = result.single()
        print(f"\n\n=== Nodes with [THINK] ===")
        print(f"Count: {record['think_count']}")

        # Total node count by workspace
        result = session.run("""
            MATCH (n)
            RETURN n.workspace, count(n) as count
            ORDER BY count DESC
        """)

        print("\n\n=== Nodes by Workspace ===")
        for record in result:
            workspace = record['n.workspace'] or '(no workspace)'
            print(f"{workspace}: {record['count']} nodes")

if __name__ == "__main__":
    check_sac_nodes()
    driver.close()
