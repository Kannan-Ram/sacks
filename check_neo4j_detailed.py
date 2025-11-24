#!/usr/bin/env python3
"""Detailed Neo4j inspection."""

from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "Password1"))

def detailed_check():
    with driver.session(database="chunk-entity-relation") as session:
        # Check all properties on nodes
        result = session.run("""
            MATCH (n)
            RETURN n
            LIMIT 5
        """)

        print("=== Sample Nodes (first 5) ===")
        for i, record in enumerate(result, 1):
            node = record['n']
            print(f"\n--- Node {i} ---")
            print(f"Labels: {list(node.labels)}")
            print(f"Properties: {dict(node)}")

        # Check all relationship types
        result = session.run("""
            MATCH ()-[r]->()
            RETURN DISTINCT type(r) as rel_type, count(*) as count
            ORDER BY count DESC
        """)

        print("\n\n=== All Relationship Types ===")
        for record in result:
            print(f"{record['rel_type']}: {record['count']}")

        # Check for [THINK] contamination
        result = session.run("""
            MATCH (n)
            WHERE n.entity_id CONTAINS '[THINK]' OR
                  n.description CONTAINS '[THINK]' OR
                  n.entity_id CONTAINS 'Okay' OR
                  n.entity_id CONTAINS 'let\\'s'
            RETURN n.entity_id, n.description
            LIMIT 5
        """)

        print("\n\n=== Nodes with Reasoning Text ===")
        for record in result:
            print(f"\nID: {record['n.entity_id']}")
            desc = record['n.description'][:200] if record['n.description'] else 'None'
            print(f"Description: {desc}...")

        # Check total counts
        result = session.run("""
            MATCH (n)
            RETURN count(n) as total_nodes
        """)
        total = result.single()['total_nodes']

        result = session.run("""
            MATCH ()-[r]->()
            RETURN count(r) as total_rels
        """)
        total_rels = result.single()['total_rels']

        print(f"\n\n=== Totals ===")
        print(f"Total nodes: {total}")
        print(f"Total relationships: {total_rels}")

if __name__ == "__main__":
    detailed_check()
    driver.close()
