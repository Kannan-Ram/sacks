"""
Knowledge Graph Context Retriever for Rakshit's Graph

Retrieves relevant context from the Neo4j knowledge graph with entity-based schema.
This version is optimized for graphs where entities use 'id' property and multiple labels.
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
        uri: str = "neo4j+s://304ad687.databases.neo4j.io",
        user: str = "neo4j",
        password: str = "f3nMzDC7pdFWoB9dqR_ajS37Vr2KNiHTNDetbCoo0rk",
        database: str = "neo4j"
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

        # Extract words
        words = re.findall(r'\b[A-Z][a-z]*(?:\s+[A-Z][a-z]*)*\b|\b[a-z]+\b', query)

        # Filter stop words and short words
        keywords = [
            word for word in words
            if word.lower() not in stop_words and len(word) > 2
        ]

        return keywords

    def search_entities(self, keywords: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for entities matching keywords using 'id' property.

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
        MATCH (n:__Entity__)
        WHERE n.id =~ $pattern
        RETURN n.id as id, labels(n) as labels
        LIMIT $limit
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, pattern=pattern, limit=limit)
            entities = []
            for record in result:
                # Filter out __Entity__ from labels to get actual type
                labels = [label for label in record['labels'] if label != '__Entity__']
                entities.append({
                    'id': record['id'],
                    'type': ', '.join(labels) if labels else 'Entity'
                })

        logger.info(f"Found {len(entities)} entities for keywords: {keywords}")
        return entities

    def get_direct_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Get direct (1-hop) relationships for an entity.

        Args:
            entity_id: ID of the entity

        Returns:
            List of direct relationships
        """
        query = """
        MATCH (source:__Entity__ {id: $entity_id})-[r]->(target:__Entity__)
        RETURN
            source.id as source,
            labels(source) as source_labels,
            type(r) as relation,
            target.id as target,
            labels(target) as target_labels
        ORDER BY relation
        LIMIT 20
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, entity_id=entity_id)
            relationships = []
            for record in result:
                # Get actual types (remove __Entity__ label)
                source_types = [l for l in record['source_labels'] if l != '__Entity__']
                target_types = [l for l in record['target_labels'] if l != '__Entity__']

                relationships.append({
                    'source': record['source'],
                    'source_type': ', '.join(source_types) if source_types else 'Entity',
                    'relation': record['relation'],
                    'target': record['target'],
                    'target_type': ', '.join(target_types) if target_types else 'Entity'
                })

        return relationships

    def get_related_entities(
        self,
        entity_id: str,
        relation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get entities related to a given entity, optionally filtered by relation type.

        Args:
            entity_id: ID of the entity
            relation_type: Optional relation type filter

        Returns:
            List of related entities
        """
        if relation_type:
            query = """
            MATCH (n:__Entity__ {id: $entity_id})-[r]->(m:__Entity__)
            WHERE type(r) = $relation_type
            RETURN DISTINCT
                m.id as id,
                labels(m) as labels,
                type(r) as relation
            LIMIT 20
            """
            params = {"entity_id": entity_id, "relation_type": relation_type}
        else:
            query = """
            MATCH (n:__Entity__ {id: $entity_id})-[r]-(m:__Entity__)
            RETURN DISTINCT
                m.id as id,
                labels(m) as labels,
                type(r) as relation
            LIMIT 20
            """
            params = {"entity_id": entity_id}

        with self.driver.session(database=self.database) as session:
            result = session.run(query, **params)
            related = []
            for record in result:
                entity_types = [l for l in record['labels'] if l != '__Entity__']
                related.append({
                    'id': record['id'],
                    'type': ', '.join(entity_types) if entity_types else 'Entity',
                    'relation': record['relation']
                })

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
        context_parts = ["Based on the Knowledge Graph:\n"]

        for entity in entities:
            entity_id = entity['id']
            entity_type = entity['type']

            context_parts.append(f"\n**{entity_id}** (Type: {entity_type}):")

            # Get direct relationships
            relationships = self.get_direct_relationships(entity_id)

            if relationships:
                for rel in relationships[:10]:  # Limit to top 10 relationships
                    context_parts.append(
                        f"  - {rel['relation']} → {rel['target']} "
                        f"({rel['target_type']})"
                    )
            else:
                context_parts.append("  - No direct relationships found")

        context = "\n".join(context_parts)
        logger.info(f"Built context with {len(entities)} entities")

        return context

    def get_entity_neighborhood(self, entity_id: str) -> Dict[str, Any]:
        """
        Get comprehensive neighborhood information for an entity.

        Args:
            entity_id: ID of the entity

        Returns:
            Dictionary with entity info and all its relationships
        """
        # Get entity info
        query = """
        MATCH (n:__Entity__ {id: $entity_id})
        RETURN n.id as id, labels(n) as labels
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, entity_id=entity_id)
            entity_info = result.single()

            if not entity_info:
                return {}

            entity_types = [l for l in entity_info['labels'] if l != '__Entity__']
            entity_dict = {
                'id': entity_info['id'],
                'type': ', '.join(entity_types) if entity_types else 'Entity'
            }

        # Get outgoing relationships
        outgoing = self.get_direct_relationships(entity_id)

        # Get incoming relationships
        query = """
        MATCH (source:__Entity__)-[r]->(target:__Entity__ {id: $entity_id})
        RETURN
            source.id as source,
            labels(source) as source_labels,
            type(r) as relation,
            target.id as target,
            labels(target) as target_labels
        LIMIT 20
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, entity_id=entity_id)
            incoming = []
            for record in result:
                source_types = [l for l in record['source_labels'] if l != '__Entity__']
                target_types = [l for l in record['target_labels'] if l != '__Entity__']

                incoming.append({
                    'source': record['source'],
                    'source_type': ', '.join(source_types) if source_types else 'Entity',
                    'relation': record['relation'],
                    'target': record['target'],
                    'target_type': ', '.join(target_types) if target_types else 'Entity'
                })

        return {
            "entity": entity_dict,
            "outgoing_relationships": outgoing,
            "incoming_relationships": incoming
        }


if __name__ == "__main__":
    # Test the retriever
    retriever = KGContextRetriever()

    try:
        # Test queries
        test_queries = [
            "What are the features of SAP Analytics Cloud?",
            "Tell me about Planning",
            "Generate test scenario for Story"
        ]

        for test_query in test_queries:
            print(f"\n{'='*80}")
            print(f"Query: {test_query}")
            print(f"{'='*80}\n")

            context = retriever.build_context(test_query, max_entities=3)
            print(context)

    finally:
        retriever.close()
