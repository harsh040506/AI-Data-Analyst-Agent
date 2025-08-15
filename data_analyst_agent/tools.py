import pandas as pd
import requests
import docker
import os
import tempfile
from logger_setup import log


def web_scraper(url: str) -> pd.DataFrame:
    log.info(f"Using basic web_scraper for URL: {url}")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        tables = pd.read_html(response.content)
        if not tables:
            raise ValueError("No HTML tables found on this page.")
        log.info(f"Successfully scraped {len(tables)} table(s). Returning the first one.")
        return tables[0]
    except Exception as e:
        log.error(f"Basic web_scraper failed for URL {url}.", exc_info=True)
        raise


def python_interpreter(code: str, data: pd.DataFrame = None, filename: str = None) -> tuple[str, pd.DataFrame]:
    log.info("Preparing to execute code in sandboxed environment...")
    log.debug(f"Code to be executed:\n{code}")

    with tempfile.TemporaryDirectory() as temp_dir:
        input_filename = filename if filename else "data.csv"
        input_data_path = os.path.join(temp_dir, input_filename)
        output_data_path = os.path.join(temp_dir, "modified_data.csv")
        script_path = os.path.join(temp_dir, "script.py")

        script_code_lines = ["import pandas as pd", "import json", "import re", "from io import BytesIO",
                             "import base64", "import numpy as np"]

        if data is not None and isinstance(data, pd.DataFrame):
            data.to_csv(input_data_path, index=False)
            if not filename:
                log.info(f"Loading data from previous step into 'df' from {input_filename}")
                script_code_lines.append(f"df = pd.read_csv('/app/{input_filename}')\n")
            else:
                log.info(f"Made file '{filename}' available. Expecting LLM code to load it.")

        script_code_lines.append(code)

        json_dump_code = """
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        return super(NumpyEncoder, self).default(obj)

if 'final_answer' in locals():
    print(json.dumps(final_answer, cls=NumpyEncoder))
"""
        script_code_lines.append(json_dump_code)

        script_code_lines.append(
            "\nif 'df' in locals() and isinstance(df, pd.DataFrame):\n    df.to_csv('/app/modified_data.csv', index=False)"
        )

        with open(script_path, "w", encoding="utf-8") as f:
            f.write("\n".join(script_code_lines))

        client = docker.from_env()
        try:
            container = client.containers.run(
                "python:3.10-slim-data-analyst",
                command=f"python /app/script.py",
                volumes={temp_dir: {'bind': '/app', 'mode': 'rw'}},
                working_dir="/app",
                remove=True, detach=False, stdout=True, stderr=True
            )
            stdout = container.decode('utf-8').strip()
            log.info(f"Interpreter stdout: {stdout[:500]}...")

            modified_df = None
            if os.path.exists(output_data_path):
                modified_df = pd.read_csv(output_data_path)
                log.info("Found modified dataframe. Reading back state.")
            elif data is not None and filename:
                modified_df = data

            return stdout, modified_df
        except docker.errors.ContainerError as e:
            error_message = e.stderr.decode('utf-8').strip()
            log.error(f"Error executing code in Docker. STDERR:\n{error_message}")
            raise RuntimeError(f"Code execution failed: {error_message}")


def build_docker_image():
    log.info("Checking for sandbox Docker image...")
    client = docker.from_env()
    try:
        client.images.get("python:3.10-slim-data-analyst")
        log.info("Docker image already exists.")
    except docker.errors.ImageNotFound:
        log.info("Docker image not found. Building... (This may take a minute)")
        try:
            client.images.build(path=".", dockerfile="Dockerfile", tag="python:3.10-slim-data-analyst")
            log.info("Docker image built successfully.")
        except Exception as e:
            log.error(f"FATAL: Failed to build Docker image. Ensure Docker Desktop is running.", exc_info=True)
            raise