# LogChat: A Memory-Enhanced Conversational AI for ME/CFS Pacing Support

## Project Overview

This repository contains the source code and complete thesis for **LogChat**, a prototype of a novel, memory-enhanced chatbot architecture designed to support individuals with Myalgic Encephalomyelitis/Chronic Fatigue Syndrome (ME/CFS) and Long Covid.

### The Challenge
Managing ME/CFS requires a meticulous energy management strategy known as *pacing* to avoid its hallmark symptom, Post-Exertional Malaise (PEM). However, the detailed logging of symptoms and activities recommended for effective pacing imposes a significant documentation burden on patients already suffering from profound fatigue and cognitive impairment.

### The Solution: LogChat
LogChat was developed as a proof-of-concept to address this challenge. It is a modular, agentic conversational AI with two primary functions:
1.  **Conversational Logging**: To transform natural, unstructured conversational interactions into a structured, longitudinal health diary.
2.  **Educational Support**: To provide accessible, on-demand educational information about ME/CFS and pacing, grounded in a curated knowledge base.

By integrating a persistent, evolving memory of the user's health status and history, LogChat aims to serve as an empathetic and personalized companion, reducing the cognitive load associated with manual tracking and empowering users to better understand the patterns of their illness.

### Key Findings
The research, conducted following the Design Science Research Methodology, confirmed the architecture's viability as a proof-of-concept. However, the evaluation revealed a critical performance dichotomy:
* **Proprietary LLMs** (e.g., Google's Gemini series) demonstrated near-perfect reliability, validating the architectural design.
* **Open-source models** suitable for private, on-device deployment showed significant inconsistencies, rendering them unsuitable for this sensitive health application at their current stage of development.

This project contributes a validated architecture for conversational health logging, a replicable evaluation method, and crucial insights into the performance gap defining the practical limits of such systems.

**For a comprehensive understanding of the research, development, and evaluation, please refer to the full thesis document located at `docs/thesis.pdf`.**

## System Architecture

LogChat is built on a modular, four-layer architecture designed for flexibility and robust, stateful conversation management. It is implemented in Python using `LangChain`, `LangGraph`, and a PostgreSQL database.

* **Interaction Layer**: Manages the live, turn-based dialogue with the user. It is orchestrated by a state graph implemented with `LangGraph` and includes:
    * **Opener Node**: Delivers a personalized greeting to initiate the conversation.
    * **Planner Node**: The reasoning core of the system. It analyzes user intent, plans the system's response, and can use tools to retrieve information (e.g., from the knowledge base or past activity logs).
    * **Responder Node**: Crafts the final, empathetic, and context-aware message presented to the user.

* **Post-Interaction Layer**: Activates after a conversation ends to process the interaction asynchronously.
    * **Summarizer Node**: Generates a concise summary of the conversation for short-term memory and updates the user's persistent long-term profile.
    * **Extractor Node**: Analyzes the full conversation transcript and uses tools to write structured `symptom` and `activity` logs to the database.

* **Data Layer**: The persistence layer of the system.
    * **PostgreSQL Database**: Stores all user data, including profiles, interaction summaries, and structured logs.
    * **pgVector Extension**: Enables Retrieval-Augmented Generation (RAG) by storing and searching vector embeddings of the knowledge base.

* **LLM Layer**: An abstraction that allows LogChat to be powered by various Large Language Models, including proprietary APIs (Google Gemini, OpenAI GPT) or locally-hosted open-source models via **Ollama**.

## Evaluation Framework

A key contribution of this thesis is a novel, automated evaluation framework designed to rigorously assess the technical reliability and functional correctness of the LogChat architecture. It consists of:
* An **Impersonator** LLM agent that simulates realistic user personas and interaction scenarios.
* A **Judge** LLM agent that programmatically analyzes conversation logs against a detailed checklist to verify system behavior and calculate a quantitative performance score.

This framework enables repeatable, objective evaluation and was instrumental in the iterative refinement of the LogChat prototype.

## Getting Started

### Prerequisites

1.  **PostgreSQL with pgvector**:
    * Install PostgreSQL (version 12+ recommended).
    * Install the `pgvector` extension and ensure it is enabled in your database.
2.  **Ollama**:
    * Install Ollama from [ollama.com](https://ollama.com).
    * Pull the LLM models you intend to use (e.g., `ollama pull qwen2.5:14b-instruct-q4_K_M`). The default model is specified in the `.env` file.

### Installation

1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/Hanneseh/LogChat.git](https://github.com/Hanneseh/LogChat.git)
    cd LogChat
    ```
2.  **Install dependencies using Poetry**:
    * Ensure you have Poetry installed.
    * Run:
        ```bash
        poetry install
        ```

### Configuration

1.  **Create a `.env` file** in the project root by copying the example below. Update the placeholder values with your actual database credentials and API keys.

    ```dotenv
    # API Keys (Optional, if using proprietary models)
    OPENAI_API_KEY="your_openai_api_key"
    GOOGLE_API_KEY="your_google_api_key"

    # Default user for the CLI application
    USER_ID=4 # Corresponds to a user ID in the database

    # Logging Configuration
    LOGCHAT_LOG_DIR="logs/" # Directory to store log files
    LOG_FULL_PROMPT="false" # Set to "true" to log full LLM prompts (very verbose)

    # LLM Configuration for LogChat's core components
    LOG_CHAT_MODEL_PROVIDER="ollama" # "ollama", "google", or "openai"
    LOG_CHAT_LLM="qwen2.5:14b-instruct-q4_K_M" # Specify the model name (e.g., from Ollama)
    OLLAMA_BASE_URL="http://localhost:11434" # Default Ollama URL

    # LLM Configuration for Evaluation Framework (Impersonator & Judge)
    JUDGE_LLM="gemini-2.5-flash-preview-05-20"
    IMPERSONATOR_LLM="gemini-2.0-flash"

    # Database Connection
    LOG_CHAT_DB="postgresql://logchat:logchat123@localhost/logchat" # Update with your DB credentials
    ```

### Database Setup

1.  **Create the database**: Ensure you have a PostgreSQL database named `logchat` (or as specified in your `LOG_CHAT_DB` variable) and that the specified user has the necessary permissions.
2.  **Run database migrations using Alembic**:
    ```bash
    poetry run alembic upgrade head
    ```
3.  **Insert master data**:
    * **Knowledge Base**: To populate the knowledge base for the RAG `retrieve_information` tool, run:
        ```bash
        poetry run python src/database/master_data/knowledge_inserter.py
        ```
        This script processes CSV files in `src/database/master_data/` and inserts their content and vector embeddings into the database.
    * **Test Users**: To insert predefined test users for evaluation (Mark, Sarah, Elena, Charlie with IDs 1-4 respectively), run:
        ```bash
        poetry run python src/database/master_data/test_user_inserter.py
        ```

## Running LogChat

You can interact with LogChat via the Command Line Interface (CLI) or run the full evaluation suite.

### Via CLI

To start a conversation with LogChat:

```bash
poetry run python -m cli
```

The `USER_ID` in your `.env` file will determine which user profile LogChat loads for the session.

### Via Evaluation Scripts

The evaluation framework uses the `Impersonator` and `Judge` LLMs to automate testing.

  * **Run the full evaluation process (Simulator + Judge + Plotter)**:

    ```bash
    poetry run python tests/eval.py
    ```

    This will:

    1.  Simulate conversations for each persona defined in `tests/data/eval_dataset.json`.
    2.  Run the `Judge` to evaluate these conversations against predefined checklists.
    3.  Generate plots visualizing the activity and symptom data from the structured logs.
        Evaluation logs, plots, and performance scores will be saved in the directory specified by `LOGCHAT_LOG_DIR` (default: `logs/`).

  * **Run only the Judge**:
    If you have existing simulation logs and only want to re-run the judgment phase:

    ```bash
    poetry run python tests/judge.py
    ```

  * **Run only the Plotter**:
    To generate persona overview plots from existing database logs:

    ```bash
    poetry run python tests/plotter.py
    ```

A `launch.json` configuration for VS Code is also provided for easier debugging.

## Project Structure

  * `src/`: Core application source code.
      * `app.py`: Main LogChat application class orchestrating the conversational flow.
      * `nodes/`: Implementations of the individual LLM-powered nodes (Planner, Responder, etc.).
      * `prompts.py`: All system and instruction prompts for the core LLM components.
      * `tools/`: Definitive functions that LogChat's agentic components can execute.
      * `database/`: SQLAlchemy models, session management, and master data insertion scripts.
  * `tests/`: The automated evaluation framework.
      * `eval.py`: Main script to run the full simulation and evaluation pipeline.
      * `judge.py`: Script defining the `Judge` agent's logic.
      * `simulator/`: Components for the `Impersonator` agent.
      * `plotter.py`: Script to generate activity/symptom overview plots.
      * `data/eval_dataset.json`: Personas, interaction scenarios, and checklists for evaluation.
      * `prompts.py`: System prompts for the Impersonator and Judge agents.
  * `cli.py`: The command-line interface for interacting with LogChat.
  * `alembic/`: Database migration scripts.
  * `docs/`:
      * **`thesis.pdf`**: The full Master's Thesis document detailing the project's background, design, evaluation, and conclusions.
      * `eval_results/`: Contains detailed, unabridged logs from the evaluation runs, including performance scores and annotated conversations for different LLMs.
  * `logs/`: Default directory for runtime logs, including evaluation outputs.

## Key Thesis Artifacts in this Repository

For those interested in the academic aspects of this project, the following artifacts are of particular interest:

  * **The Full Thesis**: The complete research is documented in `docs/thesis.pdf`.
  * **System Prompts**: All prompts used to guide the LLM components are located in `src/prompts.py`. The prompts for the evaluation agents (Impersonator and Judge) are in `tests/prompts.py`.
  * **Evaluation Dataset**: The structured scenarios used for repeatable evaluation, including persona definitions and detailed interaction checklists, can be found in `tests/data/eval_dataset.json`.
  * **Evaluation Results**: Raw, annotated logs from evaluation runs with different LLMs are stored in `docs/eval_results/`. These files provide a transparent view of each model's performance on a task-by-task basis.
  * **Core Logic**: The primary system orchestration using `LangGraph` is in `src/app.py`, with the individual agentic components defined in `src/nodes/`.

## Disclaimer

LogChat is a research prototype. It is **not a medical device** and should not be used for clinical decision-making or to replace professional medical advice. The system is intended for research and demonstration purposes only.