"""
SAC Knowledge Graph-Grounded Chatbot Service

Uses local LLM with OpenAI-compatible API and Neo4j knowledge graph
to generate contextually grounded responses for SAC testing scenarios.
"""

import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from kg_context_retriever import KGContextRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SACChatbot:
    """SAC testing assistant powered by knowledge graph and LLM."""

    def __init__(
        self,
        llm_base_url: str = "http://127.0.0.1:1234/v1",
        llm_model: str = "mistralai/magistral-small-2509",
        llm_api_key: str = "placeholder-api-key",
        neo4j_uri: str = "bolt://127.0.0.1:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "Password1",
        neo4j_database: str = "sac-top-kg",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ):
        """
        Initialize the chatbot.

        Args:
            llm_base_url: Base URL for OpenAI-compatible LLM API
            llm_model: Model name to use
            llm_api_key: API key (placeholder for local LLM)
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            neo4j_database: Neo4j database name
            temperature: LLM temperature (0-1, higher = more creative)
            max_tokens: Maximum tokens in response
        """
        # Initialize OpenAI client with local LLM
        self.client = OpenAI(
            base_url=llm_base_url,
            api_key=llm_api_key
        )
        self.model = llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize knowledge graph retriever
        self.kg_retriever = KGContextRetriever(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
            database=neo4j_database
        )

        # System prompt
        self.system_prompt = """You are an expert SAP Analytics Cloud (SAC) testing assistant.
Your role is to help QA engineers and testers create comprehensive test scenarios based on
the SAC product knowledge graph.

When generating test scenarios:
1. Use the provided knowledge graph context to ensure accuracy
2. Include specific SAC features, capabilities, and relationships mentioned in the context
3. Create realistic, actionable test cases with clear steps
4. Reference the provenance (page numbers) when available
5. Consider edge cases and integration points between features
6. Be specific about widgets, features, and capabilities

Always ground your responses in the knowledge graph context provided. If the context doesn't
contain relevant information, acknowledge that and provide general testing guidance."""

        logger.info("SAC Chatbot initialized successfully")

    def close(self):
        """Clean up resources."""
        self.kg_retriever.close()

    def generate_response(
        self,
        user_query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        use_kg_context: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a response to user query.

        Args:
            user_query: User's question
            chat_history: Optional chat history for context
            use_kg_context: Whether to retrieve and use KG context

        Returns:
            Dictionary with response and metadata
        """
        # Build messages for the LLM
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add chat history if provided
        if chat_history:
            messages.extend(chat_history)

        # Retrieve knowledge graph context
        kg_context = ""
        if use_kg_context:
            try:
                kg_context = self.kg_retriever.build_context(user_query)
                logger.info(f"Retrieved KG context: {len(kg_context)} characters")
            except Exception as e:
                logger.error(f"Error retrieving KG context: {e}")
                kg_context = "Error retrieving knowledge graph context."

        # Build the user message with context
        if kg_context and kg_context != "No relevant context found in the knowledge graph.":
            user_message = f"""Knowledge Graph Context:
{kg_context}

User Question: {user_query}

Please generate a response based on the knowledge graph context above."""
        else:
            user_message = user_query

        messages.append({"role": "user", "content": user_message})

        # Call LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            assistant_message = response.choices[0].message.content

            return {
                "response": assistant_message,
                "kg_context": kg_context,
                "model": self.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if hasattr(response, 'usage') else None
            }

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "response": f"Error generating response: {str(e)}",
                "kg_context": kg_context,
                "model": self.model,
                "error": str(e)
            }

    def generate_test_scenario(
        self,
        feature: str,
        test_type: str = "exploratory"
    ) -> str:
        """
        Generate a test scenario for a specific SAC feature.

        Args:
            feature: SAC feature to test (e.g., "Geo Map", "Story", "Chart")
            test_type: Type of testing (exploratory, functional, integration, etc.)

        Returns:
            Formatted test scenario
        """
        query = f"Generate a {test_type} test scenario for {feature} in SAP Analytics Cloud"
        result = self.generate_response(query)
        return result["response"]

    def explain_feature(self, feature: str) -> str:
        """
        Explain a SAC feature based on knowledge graph.

        Args:
            feature: SAC feature to explain

        Returns:
            Explanation of the feature
        """
        query = f"Explain {feature} and its relationships with other SAC components"
        result = self.generate_response(query)
        return result["response"]

    def find_related_features(self, feature: str) -> List[Dict[str, Any]]:
        """
        Find features related to a given feature.

        Args:
            feature: SAC feature

        Returns:
            List of related features with relationships
        """
        return self.kg_retriever.get_related_entities(feature)

    def get_feature_details(self, feature: str) -> Dict[str, Any]:
        """
        Get comprehensive details about a feature.

        Args:
            feature: SAC feature name

        Returns:
            Dictionary with feature details and relationships
        """
        return self.kg_retriever.get_entity_neighborhood(feature)


def main():
    """Test the chatbot."""
    chatbot = SACChatbot()

    try:
        # Test queries
        test_queries = [
            "Generate an exploratory test scenario for Geo Map",
            "What are the relationships between Story and Chart widgets?",
            "Create integration test cases for Planning with Data Actions"
        ]

        for query in test_queries:
            print(f"\n{'='*80}")
            print(f"Query: {query}")
            print(f"{'='*80}\n")

            result = chatbot.generate_response(query)

            print("Knowledge Graph Context:")
            print(result['kg_context'])
            print("\n" + "-"*80 + "\n")

            print("Response:")
            print(result['response'])
            print("\n")

    finally:
        chatbot.close()


if __name__ == "__main__":
    main()
