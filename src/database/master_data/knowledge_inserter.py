import logging
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings

project_root = Path(__file__).resolve().parents[3]
sys.path.append(str(project_root))

from src.database import LogChatDB  # noqa: E402

load_dotenv()
logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
DATA_DIR = Path(__file__).parent

embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)


def get_embedding(text: str) -> list[float] | None:
    """Generates a vector embedding for the given text using OllamaEmbeddings."""
    try:
        return embeddings.embed_query(text)
    except Exception as e:
        logger.error(f"An unexpected error occurred during embedding with Ollama: {e}")
        return None


def process_csv_file(file_path: Path, db: LogChatDB):
    """Reads a CSV file using pandas, generates embeddings, and inserts data via LogChatDB."""
    logger.info(f"Processing file: {file_path.name}")
    source_name = file_path.stem

    try:
        df = pd.read_csv(file_path)
        required_columns = {"source", "headline", "content"}
        if not required_columns.issubset(df.columns):
            logger.error(
                f"Skipping {file_path.name}: Missing required columns "
                f"(need 'source', 'headline', 'content'). Found: {list(df.columns)}"
            )
            return

        count = 0
        processed_count = 0
        for row in df.itertuples(index=False):
            source = (
                str(row.source).strip()
                if hasattr(row, "source") and pd.notna(row.source)
                else source_name
            )
            headline = (
                str(row.headline).strip()
                if hasattr(row, "headline") and pd.notna(row.headline)
                else ""
            )
            content = (
                str(row.content).strip()
                if hasattr(row, "content") and pd.notna(row.content)
                else ""
            )

            if not content:
                logger.warning(
                    f"Skipping row {processed_count} in {file_path.name} due to empty content."
                )
                continue

            if headline:
                text_to_embed = f"{headline}: {content}"
            else:
                text_to_embed = content

            embedding_vector = get_embedding(text_to_embed)

            if embedding_vector:
                try:
                    db.add_knowledge_chunk(
                        source=source,
                        headline=headline if headline else None,
                        content=content,
                        embedding=embedding_vector,
                    )
                    count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to add knowledge chunk for row {processed_count} in {file_path.name}. "
                        f"Headline: '{headline[:50]}...'. Error: {e}"
                    )
            else:
                logger.warning(
                    f"Could not get embedding for row {processed_count} in {file_path.name}. "
                    f"Headline: '{headline[:50]}...'"
                )

        logger.info(
            f"Successfully processed {processed_count} rows and added {count} entries from {file_path.name}"
        )

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
    except pd.errors.EmptyDataError:
        logger.warning(f"Skipping empty file: {file_path.name}")
    except Exception as e:
        logger.error(f"Failed to process {file_path.name}: {e}")


def main():
    """Main function to find CSV files and process them."""
    logger.info("Starting knowledge base ingestion...")
    db = LogChatDB()

    csv_files = list(DATA_DIR.glob("*.csv"))

    if not csv_files:
        logger.warning(f"No CSV files found in {DATA_DIR}. Exiting.")
        return

    logger.info(f"Found {len(csv_files)} CSV files to process.")

    for csv_file in csv_files:
        process_csv_file(csv_file, db)

    logger.info("Knowledge base ingestion finished.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.addHandler(logging.StreamHandler())
    main()
