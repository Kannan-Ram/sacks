"""Neo4j database client for knowledge graph storage and queries.

This module provides a client for interacting with Neo4j database,
including connection management, graph creation, and querying.
"""

from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError

from .config import settings
from .logger import setup_logger

logger = setup_logger(__name__)


class Neo4jClient:
    """Client for Neo4j database operations."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        """Initialize Neo4j client.

        Args:
            uri: Neo4j URI (defaults to settings.neo4j_uri)
            user: Neo4j username (defaults to settings.neo4j_user)
            password: Neo4j password (defaults to settings.neo4j_password)
        """
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self._driver: Optional[Driver] = None

        logger.info(f"Neo4jClient initialized with URI: {self.uri}")

    def connect(self) -> None:
        """Establish connection to Neo4j database.

        Raises:
            ServiceUnavailable: If cannot connect to Neo4j
            AuthError: If authentication fails
        """
        try:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j")

        except ServiceUnavailable as e:
            logger.error(f"Cannot connect to Neo4j at {self.uri}: {e}")
            raise
        except AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            raise

    def close(self) -> None:
        """Close Neo4j connection."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")

    def __enter__(self) -> "Neo4jClient":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def verify_connection(self) -> bool:
        """Verify that connection to Neo4j is active.

        Returns:
            True if connected, False otherwise
        """
        try:
            if not self._driver:
                return False
            self._driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            return False

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries

        Raises:
            RuntimeError: If not connected to database
        """
        if not self._driver:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        parameters = parameters or {}

        try:
            with self._driver.session() as session:
                result = session.run(query, parameters)
                return [dict(record) for record in result]

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def create_node(
        self,
        label: str,
        properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a node in the graph.

        Args:
            label: Node label
            properties: Node properties

        Returns:
            Created node data
        """
        query = f"""
        CREATE (n:{label} $props)
        RETURN n
        """
        result = self.execute_query(query, {"props": properties})
        return result[0]["n"] if result else {}

    def create_relationship(
        self,
        from_node_label: str,
        from_node_props: Dict[str, Any],
        relationship_type: str,
        to_node_label: str,
        to_node_props: Dict[str, Any],
        rel_properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a relationship between two nodes.

        Args:
            from_node_label: Label of source node
            from_node_props: Properties to match source node
            relationship_type: Type of relationship
            to_node_label: Label of target node
            to_node_props: Properties to match target node
            rel_properties: Properties for the relationship

        Returns:
            True if relationship created
        """
        rel_properties = rel_properties or {}

        # Build WHERE clauses
        from_conditions = " AND ".join(
            [f"from.{k} = ${{{k}_from}}" for k in from_node_props.keys()]
        )
        to_conditions = " AND ".join(
            [f"to.{k} = ${{{k}_to}}" for k in to_node_props.keys()]
        )

        query = f"""
        MATCH (from:{from_node_label}), (to:{to_node_label})
        WHERE {from_conditions} AND {to_conditions}
        CREATE (from)-[r:{relationship_type} $rel_props]->(to)
        RETURN r
        """

        parameters = {
            **{f"{k}_from": v for k, v in from_node_props.items()},
            **{f"{k}_to": v for k, v in to_node_props.items()},
            "rel_props": rel_properties,
        }

        result = self.execute_query(query, parameters)
        return len(result) > 0

    def clear_database(self) -> None:
        """Clear all nodes and relationships from database.

        WARNING: This will delete all data in the database!
        """
        logger.warning("Clearing all data from Neo4j database")
        query = "MATCH (n) DETACH DELETE n"
        self.execute_query(query)
        logger.info("Database cleared")

    def get_node_count(self) -> int:
        """Get total number of nodes in database.

        Returns:
            Node count
        """
        query = "MATCH (n) RETURN count(n) as count"
        result = self.execute_query(query)
        return result[0]["count"] if result else 0

    def get_relationship_count(self) -> int:
        """Get total number of relationships in database.

        Returns:
            Relationship count
        """
        query = "MATCH ()-[r]->() RETURN count(r) as count"
        result = self.execute_query(query)
        return result[0]["count"] if result else 0

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph.

        Returns:
            Dictionary with graph statistics
        """
        return {
            "nodes": self.get_node_count(),
            "relationships": self.get_relationship_count(),
            "uri": self.uri,
        }
