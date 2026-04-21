# resumeagent

> An AI-powered agent system to automatically generate professional resumes from your GitHub data.

## 🧠 Overview

This project leverages a multi-agent architecture to streamline resume creation. It intelligently extracts and processes information from your GitHub profile, embeds this data, and uses a vector database to generate a comprehensive and tailored DOCX resume. The system aims to automate the tedious aspects of resume building, allowing developers to quickly create or update their resumes based on their latest contributions and projects.

## 🔨 What I Built

The `resumeagent` is designed around a series of interconnected AI agents, each handling a specific part of the resume generation pipeline.

-   **GitHub Data Fetching Agent:** Retrieves public repository information and user data from GitHub.
-   **Embedding Agent:** Processes the fetched data into a format suitable for vector storage.
-   **Vector Database Query Agent:** Interacts with a FAISS vector database to retrieve relevant information based on specific queries.
-   **Resume Information Extraction Agent:** Distills key professional details, project summaries, and skills from the processed data.
-   **DOCX Resume Generation Agent:** Compiles the extracted information into a structured and well-formatted DOCX resume document.
-   **API Interaction and Caching:** Manages external API calls and caches responses to optimize performance and reduce redundant requests.

## 💭 Thought Process

My approach focused on breaking down the complex task of resume generation into manageable, specialized AI agents. I chose LangGraph as the orchestrator for its ability to define and manage stateful agent interactions, which is crucial for a multi-step process like this. The integration of a vector database (FAISS) was a key decision to enable efficient semantic search and retrieval of relevant GitHub data. This allows the system to intelligently pull out project details and contributions that best highlight a user's experience. To handle external data, I prioritized robust API interaction with GitHub and incorporated caching to improve response times and reduce API rate limit issues. The use of Pydantic ensures data validation and structured output, which is essential for consistent resume generation.

## 🛠️ Tools & Tech Stack

| Layer       | Technology          |
| :---------- | :------------------ |
| Language    | Python              |
| Framework   | LangGraph, FastAPI  |
| AI / LLM    | Google Generative AI|
| Database    | FAISS (Vector DB)   |
| Data        | NumPy, Pandas       |
| API Client  | Requests            |
| Data Mgmt   | Pydantic, python-dotenv |
| Document Gen| python-docx (inferred) |

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- A Google Generative AI API Key
- A GitHub Personal Access Token (if fetching private repo data, otherwise public data is accessible)

### Installation

```bash
git clone https://github.rashadmin/resumeagent.git
cd resumeagent
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_google_generative_ai_key
GITHUB_TOKEN=your_github_personal_access_token # Optional, for private repos
```

### Run

While the `agent.py` contains the core logic, a typical execution would involve instantiating and running the agents, possibly through a `main.py` or a FastAPI application.

```bash
# Example (assuming an entry point is defined, e.g., main.py or direct agent execution)
python -m agent
```

## 📖 Usage

### Example 1: Generating a Resume (Conceptual)

```python
from agent import ResumeAgent

# Initialize the main resume agent
resume_builder = ResumeAgent(
    google_api_key="your_google_api_key",
    github_token="your_github_token"
)

# Assume a method to trigger the resume generation process
# This would internally call the various agents
docx_output_path = resume_builder.generate_resume(github_username="your-github-username")

print(f"Resume generated at: {docx_output_path}")
```

## 📚 Resources

-   [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction) — Underlying framework for LangGraph
-   [Google Generative AI Docs](https://ai.google.dev/docs) — LLM API reference
-   [FastAPI Documentation](https://fastapi.tiangolo.com/) — Web framework (if used for API)
-   [FAISS GitHub](https://github.com/facebookresearch/faiss) — Vector similarity search library
-   [python-dotenv Documentation](https://pypi.org/project/python-dotenv/) — Managing environment variables
-   [python-docx Documentation](https://python-docx.readthedocs.io/en/latest/) — Creating and updating Microsoft Word files

## 📄 License

MIT © [rashadmin](https://github.com/rashadmin)
