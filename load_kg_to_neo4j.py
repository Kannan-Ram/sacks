"""
Load SAC Knowledge Graph Triples from CSV to Neo4j

This script reads the sac_knowledge_graph_triples.csv file and loads it into
a Neo4j database named 'sac-top-kg' as a knowledge graph.
"""

import csv
from pathlib import Path
from typing import Dict, List
import logging
from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KnowledgeGraphLoader:
    """Load knowledge graph triples into Neo4j."""

    def __init__(
        self,
        uri: str = "bolt://127.0.0.1:7687",
        user: str = "neo4j",
        password: str = "Password1",  # Update this
        database: str = "sac-top-kg"
    ):
        """Initialize Neo4j connection."""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        logger.info(f"Connected to Neo4j at {uri}, database: {database}")

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def clear_database(self):
        """Clear all nodes and relationships from the database."""
        with self.driver.session(database=self.database) as session:
            result = session.run("MATCH (n) DETACH DELETE n")
            logger.info("Database cleared")

    def create_indexes(self):
        """Create indexes for better query performance."""
        indexes = [
            "CREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name)",
            "CREATE INDEX entity_type IF NOT EXISTS FOR (n:Entity) ON (n.type)",
        ]

        with self.driver.session(database=self.database) as session:
            for index_query in indexes:
                session.run(index_query)
                logger.info(f"Created index: {index_query}")

    def load_triple(
        self,
        subject: str,
        subject_type: str,
        relation: str,
        obj: str,
        object_type: str,
        confidence: float,
        provenance: str
    ):
        """
        Load a single triple into Neo4j.

        Creates nodes for subject and object with their types as labels,
        and creates a relationship between them.
        """
        query = """
        MERGE (s:Entity {name: $subject})
        ON CREATE SET s.type = $subject_type
        MERGE (o:Entity {name: $object})
        ON CREATE SET o.type = $object_type
        MERGE (s)-[r:RELATES {type: $relation}]->(o)
        ON CREATE SET
            r.confidence = $confidence,
            r.provenance = $provenance
        ON MATCH SET
            r.confidence = $confidence,
            r.provenance = $provenance
        """

        with self.driver.session(database=self.database) as session:
            session.run(
                query,
                subject=subject,
                subject_type=subject_type,
                relation=relation,
                object=obj,
                object_type=object_type,
                confidence=confidence,
                provenance=provenance
            )

    def load_from_csv(self, csv_path: Path, clear_first: bool = True):
        """
        Load all triples from CSV file into Neo4j.

        Args:
            csv_path: Path to the CSV file
            clear_first: Whether to clear the database before loading
        """
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        if clear_first:
            logger.info("Clearing existing data...")
            self.clear_database()

        logger.info("Creating indexes...")
        self.create_indexes()

        logger.info(f"Loading triples from {csv_path}...")

        count = 0
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    self.load_triple(
                        subject=row['subject'],
                        subject_type=row['subject_type'],
                        relation=row['relation'],
                        obj=row['object'],
                        object_type=row['object_type'],
                        confidence=float(row['confidence']),
                        provenance=row['provenance']
                    )
                    count += 1

                    if count % 50 == 0:
                        logger.info(f"Loaded {count} triples...")

                except Exception as e:
                    logger.error(f"Error loading row {count + 1}: {e}")
                    logger.error(f"Row data: {row}")
                    continue

        logger.info(f"Successfully loaded {count} triples!")

        # Print statistics
        self.print_stats()

    def print_stats(self):
        """Print database statistics."""
        with self.driver.session(database=self.database) as session:
            # Count nodes
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]

            # Count relationships
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]

            # Count entity types
            type_query = """
            MATCH (n:Entity)
            RETURN n.type as type, count(n) as count
            ORDER BY count DESC
            LIMIT 10
            """
            types = session.run(type_query).data()

            # Count relationship types
            rel_type_query = """
            MATCH ()-[r:RELATES]->()
            RETURN r.type as relation_type, count(r) as count
            ORDER BY count DESC
            LIMIT 10
            """
            rel_types = session.run(rel_type_query).data()

            logger.info("=" * 50)
            logger.info("DATABASE STATISTICS")
            logger.info("=" * 50)
            logger.info(f"Total Entities: {node_count}")
            logger.info(f"Total Relationships: {rel_count}")
            logger.info("")
            logger.info("Top 10 Entity Types:")
            for item in types:
                logger.info(f"  {item['type']}: {item['count']}")
            logger.info("")
            logger.info("Top 10 Relation Types:")
            for item in rel_types:
                logger.info(f"  {item['relation_type']}: {item['count']}")
            logger.info("=" * 50)


def main():
    """Main function to load the knowledge graph."""
    # Configuration
    NEO4J_URI = "bolt://127.0.0.1:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "Password1"
    NEO4J_DATABASE = "sac-top-kg"
    CSV_FILE = Path(__file__).parent / "sac_knowledge_graph_triples.csv"

    # Load the knowledge graph
    loader = KnowledgeGraphLoader(
        uri=NEO4J_URI,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD,
        database=NEO4J_DATABASE
    )

    try:
        loader.load_from_csv(CSV_FILE, clear_first=True)
        logger.info("Knowledge graph loading complete!")
        logger.info(f"Open Neo4j Browser at http://localhost:7474")
        logger.info(f"Run this query to explore: MATCH (n)-[r]->(m) RETURN n,r,m LIMIT 100")
    except Exception as e:
        logger.error(f"Error loading knowledge graph: {e}")
        raise
    finally:
        loader.close()


if __name__ == "__main__":
    main()
