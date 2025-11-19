"""
Knowledge Graph Context Retriever for SAC Chatbot

Retrieves relevant context from the Neo4j knowledge graph based on user queries.
"""

import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KGContextRetriever:
    """Retrieve context from Neo4j knowledge graph for chatbot queries."""

    def __init__(
        self,
        uri: str = "bolt://127.0.0.1:7687",
        user: str = "neo4j",
        password: str = "Password1",
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

    def extract_keywords(self, query: str) -> List[str]:
        """
        Extract potential entity keywords from user query.

        Args:
            query: User's question

        Returns:
            List of keywords that might match entities
        """
        # Common stop words to filter out
        stop_words = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'can', 'may', 'might', 'must', 'for', 'and', 'or', 'but',
            'in', 'on', 'at', 'to', 'from', 'with', 'about', 'what', 'how',
            'when', 'where', 'why', 'which', 'who', 'generate', 'create', 'make',
            'new', 'test', 'scenario', 'like', 'something', 'that'
        }

        # Extract words (handle multi-word terms)
        words = re.findall(r'\b[A-Z][a-z]*(?:\s+[A-Z][a-z]*)*\b|\b[a-z]+\b', query)

        # Filter stop words and short words
        keywords = [
            word for word in words
            if word.lower() not in stop_words and len(word) > 2
        ]

        return keywords

    def search_entities(self, keywords: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for entities matching keywords.

        Args:
            keywords: List of keywords to search for
            limit: Maximum number of entities to return

        Returns:
            List of matching entities with their properties
        """
        if not keywords:
            return []

        # Build case-insensitive regex pattern
        pattern = '|'.join([f'(?i).*{re.escape(kw)}.*' for kw in keywords])

        query = """
        MATCH (n:Entity)
        WHERE n.name =~ $pattern
        RETURN n.name as name, n.type as type
        LIMIT $limit
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, pattern=pattern, limit=limit)
            entities = [dict(record) for record in result]

        logger.info(f"Found {len(entities)} entities for keywords: {keywords}")
        return entities

    def get_entity_relationships(
        self,
        entity_name: str,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get all relationships for a given entity up to max_depth.

        Args:
            entity_name: Name of the entity
            max_depth: Maximum relationship depth (1 or 2)

        Returns:
            List of relationships with source, relation, target, and metadata
        """
        query = f"""
        MATCH path = (n:Entity {{name: $entity_name}})-[r:RELATES*1..{max_depth}]-(m:Entity)
        RETURN
            [node in nodes(path) | {{name: node.name, type: node.type}}] as nodes,
            [rel in relationships(path) | {{
                type: rel.type,
                confidence: rel.confidence,
                provenance: rel.provenance
            }}] as relationships
        LIMIT 50
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, entity_name=entity_name)
            paths = [dict(record) for record in result]

        logger.info(f"Found {len(paths)} relationship paths for '{entity_name}'")
        return paths

    def get_direct_relationships(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Get direct (1-hop) relationships for an entity.

        Args:
            entity_name: Name of the entity

        Returns:
            List of direct relationships
        """
        query = """
        MATCH (source:Entity {name: $entity_name})-[r:RELATES]->(target:Entity)
        RETURN
            source.name as source,
            source.type as source_type,
            r.type as relation,
            target.name as target,
            target.type as target_type,
            r.confidence as confidence,
            r.provenance as provenance
        ORDER BY r.confidence DESC
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, entity_name=entity_name)
            relationships = [dict(record) for record in result]

        return relationships

    def get_related_entities(
        self,
        entity_name: str,
        relation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get entities related to a given entity, optionally filtered by relation type.

        Args:
            entity_name: Name of the entity
            relation_type: Optional relation type filter (e.g., 'CONTAINS', 'SUPPORTS')

        Returns:
            List of related entities
        """
        if relation_type:
            query = """
            MATCH (n:Entity {name: $entity_name})-[r:RELATES {type: $relation_type}]-(m:Entity)
            RETURN DISTINCT
                m.name as name,
                m.type as type,
                r.type as relation,
                r.confidence as confidence
            ORDER BY r.confidence DESC
            LIMIT 20
            """
            params = {"entity_name": entity_name, "relation_type": relation_type}
        else:
            query = """
            MATCH (n:Entity {name: $entity_name})-[r:RELATES]-(m:Entity)
            RETURN DISTINCT
                m.name as name,
                m.type as type,
                r.type as relation,
                r.confidence as confidence
            ORDER BY r.confidence DESC
            LIMIT 20
            """
            params = {"entity_name": entity_name}

        with self.driver.session(database=self.database) as session:
            result = session.run(query, **params)
            related = [dict(record) for record in result]

        return related

    def build_context(self, query: str, max_entities: int = 3) -> str:
        """
        Build context string from knowledge graph based on user query.

        Args:
            query: User's question
            max_entities: Maximum number of entities to include in context

        Returns:
            Formatted context string for LLM
        """
        # Extract keywords and search for entities
        keywords = self.extract_keywords(query)
        logger.info(f"Extracted keywords: {keywords}")

        entities = self.search_entities(keywords, limit=max_entities)

        if not entities:
            return "No relevant context found in the knowledge graph."

        # Build context from entities and their relationships
        context_parts = ["Based on the SAC Knowledge Graph:\n"]

        for entity in entities:
            entity_name = entity['name']
            entity_type = entity['type']

            context_parts.append(f"\n**{entity_name}** (Type: {entity_type}):")

            # Get direct relationships
            relationships = self.get_direct_relationships(entity_name)

            if relationships:
                for rel in relationships[:10]:  # Limit to top 10 relationships
                    context_parts.append(
                        f"  - {rel['relation']} → {rel['target']} "
                        f"({rel['target_type']}) "
                        f"[Confidence: {rel['confidence']:.2f}, Source: {rel['provenance']}]"
                    )
            else:
                context_parts.append("  - No direct relationships found")

        context = "\n".join(context_parts)
        logger.info(f"Built context with {len(entities)} entities")

        return context

    def get_entity_neighborhood(self, entity_name: str) -> Dict[str, Any]:
        """
        Get comprehensive neighborhood information for an entity.

        Args:
            entity_name: Name of the entity

        Returns:
            Dictionary with entity info and all its relationships
        """
        # Get entity info
        query = """
        MATCH (n:Entity {name: $entity_name})
        RETURN n.name as name, n.type as type
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, entity_name=entity_name)
            entity_info = result.single()

            if not entity_info:
                return {}

            entity_dict = dict(entity_info)

        # Get outgoing relationships
        outgoing = self.get_direct_relationships(entity_name)

        # Get incoming relationships
        query = """
        MATCH (source:Entity)-[r:RELATES]->(target:Entity {name: $entity_name})
        RETURN
            source.name as source,
            source.type as source_type,
            r.type as relation,
            target.name as target,
            target.type as target_type,
            r.confidence as confidence,
            r.provenance as provenance
        ORDER BY r.confidence DESC
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, entity_name=entity_name)
            incoming = [dict(record) for record in result]

        return {
            "entity": entity_dict,
            "outgoing_relationships": outgoing,
            "incoming_relationships": incoming
        }


if __name__ == "__main__":
    # Test the retriever
    retriever = KGContextRetriever()

    try:
        # Test query
        test_query = "Generate a test scenario for geo maps"
        print(f"Query: {test_query}\n")

        context = retriever.build_context(test_query)
        print(context)

    finally:
        retriever.close()
