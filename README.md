# LogChat: A Memory Enhanced Personal Chatbot for ME/CFS Patients

## Overview
LogChat is a master thesis project that focuses on developing a memory-enhanced personal chatbot system designed specifically to support ME/CFS (Myalgic Encephalomyelitis/Chronic Fatigue Syndrome) patients. The system helps patients track symptoms, activities, experiences, and consumption patterns while providing a conversational interface for day-to-day support.

## Architecture
LogChat implements a memory-enhanced architecture using:
- LangGraph for creating a stateful conversation system
- PostgreSQL database for persistent storage of user data and conversation history
- Various Large Language Models (LLMs) for natural language processing

#### Version 1.0.0
- A naive multi-stage processing approach with specialized components:
  - Task Manager: Extracts relevant health information from conversations after each turn
  - Response Generator: Creates appropriate responses based on context and history
- Evaluated with:
  - gemini-2.0-flash

## Features
- Symptom tracking and logging
- Activity monitoring and management
- Experience documentation
- Consumption logging (food, medications, etc.)
- Persistent memory of user interactions
- Context-aware responses that consider past conversations
- Simulated time capability for testing and development

## Project Structure
- `src/`: Core application code
  - `app.py`: Main application logic
  - `database/`: Database models and interaction
  - `node/`: Processing nodes for the conversation graph
  - `tools/`: Specialized tools for updating various logs
- `tests/`: Testing framework including evaluation tools
- `cli/`: Command-line interface
- `alembic/`: Database migration tools

## Research Focus
This project explores how memory-enhanced architectures in conversational AI can provide better support for patients with chronic conditions. The research investigates how persistent, contextual memory in chatbots can improve the quality of care and support for ME/CFS patients by maintaining awareness of their condition history and current state.
