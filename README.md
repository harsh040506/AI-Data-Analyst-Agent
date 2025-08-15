# AI Data Analyst Agent

This is the official repository for the AI Data Analyst Agent. The project implements a sophisticated, multimodal agent that exposes a powerful API endpoint to dynamically source, prepare, analyze, and visualize data from various sources, including CSVs, Excel files, websites, and even images, using Google's Gemini LLM.

The agent is built on a robust **Planner-Executor** pattern, ensuring a clear separation between reasoning (the LLM's plan) and action (code execution). All user-requested code is run in a **secure, isolated Docker sandbox** to prevent security risks.

## Features

-   **Dynamic Task Planning:** The LLM generates a custom, step-by-step plan to answer any data analysis question.
-   **Multimodal Analysis:** Can process and reason about data from multiple sources in a single request:
    -   **Tabular Data:** Full support for `.csv` and `.xlsx` (Excel) files.
    -   **Image Recognition:** Can analyze charts, graphs, and tables within `.png`, `.jpg`, and `.jpeg` files.
    -   **Web Scraping:** Capable of fetching and parsing tables directly from URLs.
-   **Secure, Sandboxed Execution:** All LLM-generated code is executed in an isolated Docker container, protecting the host system from any potential harm.
-   **State Management:** The agent maintains the state of the data (as a pandas DataFrame) across multiple steps in its plan.
-   **Robust Error Handling:** The system is designed to handle common data type issues (e.g., NumPy `int64` serialization) and LLM response inconsistencies.

## Architecture Overview

The agent operates on a simple but powerful workflow that separates planning from execution.

```mermaid
graph TD
    A[User Request via API] -- POST with files --> B{Flask Server (app.py)};
    B -- Extracts Schema & Image Data --> C[Prompt Generation];
    C -- Sends multimodal prompt --> D[Planner (Gemini LLM)];
    D -- Returns JSON plan --> B;
    B -- Executes each step --> E{Executor (tools.py)};
    subgraph E [Tools]
        F[python_interpreter in Docker]
        G[web_scraper]
    end
    E -- Returns final result --> B;
    B -- Sends JSON response --> H[User];```

1.  **The Planner (Gemini):** Receives the user's questions, along with the schema of any uploaded data files and the content of any images. It generates a multi-step JSON plan to solve the task.
2.  **The Executor (`app.py`):** The Flask server parses the JSON plan and executes each step in sequence using a predefined set of tools.
3.  **The Tools (`tools.py`):**
    -   `web_scraper`: Fetches initial data from a URL.
    -   `python_interpreter`: The core tool. It executes LLM-generated Python code in the secure Docker sandbox.

## Prerequisites

Before you begin, ensure you have the following installed:

-   **Python 3.10+**
-   **Docker Desktop:** Must be installed and running.
-   **Git**

## Setup & Installation

Follow these steps to get the application running locally.

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/harsh040506/AI-Data-Analyst-Agent.git
    cd AI-Data-Analyst-Agent
    ```

2.  **Create and Activate a Python Virtual Environment**
    ```bash
    # For Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies**
    This will install all necessary Python libraries for both the host server and the Docker sandbox.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure API Keys**
    The application is currently hardcoded to use the API key within `app.py`. Ensure the `GEMINI_API_KEYS` list contains your valid key.

5.  **Build the Sandbox Environment**
    The application will automatically build the necessary Docker image on its first run. You can also build it manually:
    ```bash
    # (Optional) Manual build
    docker build -t python:3.10-slim-data-analyst .
    ```

## Running the Application

Once the setup is complete, start the Flask API server:

```bash
flask run --host=0.0.0.0 --port=5000
```

The server will be accessible at `http://127.0.0.1:5000`.

## API Usage

The application exposes a single endpoint: `POST /api/`. You must send a `multipart/form-data` request containing a `questions.txt` file and any optional data or image files.

The form field name for each file **must be the filename itself**.

### Example `curl` Commands

**Analyzing a CSV file:**

```bash
curl "http://127.0.0.1:5000/api/" \
  -F "questions.txt=@my_questions.txt" \
  -F "sales_data.csv=@path/to/your/sales_data.csv"
```

**Analyzing an Image and a CSV file:**

```bash
curl "http://127.0.0.1:5000/api/" \
  -F "questions.txt=@my_questions_about_image.txt" \
  -F "chart.png=@path/to/your/chart.png" \
  -F "user_data.csv=@path/to/your/user_data.csv"
```

**Analyzing an Excel file:**

```bash
curl "http://127.0.0.1:5000/api/" \
  -F "questions.txt=@my_excel_questions.txt" \
  -F "report.xlsx=@path/to/your/report.xlsx"
```

## Making the API Publicly Accessible (for Testing)

To allow others to test your locally running API, you can use `ngrok`.

1.  **Download and install ngrok:** [https://ngrok.com/download](https://ngrok.com/download)
2.  **Authenticate ngrok** (one-time setup):
    ```bash
    ngrok config add-authtoken <YOUR_NGROK_TOKEN>
    ```
3.  With your Flask app running, open a **new terminal** and run:
    ```bash
    ngrok http 5000
    ```
4.  `ngrok` will provide a public `https://` URL. Share this URL with your tester. It will securely forward all requests to your local application.

## Project Structure

```
.
├── diagnostics/         # Logs and artifacts for each API request are saved here.
├── .venv/               # Python virtual environment directory.
├── app.py               # Main Flask application, orchestrator, and API endpoint.
├── tools.py             # Defines the agent's capabilities (python_interpreter, web_scraper).
├── prompts.py           # Contains the master prompt with generalized patterns for the LLM.
├── logger_setup.py      # Configures application-wide logging.
├── Dockerfile           # Defines the secure sandbox environment for code execution.
├── requirements.txt     # Lists all Python dependencies for the project.
├── README.md            # This file.
└── LICENSE              # MIT License file.
```

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
