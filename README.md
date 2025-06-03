# LogChat: A Conversational AI for ME/CFS Pacing Support

## Project Overview

LogChat is a Python-based chat application developed as part of a Master's Thesis. It is designed to assist individuals with Myalgic Encephalomyelitis/Chronic Fatigue Syndrome (ME/CFS) and Long Covid in managing their condition through a technique called pacing. The system aims to reduce the documentation burden of daily activity and symptom logging by enabling users to interact conversationally.

The primary goal of this research project is to explore how current natural language processing technology, specifically Large Language Models (LLMs), can be integrated into a system architecture to enable continuous, conversation-based tracking of activities and symptom severity for ME/CFS patients. For a comprehensive understanding of the research, development, and evaluation, please refer to the full thesis located at `docs/thesis.pdf`.

## System Architecture

LogChat employs a modular architecture built with Python, LangGraph, LangChain, and Ollama for local LLM execution. Key components include:

* **Conversational Interface**: Manages the dialogue flow and state.
* **LLM-Powered Nodes**:
    * **Opener**: Initiates conversations with personalized greetings.
    * **Planner**: Analyzes user input, determines conversational goals, and invokes tools.
    * **Responder**: Generates empathetic and contextually appropriate user-facing messages.
    * **Extractor**: Identifies and structures loggable information (symptoms, activities) from the conversation.
    * **Summarizer**: Maintains short-term and long-term memory by creating interaction summaries and updating a user profile.
* **Tools**: Functions that LLM components can call (e.g., `log_activity`, `log_symptom`, `retrieve_information`, `retrieve_activity_level`).
* **Database**: A PostgreSQL database with the pgvector extension stores user data, conversation history, structured logs, and knowledge base embeddings.
* **Evaluation Framework**: A suite of scripts and datasets for simulating user interactions and evaluating the system's performance.

## Getting Started

### Prerequisites

1.  **PostgreSQL with pgvector**:
    * Install PostgreSQL (version 12+ recommended).
    * Install the pgvector extension. Ensure it's enabled for your database.
2.  **Ollama**:
    * Install Ollama from [ollama.com](https://ollama.com/).
    * Pull the LLM models you intend to use (e.g., `ollama pull qwen2.5:14b-instruct-q4_K_M`). The default model is specified in the `.env` file.

### Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd LogChat
    ```
2.  **Install dependencies using Poetry**:
    * Ensure you have Poetry installed.
    * Run:
        ```bash
        poetry install
        ```

### Configuration

1.  **Create a `.env` file** in the root of the project by copying the example below. Update the placeholder values with your actual keys and settings.

    ```dotenv
    # API Keys (Optional, if using proprietary models)
    OPENAI_API_KEY=your_openai_api_key
    GOOGLE_API_KEY=your_google_api_key

    # Default user for CLI
    USER_ID=4 # Corresponds to a user ID in the database

    # Logging Configuration
    LOGCHAT_LOG_DIR="logs/" # Directory to store logs
    LOG_FULL_PROMPT="false" # Set to "true" to log full LLM prompts (very verbose)

    # LLM Configuration for LogChat's core components
    LOG_CHAT_MODEL_PROVIDER="ollama" # "ollama", "google", or "openai"
    LOG_CHAT_LLM="qwen2.5:14b-instruct-q4_K_M" # Specify the model name
    OLLAMA_BASE_URL="http://localhost:11434" # Default Ollama URL

    # LLM Configuration for Evaluation (Impersonator & Judge)
    JUDGE_LLM="gemini-2.5-flash-preview-05-20" # Or any capable model
    IMPERSONATOR_LLM="gemini-2.0-flash" # Or any capable model

    # Database Connection
    LOG_CHAT_DB="postgresql://logchat:logchat123@localhost/logchat" # Update with your DB credentials
    ```

### Database Setup

1.  **Create the database**: Ensure you have a PostgreSQL database named `logchat` (or as specified in your `LOG_CHAT_DB` environment variable) and that the user specified has the necessary permissions.
2.  **Run database migrations using Alembic**:
    ```bash
    poetry run alembic upgrade head
    ```
3.  **Insert master data**:
    * **Knowledge Base**: To populate the knowledge base for the `retrieve_information` tool, run:
        ```bash
        poetry run python src/database/master_data/knowledge_inserter.py
        ```
        This script will process CSV files in `src/database/master_data/` (e.g., `meassociation_pacing_guide_patients.csv`) and insert their content along with embeddings into the database.
    * **Test Users**: To insert predefined test users (Mark, Sarah, Elena, Charlie with IDs 1-4 respectively), run:
        ```bash
        poetry run python src/database/master_data/test_user_inserter.py
        ```

## Running LogChat

You can interact with LogChat via the Command Line Interface (CLI) or run the evaluation scripts.

### Via CLI

To start a conversation with LogChat:

```bash
poetry run python -m cli
```
The `USER_ID` in your `.env` file will determine which user profile LogChat loads.

### Via Evaluation Scripts

The evaluation framework uses an `Impersonator` LLM to simulate user interactions and a `Judge` LLM to assess LogChat's performance.

* **Run the full evaluation process (Simulator + Judge + Plotter)**:
    ```bash
    poetry run python tests/eval.py
    ```
    This will:
    1.  Simulate conversations for each persona in `tests/data/eval_dataset.json`.
    2.  Run the `Judge` to evaluate these conversations against predefined checklists.
    3.  Generate plots visualizing activity and symptom data from the simulated logs.
    Evaluation logs and plots will be saved in the directory specified by `LOGCHAT_LOG_DIR` (default: `logs/`).

* **Run only the Judge**:
    If you have existing simulation logs and only want to re-run the judgment phase:
    ```bash
    poetry run python tests/judge.py
    ```

* **Run only the Plotter**:
    To generate plots from existing database logs:
    ```bash
    poetry run python tests/plotter.py
    ```

You can also use a `launch.json` configuration with your IDE (like VS Code) for easier debugging:

## Project Structure

* `src/`: Core application code.
    * `app.py`: Main LogChat application class.
    * `nodes/`: Individual LLM-powered components (Planner, Responder, etc.).
    * `prompts.py`: System and instruction prompts for all LLM components.
    * `tools/`: Definitive functions that LogChat can execute.
    * `database/`: Database models, session management, and master data.
* `tests/`: Evaluation framework.
    * `eval.py`: Main script to run simulations and evaluations.
    * `judge.py`: Script for the `Judge` LLM to evaluate conversations.
    * `simulator/`: Components for the `Impersonator` LLM.
    * `plotter.py`: Script to generate activity/symptom plots.
    * `data/eval_dataset.json`: Personas and interaction scenarios for evaluation.
    * `prompts.py`: System prompts for the Impersonator and Judge LLMs.
* `cli/`: Command-line interface for interacting with LogChat.
* `alembic/`: Database migration scripts.
* `docs/`:
    * `thesis.pdf`: The full Master's Thesis document detailing the project.
    * `eval_results/`: Contains detailed logs from evaluation runs, including performance scores and annotated conversations for different LLMs.
* `logs/`: Default directory for runtime logs, including evaluation outputs.

## For Thesis Supervisors

The following parts of the repository might be of particular interest:

* **Prompts**: All prompts used to guide the LLM components are located in `src/prompts.py`. The prompts for the evaluation LLMs (Impersonator and Judge) are in `tests/prompts.py`.
* **Evaluation Dataset**: The structured scenarios used for evaluation, including persona definitions and interaction checklists, can be found in `tests/data/eval_dataset.json`.
* **Evaluation Results**: Detailed logs from various evaluation runs with different LLMs are stored in `docs/eval_results/`. Each sub-directory typically contains the raw conversation logs, the Judge's annotated evaluation, and a summary of scores. A comparative summary across different models can be found in `docs/eval_results/summary.log`.
* **Core Logic**: The interaction flow and state management are primarily orchestrated in `src/app.py` using LangGraph, with individual agentic components in `src/nodes/`.

This repository serves as a public archive for the LogChat thesis project.

## Disclaimer

LogChat is a research prototype. It is not a medical device and should not be used for clinical decision-making or to replace professional medical advice.