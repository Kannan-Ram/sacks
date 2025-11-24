"""
SAC Knowledge Graph-Grounded Chatbot UI

Streamlit interface for the SAC testing assistant chatbot.
"""

import streamlit as st
from sac_chatbot_service import SACChatbot
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="SAC Testing Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #0070f3;
        margin-bottom: 1rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #0070f3;
    }
    .assistant-message {
        background-color: #f5f5f5;
        border-left: 4px solid #4caf50;
    }
    .kg-context {
        background-color: #2b2b2b;
        border: 1px solid #4a4a4a;
        border-radius: 0.3rem;
        padding: 0.8rem;
        font-size: 0.85rem;
        font-family: monospace;
        color: #e0e0e0;
    }
    .stButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_chatbot():
    """Initialize the chatbot (cached to avoid reconnections)."""
    return SACChatbot(
        llm_base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1"),
        llm_model=os.getenv("LLM_MODEL_NAME", "mistralai/magistral-small-2509"),
        neo4j_uri=os.getenv("NEO4J_URI", "neo4j+s://304ad687.databases.neo4j.io"),
        neo4j_user=os.getenv("NEO4J_USERNAME", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "f3nMzDC7pdFWoB9dqR_ajS37Vr2KNiHTNDetbCoo0rk"),
        neo4j_database=os.getenv("NEO4J_DATABASE", "neo4j")
    )


def main():
    """Main Streamlit application."""

    # Header
    st.markdown('<p class="main-header">🤖 SAC Testing Assistant</p>', unsafe_allow_html=True)
    st.markdown(
        "**AI-powered testing assistant grounded by SAC Knowledge Graph**  \n"
        "Ask questions about SAC features, generate test scenarios, or explore feature relationships."
    )

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        # Temperature control
        temperature = st.slider(
            "Creativity (Temperature)",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1,
            help="Higher values = more creative responses"
        )

        # Show KG context toggle
        show_kg_context = st.checkbox(
            "Show Knowledge Graph Context",
            value=True,
            help="Display the KG context used to ground responses"
        )

        st.divider()

        # Quick actions
        st.header("🚀 Quick Actions")

        if st.button("📊 Generate Geo Map Test"):
            st.session_state.quick_query = "Generate an exploratory test scenario for Geo Map widget in SAC"

        if st.button("📈 Story Widget Tests"):
            st.session_state.quick_query = "Create integration test cases for Story with Chart and Table widgets"

        if st.button("🔄 Data Action Tests"):
            st.session_state.quick_query = "Generate test scenarios for Data Actions in Planning"

        if st.button("🎨 Canvas Page Tests"):
            st.session_state.quick_query = "Create test cases for Canvas Pages with multiple widget types"

        st.divider()

        # Example queries
        st.header("💡 Example Queries")
        st.markdown("""
        - Generate test scenarios for Geo Map
        - What features support Canvas Pages?
        - Create integration tests for Planning
        - Explain Story and its relationships
        - Test cases for R Visualization
        - What capabilities does Table widget have?
        """)

        st.divider()

        # Clear chat button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.rerun()

        st.divider()

        # Stats
        st.header("📊 Stats")
        if "messages" in st.session_state:
            st.metric("Messages", len(st.session_state.messages))

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.chat_history = []

    # Initialize chatbot
    try:
        chatbot = initialize_chatbot()
        # Update temperature if changed
        chatbot.temperature = temperature
    except Exception as e:
        st.error(f"❌ Failed to initialize chatbot: {e}")
        st.stop()

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Show KG context if available and toggle is on
            if (
                message["role"] == "assistant"
                and show_kg_context
                and "kg_context" in message
                and message["kg_context"]
            ):
                with st.expander("📚 Knowledge Graph Context Used"):
                    st.markdown(
                        f'<div class="kg-context">{message["kg_context"]}</div>',
                        unsafe_allow_html=True
                    )

    # Handle quick query from sidebar
    if "quick_query" in st.session_state:
        user_input = st.session_state.quick_query
        del st.session_state.quick_query
    else:
        # Chat input
        user_input = st.chat_input("Ask me about SAC testing...")

    if user_input:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking and consulting knowledge graph..."):
                try:
                    # Generate response
                    result = chatbot.generate_response(
                        user_query=user_input,
                        chat_history=st.session_state.chat_history[-6:]  # Last 3 exchanges
                    )

                    response = result["response"]
                    kg_context = result.get("kg_context", "")

                    # Display response
                    st.markdown(response)

                    # Show KG context if enabled
                    if show_kg_context and kg_context:
                        with st.expander("📚 Knowledge Graph Context Used"):
                            st.markdown(
                                f'<div class="kg-context">{kg_context}</div>',
                                unsafe_allow_html=True
                            )

                    # Show usage stats if available
                    if result.get("usage"):
                        usage = result["usage"]
                        st.caption(
                            f"📊 Tokens: {usage.get('total_tokens', 'N/A')} "
                            f"(Prompt: {usage.get('prompt_tokens', 'N/A')}, "
                            f"Response: {usage.get('completion_tokens', 'N/A')})"
                        )

                    # Add to session state
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "kg_context": kg_context
                    })

                    # Update chat history for context
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": user_input
                    })
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response
                    })

                except Exception as e:
                    error_msg = f"❌ Error generating response: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })

    # Footer
    st.divider()
    st.caption(
        "🔗 Powered by SAC Knowledge Graph (Neo4j) | "
        "🤖 Local LLM (OpenAI-compatible API) | "
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )


if __name__ == "__main__":
    main()
