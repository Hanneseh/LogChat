import json
import os

from dotenv import load_dotenv
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool
from langchain_ollama import OllamaEmbeddings  # Added

from src.database import LogChatDB
from src.logger import logger
from src.utils import get_current_sim_time

load_dotenv()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
RETRIEVAL_LIMIT = 3

db = LogChatDB()

embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)


def get_embedding(text: str) -> list[float] | None:
    """Generates a vector embedding for the given text using OllamaEmbeddings."""
    try:
        return embeddings.embed_query(text)
    except Exception as e:
        logger.error(f"An unexpected error occurred during embedding with Ollama: {e}")
        return None


@tool(parse_docstring=True)
def retrieve_information(
    config: RunnableConfig,
    query: str,
):
    """
    Searches the LogChat knowledge base for relevant information.

    Use this tool to: Find educational content about ME/CFS, Long Covid, Post-Exertional Malaise (PEM), pacing strategies, or specific symptoms when the user asks or the conversation context requires it (e.g., explaining PEM after user reports overexertion). The knowledge base includes clinical guidelines, research summaries, and pacing techniques.

    Args:
        query (str): A specific question or topic to search for (e.g., "What is PEM?", "pacing strategies for cognitive tasks").
    """
    configurable = config.get("configurable", {})
    current_sim_time = get_current_sim_time(configurable)
    similarity_threshold = 0.4

    tool_args = {
        "query": query,
    }
    logger.write(
        f"RETRIEVE INFORMATION - Args: {json.dumps(tool_args)}",
        sim_time=current_sim_time,
    )

    query_embedding = get_embedding(query)
    if not query_embedding:
        logger.error("Failed to get embedding for the query.")
        return "Could not process the query for information retrieval."

    try:
        search_results_with_scores = db.perform_vector_search_with_scores(
            query_embedding, RETRIEVAL_LIMIT
        )
        filtered_results = [
            knowledge
            for knowledge, score in search_results_with_scores
            if score <= similarity_threshold
        ]
        formatted_output = db.format_results(filtered_results)
    except Exception as e:
        logger.error(f"Database session error during retrieval: {e}")
        return "An error occurred while searching the knowledge base."

    return formatted_output
