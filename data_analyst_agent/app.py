from flask import Flask, request, jsonify
import google.generativeai as genai
import json
import os
import datetime
import re
import pandas as pd
import base64
from prompts import PLANNER_PROMPT
from logger_setup import log
from tools import web_scraper, python_interpreter, build_docker_image

app = Flask(__name__)

GEMINI_API_KEYS = [
    "GEMINI_API_KEY_1",
    "GEMINI_API_KEY_2",
]

DIAGNOSTICS_DIR = "diagnostics"
MODEL_NAME = 'gemini-2.0-flash'

if not os.path.exists(DIAGNOSTICS_DIR):
    os.makedirs(DIAGNOSTICS_DIR)


def get_gemini_model_with_retry():
    if not GEMINI_API_KEYS or not any(key.strip() for key in GEMINI_API_KEYS):
        raise ValueError("GEMINI_API_KEYS list is empty.")

    for i, key in enumerate(GEMINI_API_KEYS):
        key = key.strip()
        if not key:
            continue
        try:
            log.info(f"Attempting to configure Gemini API with key #{i + 1}...")
            genai.configure(api_key=key)
            model = genai.GenerativeModel(MODEL_NAME)
            model.generate_content("test", generation_config=genai.types.GenerationConfig(max_output_tokens=1))
            log.info(f"Successfully configured Gemini with key #{i + 1} using {MODEL_NAME}.")
            return model
        except Exception as e:
            log.warning(f"Failed to use Gemini API key #{i + 1}. Error: {e}")

    raise ConnectionError("All provided Gemini API keys failed.")


@app.route('/api/', methods=['POST'])
def analyze_data():
    start_time = datetime.datetime.now()

    try:
        ip_address = request.remote_addr.replace(":", "_")
        timestamp = start_time.strftime("%Y-%m-%d_%H-%M-%S")
        request_diag_folder = os.path.join(DIAGNOSTICS_DIR, f"{ip_address}_{timestamp}")
        os.makedirs(request_diag_folder)
        log.info(f"Created diagnostics folder: {request_diag_folder}")

        if 'questions.txt' not in request.files:
            return jsonify({"error": "questions.txt is a required file."}), 400
        questions = request.files['questions.txt'].read().decode('utf-8')
        with open(os.path.join(request_diag_folder, "01_request_questions.txt"), "w") as f:
            f.write(questions)

        context_data = None
        context_filename = None
        image_contexts = []
        schema_info_parts = []

        for field_name, file_storage in request.files.items():
            if field_name == 'questions.txt':
                continue

            file_name_lower = field_name.lower()
            if file_name_lower.endswith('.csv'):
                log.info(f"Found uploaded CSV file: {field_name}")
                context_data = pd.read_csv(file_storage.stream)
                context_filename = field_name
                schema_info_parts.append(
                    f"a data file named '{field_name}' with columns: {context_data.columns.tolist()}")

            elif file_name_lower.endswith('.xlsx'):
                log.info(f"Found uploaded Excel file: {field_name}")
                context_data = pd.read_excel(file_storage.stream)
                context_filename = field_name
                schema_info_parts.append(
                    f"a data file named '{field_name}' with columns: {context_data.columns.tolist()}")

            elif file_name_lower.endswith(('.png', '.jpg', '.jpeg')):
                log.info(f"Found uploaded image: {field_name}")
                # Extract mime type and encode image for multimodal input
                mime_type = f"image/{file_name_lower.split('.')[-1]}"
                img_base64 = base64.b64encode(file_storage.read()).decode('utf-8')
                image_contexts.append({"mime_type": mime_type, "data": img_base64})
                schema_info_parts.append(f"an image file named '{field_name}'")

        if not schema_info_parts:
            schema_info = "No data or image files were uploaded."
        else:
            schema_info = "The user uploaded " + " and ".join(schema_info_parts) + "."

    except Exception as e:
        log.error("FATAL: Error during setup or request parsing.", exc_info=True)
        return jsonify({"error": f"Internal server error: {e}"}), 500

    try:
        model = get_gemini_model_with_retry()
        text_prompt = PLANNER_PROMPT.format(
            user_questions=questions,
            uploaded_file_schema=schema_info
        )

        # Prepare content for multimodal generation
        content_parts = [text_prompt]
        content_parts.extend(image_contexts)

        generation_config = genai.types.GenerationConfig(
            max_output_tokens=8192,
            temperature=0.1
        )
        response = model.generate_content(content_parts, generation_config=generation_config)

        with open(os.path.join(request_diag_folder, "02_gemini_raw_response.txt"), "w") as f:
            f.write(response.text)

        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if not json_match:
            raise json.JSONDecodeError("No JSON array found in LLM response.", response.text, 0)

        plan_str = json_match.group(0)
        plan = json.loads(plan_str)

        with open(os.path.join(request_diag_folder, "03_gemini_parsed_plan.json"), "w") as f:
            json.dump(plan, f, indent=4)
        log.info(f"Received and parsed a plan with {len(plan)} steps.")
    except Exception as e:
        log.error(f"Failed to get or parse plan from Gemini.", exc_info=True)
        return jsonify({"error": f"Failed to get or parse plan from LLM: {e}"}), 500

    if not plan:
        return jsonify({"error": "LLM generated an empty plan."}), 500

    try:
        final_step_index = len(plan) - 1
        for i, step in enumerate(plan):
            tool_name = step.get("tool")
            args = step.get("args", {})
            is_final_step = (i == final_step_index)
            log.info(f"Executing {'FINAL' if is_final_step else 'INTERMEDIATE'} step {i + 1}: tool='{tool_name}'")

            if (datetime.datetime.now() - start_time).total_seconds() > 280:
                log.error("Execution timed out before completing all steps.")
                return jsonify({"error": "Processing timed out."}), 500

            if tool_name == "web_scraper":
                context_data = web_scraper(url=args.get("url"))
            elif tool_name == "python_interpreter":
                stdout, modified_df = python_interpreter(
                    code=args.get("code"),
                    data=context_data,
                    filename=context_filename
                )
                context_data = modified_df
                context_filename = None

                if is_final_step:
                    log.info("Final step executed. Preparing response.")
                    with open(os.path.join(request_diag_folder, "04_final_step_stdout.txt"), "w") as f:
                        f.write(stdout)
                    try:
                        final_response_obj = json.loads(stdout)
                        with open(os.path.join(request_diag_folder, "05_final_output.json"), "w") as f:
                            json.dump(final_response_obj, f, indent=4)
                        log.info("Request fully processed. Returning final JSON object.")
                        return jsonify(final_response_obj)
                    except json.JSONDecodeError:
                        log.error(f"FATAL: The final step's output was not valid JSON. Output: {stdout}", exc_info=True)
                        return jsonify(
                            {"error": "The agent failed to produce a valid JSON response in the final step."}), 500
            else:
                log.warning(f"Unknown tool '{tool_name}' requested in plan.")
                if is_final_step:
                    return jsonify({"error": f"Final step requested an unknown tool: {tool_name}"}), 500
    except Exception as e:
        log.error(f"Error during plan execution at step {i + 1}.", exc_info=True)
        return jsonify({"error": f"Execution failed: {e}"}), 500

    log.error("Execution loop completed without returning a response from a final step.")
    return jsonify({"error": "Agent finished plan but did not produce a final answer."}), 500


if __name__ == '__main__':
    try:
        build_docker_image()
        app.run(host='0.0.0.0', port=5002, debug=False)
    except Exception as e:

        log.error(f"Failed to start the application.", exc_info=True)
