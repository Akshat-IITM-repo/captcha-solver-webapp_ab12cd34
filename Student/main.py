# /// script 
# requires-python = '>=3.11'
# dependencies = [
#     "fastapi[standard]",
#     "uvicorn",
#     "requests",
#     "httpx" # Added for cleaner API calls
# ]
# ///

import os
import time
import base64
import requests
import json
import httpx # Used for clean API interaction
from pathlib import Path
from fastapi import FastAPI

# GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
# SECRET_KEY = os.getenv("secret")
# VISIBLE_TYPE = os.getenv("visible_type", "public").lower()  # default: public
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

GITHUB_USERNAME = "Akshat-IITM-repo"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SECRET_KEY = "akshat123"
VISIBLE_TYPE = "public"
OPENAI_BASE_URL = "https://aipipe.org/openai/v1/"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
app = FastAPI()

# ----------------------------
# LLM Generation Logic (Core)
# ----------------------------

import subprocess
from pathlib import Path
import base64

def generate_llm_code(brief: str, sample_png_b64: str = None) -> str:
    """
    Generates code by invoking the 'llm' CLI in single-line, non-interactive mode.
    """

    # System message describing the LLM behavior
    system_prompt = (
        "You are an expert web developer specializing in single-file responsive "
        "HTML/JavaScript applications using modern, clean code. "
        "Output must be a self-contained HTML file. Use Tailwind CDN. "
        "Do NOT use alert(). Make it concise and professional. "
        "Your response MUST start with <!DOCTYPE html> and end with </html>, and contain ONLY the code. "
        
        # === CRITICAL ADDITION: Enforce JavaScript logic for image loading ===
        "The HTML MUST include a <script> block at the end of the <body>. "
        "This script MUST retrieve the 'url' query parameter (e.g., from '?url=...') "
        "and dynamically set the 'src' attribute of the main image element. "
        "If the URL parameter is missing, use the simple placeholder image: 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7' "
        "to prevent broken image icons."
        # ====================================================================
    )

    # User message describing the task
    user_prompt = f"Create a single-page captcha solver app for the following brief: '{brief}'."

    # Inform the LLM that an image is available to inform the design
    if sample_png_b64:
        user_prompt += (
            "\nNote: A sample captcha image named 'sample.png' exists. Design the app to load "
            "the image dynamically from the URL parameter (?url=...) and **DO NOT include the base64 content** "
            "in the final HTML output."
        )

    # Combine system + user messages into a single prompt
    full_prompt = f"{system_prompt}\n{user_prompt}"

    # Convert multi-line prompt into a single line by replacing newlines
    full_prompt_single_line = " ".join(full_prompt.splitlines()).strip()

    try:
        # Run the LLM CLI in single-line, non-interactive mode
        result = subprocess.run(
            ["llm", "--model", "gpt-4o-mini", full_prompt_single_line],
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout.strip()
        if not output:
            raise Exception("LLM CLI returned empty output")
        return output

    except subprocess.CalledProcessError as e:
        # CLI failed
        raise Exception(f"LLM CLI failed:\n{e.stderr}") from e

def write_code_with_llm(data: dict, output_dir="temp_app"):
    """
    Generates all necessary files using the LLM and saves them locally.
    Includes robust fallback logic.
    """

    import os
    import base64
    from pathlib import Path

    os.makedirs(output_dir, exist_ok=True)
    brief = data.get("brief", "Minimal app generated")
    attachments = data.get("attachments", [])

    # --------------------------
    # Helper: safe Base64 decode
    # --------------------------
    def safe_b64decode(data_str):
        data_str = data_str.strip()
        missing_padding = len(data_str) % 4
        if missing_padding != 0:
            data_str += '=' * (4 - missing_padding)
        return base64.b64decode(data_str)

    # --------------------------
    # 1. Decode Attachments (find sample.png for LLM)
    # --------------------------
    sample_png_b64 = None
    for attach in attachments:
        name = attach["name"]
        url = attach["url"]
        if url.startswith("data:"):
            try:
                header, encoded = url.split(",", 1)
                content = safe_b64decode(encoded)
                path = Path(output_dir, name)
                with open(path, "wb") as f:
                    f.write(content)
                print(f"✅ Saved attachment: {name}")

                # Capture the base64 content for the LLM
                if name == "sample.png":
                    sample_png_b64 = encoded

            except Exception as e:
                print(f"⚠️ Failed to decode {name}: {e}")

    # --------------------------
    # 2. Generate index.html (LLM or Fallback)
    # --------------------------
    try:
        html_content = generate_llm_code(brief, sample_png_b64)
        print(f"✅ Code generated successfully via LLM.")

        # === FIX IMPLEMENTED HERE: Strip any surrounding text/markdown ===
        start_tag = "<!DOCTYPE html>"
        end_tag = "</html>"

        # Find the start and end of the HTML structure (case-insensitive search)
        lower_content = html_content.lower()
        start_index = lower_content.find(start_tag.lower())
        end_index = lower_content.find(end_tag.lower())

        if start_index != -1 and end_index != -1:
            # Slice the content from the start tag up to and including the end tag
            html_content = html_content[start_index : end_index + len(end_tag)].strip()
        # =================================================================

    except Exception as e:
        print(f"❌ LLM generation failed ({e}). Falling back to safe HTML template.")
        html_content = generate_safe_html(brief)

    # Save the generated (or fallback) HTML
    Path(output_dir, "index.html").write_text(html_content)

    # --------------------------
    # 3. Generate README.md
    # --------------------------
    readme_content = f"""# {data.get('task', 'Task')}
## Summary
{brief}

## Setup
This is a single-page application. Run locally by opening `index.html` in your browser and append `?url=[CAPTCHA_IMAGE_URL]` to the address.

## Code Explanation
The application uses client-side JavaScript to read the image URL from the query parameter and dynamically renders the image for solving.

## License
MIT License.
"""
    Path(output_dir, "README.md").write_text(readme_content)

    # --------------------------
    # 4. Generate LICENSE
    # --------------------------
    mit_license = """MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy...
"""
    Path(output_dir, "LICENSE").write_text(mit_license)

    print(f"✅ Generated all project files in '{output_dir}'.")
    return output_dir


def generate_safe_html(brief: str) -> str:
    """Fallback function to generate a guaranteed, basic HTML page."""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Captcha Solver (Fallback)</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex flex-col items-center justify-center min-h-screen">
    <div class="bg-white p-8 rounded-lg shadow-xl max-w-lg w-full">
        <h1 class="text-2xl font-bold mb-4 text-gray-800">Solver App</h1>
        <p class="text-gray-600 mb-6">{brief}</p>
        
        <div id="captcha-container" class="bg-gray-200 p-4 rounded-lg flex justify-center items-center h-48 mb-4">
            <p class="text-gray-500">Image placeholder (Check URL parameter)</p>
        </div>

        <div id="solver-output" class="text-xl font-mono text-green-600">
            Awaiting input...
        </div>
        
        <p class="mt-4 text-xs text-red-500">Note: LLM generation failed. Showing safe fallback HTML.</p>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const urlParams = new URLSearchParams(window.location.search);
            const imageUrl = urlParams.get('url');

            const container = document.getElementById('captcha-container');
            if (imageUrl) {{
                container.innerHTML = `<img src="${{imageUrl}}" alt="Captcha Image" class="max-w-full max-h-full rounded-md shadow-md"/>`;
            }}
        }});
    </script>
</body>
</html>
"""

# ----------------------------
# Utility functions
# ----------------------------

def validate_secret(secret: str) -> bool:
    return secret == SECRET_KEY

def create_github_repo(repo_name: str):
    payload = {
        "name": repo_name,
        "private": False,
        "auto_init": True,
        "license_template": "mit"
    }
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    res = requests.post("https://api.github.com/user/repos", headers=headers, json=payload)

    if res.status_code == 201:
        print(f"✅ Repository '{repo_name}' created")
        return res.json()
    elif res.status_code == 422:
        errors = res.json().get("errors", [])
        if any(err.get('message') == 'name already exists on this account' for err in errors):
            print(f"⚠️ Repository '{repo_name}' already exists, continuing")
            return {"status": "exists", "repo_name": repo_name}
    else:
        raise Exception(f"Failed to create repo: {res.text}")
    return {"status": "exists", "repo_name": repo_name} # Fallthrough guarantee

def set_repo_visibility(repo_name: str):
    if VISIBLE_TYPE not in ["public", "private"]:
        raise ValueError(f"Invalid VISIBLE_TYPE: {VISIBLE_TYPE}")
    
    make_public = VISIBLE_TYPE == "public"
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}"
    payload = {"private": not make_public}
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.patch(url, headers=headers, json=payload)

    if res.status_code == 200:
        print(f"✅ Repo visibility set to {VISIBLE_TYPE}")
    else:
        raise Exception(f"❌ Failed to set visibility: {res.text}")

def enable_github_pages(repo_name: str):
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/pages"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    payload = {"build_type": "legacy", "source": {"branch": "main", "path": "/"}}

    # 1. Attempt to UPDATE the Pages site configuration (PUT)
    res = requests.put(url, headers=headers, json=payload)
    if res.status_code == 404:
        # Fallback: Attempt to CREATE the Pages site (POST)
        print(f"Pages not found, attempting initial creation (POST)...")
        res = requests.post(url, headers=headers, json=payload)

    # --- Check final status codes (from PUT or POST) ---
    if res.status_code in [201, 202, 204]:
        print(f"✅ GitHub Pages enabled for '{repo_name}'")
    elif res.status_code == 409:
        print(f"⚠️ GitHub Pages already configured")
    elif res.status_code == 422 and "plan does not support GitHub Pages" in res.text:
        print(f"⚠️ Cannot enable Pages due to plan limitation")
        return {"error": "plan limitation"}
    else:
        raise Exception(f"Failed to enable Pages: {res.status_code} - {res.text}")


def push_files_to_repo(repo_name: str, data: dict):
    """
    Push local files from write_code_with_llm() to GitHub repo using GitHub API.
    """
    output_dir = write_code_with_llm(data)
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    branch = "main"

    # 1. Get latest commit SHA
    res_ref = requests.get(f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/git/ref/heads/{branch}", headers=headers)
    if res_ref.status_code != 200:
        raise Exception(f"Cannot get branch ref: {res_ref.status_code} - {res_ref.text}")
    sha_latest_commit = res_ref.json()["object"]["sha"]

    # 2. Get base tree SHA
    res_commit = requests.get(f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/git/commits/{sha_latest_commit}", headers=headers)
    if res_commit.status_code != 200:
        raise Exception(f"Cannot get commit info: {res_commit.status_code} - {res_commit.text}")
    base_tree_sha = res_commit.json()["tree"]["sha"]

    # 3. Create blobs for each file
    blobs = []
    for file_name in os.listdir(output_dir):
        path = os.path.join(output_dir, file_name)
        # Skip directories
        if os.path.isdir(path):
            continue

        with open(path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode()

        res_blob = requests.post(
            f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/git/blobs",
            headers=headers,
            json={"content": content_b64, "encoding": "base64"}
        )

        if res_blob.status_code != 201:
            raise Exception(f"Failed to create blob for '{file_name}': {res_blob.status_code} - {res_blob.text}")

        blobs.append({"path": file_name, "mode": "100644", "type": "blob", "sha": res_blob.json()["sha"]})

    # 4. Create new tree
    res_tree = requests.post(
        f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/git/trees",
        headers=headers,
        json={"base_tree": base_tree_sha, "tree": blobs}
    )

    if res_tree.status_code != 201:
        raise Exception(f"Failed to create tree: {res_tree.status_code} - {res_tree.text}")
    new_tree_sha = res_tree.json()["sha"]

    # 5. Create new commit
    res_commit_new = requests.post(
        f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/git/commits",
        headers=headers,
        json={"message": "LLM Generated App (Round 1)", "tree": new_tree_sha, "parents": [sha_latest_commit]}
    )

    if res_commit_new.status_code != 201:
        raise Exception(f"Failed to create commit: {res_commit_new.status_code} - {res_commit_new.text}")
    new_commit_sha = res_commit_new.json()["sha"]

    # 6. Update branch reference
    res_update = requests.patch(
        f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/git/refs/heads/{branch}",
        headers=headers,
        json={"sha": new_commit_sha}
    )

    if res_update.status_code not in [200, 201]:
        raise Exception(f"Failed to update branch: {res_update.status_code} - {res_update.text}")

    print(f"✅ Pushed files to repo '{repo_name}' successfully")
    return new_commit_sha

# ----------------------------
# Evaluation Callback
# ----------------------------

def post_evaluation_callback(data: dict, repo_name: str, commit_sha: str):
    evaluation_url = data.get("evaluation_url")
    
    # Construct the JSON payload for the Instructor API
    payload = {
        "email": data.get("email"),
        "task": data.get("task"),
        "round": data.get("round"),
        "nonce": data.get("nonce"),
        "repo_url": f"https://github.com/{GITHUB_USERNAME}/{repo_name}",
        "commit_sha": commit_sha,
        "pages_url": f"https://{GITHUB_USERNAME}.github.io/{repo_name}/"
    }
    
    if not evaluation_url or "example.com" in evaluation_url:
        print("⚠️ Skipping callback: No valid evaluation URL provided.")
        return

    delay = 1
    for attempt in range(5):
        try:
            res = requests.post(evaluation_url, json=payload, timeout=5)
            if res.status_code == 200:
                print(f"✅ Evaluation callback successful (Status 200) after {attempt+1} attempts.")
                return
            else:
                print(f"⚠️ Callback attempt {attempt+1} failed: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"⚠️ Callback attempt {attempt+1} exception: {e}")
        
        if attempt < 4: # Wait only before the final attempt
            time.sleep(delay)
            delay *= 2

    print(f"⚠️ All callback attempts failed for {evaluation_url}")


def round1(data: dict):
    repo_name = f"{data['task']}_{data['nonce']}"
    
    # 1. Create Repo (or confirm existence)
    create_github_repo(repo_name)
    
    # 2. Generate Code and Push Files
    try:
        commit_sha = push_files_to_repo(repo_name, data)
    except Exception as e:
        print(f"❌ FATAL ERROR during file push: {e}")
        return {"error": "Deployment failed during commit/push."}

    # 3. Set Visibility & Enable Pages
    pages_enabled = None
    if data.get("enable_pages", True):
        try:
            set_repo_visibility(repo_name)
            pages_enabled = enable_github_pages(repo_name)
        except Exception as e:
            print(f"❌ FATAL ERROR during Pages setup: {e}")
            return {"error": "GitHub Pages setup failed."}
    
    # If Pages setup returned a non-critical error (like plan limitation), propagate it
    if pages_enabled and pages_enabled.get("error"):
        return {"message": "Round 1 task processed with warnings.", "warning": pages_enabled["error"]}

    # 4. Send Evaluation Callback
    post_evaluation_callback(data, repo_name, commit_sha)
    return {"message": "Round 1 task processed"}


def round2(data: dict):
    repo_name = f"{data['task']}_{data['nonce']}"
    
    # 1. Generate Revised Code and Push Files
    try:
        commit_sha = push_files_to_repo(repo_name, data)
    except Exception as e:
        print(f"❌ FATAL ERROR during R2 push: {e}")
        return {"error": "Deployment failed during commit/push for Round 2."}
        
    # 2. Ensure Pages and Visibility are set (idempotent calls)
    try:
        set_repo_visibility(repo_name)
        pages_enabled = enable_github_pages(repo_name)
    except Exception as e:
        print(f"❌ FATAL ERROR during R2 Pages setup: {e}")
        return {"error": "GitHub Pages setup failed for Round 2."}

    # 3. Send Evaluation Callback
    post_evaluation_callback(data, repo_name, commit_sha)
    return {"message": "Round 2 task processed"}

# ----------------------------
# FastAPI Endpoint
# ----------------------------

@app.post("/handle_task")
def handle_task(data: dict):
    if not validate_secret(data.get("secret", "")):
        return {"error": "Invalid secret"}

    round_num = data.get("round")
    
    if round_num == 1:
        result = round1(data)
    elif round_num == 2:
        result = round2(data)
    else:
        return {"error": "Invalid round"}
        
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
