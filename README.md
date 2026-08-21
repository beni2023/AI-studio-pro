# Prompt Architect — Standalone Laptop App

This is a beautiful, elite prompt engineering and system integration workbench built strictly for your laptop. It allows you to transform raw prompts and ideas into highly optimized, structured English prompts, complete with comprehensive architectural breakdowns and ready-to-run API integration code snippets.

## Features
- **Elite Prompt Engineering Heuristics**: Automatically injects structural constraints, context settings, custom output definitions, and Chain of Thought parameters.
- **Universal SDK Code Generator**: Renders copyable Python code tailored directly to your target provider (Gemini, ChatGPT GPT-4o, Claude 3.5, or general requests).
- **Persistent Local Library**: Saves your architected prompts to a local JSON file (`prompt_library.json`) on your laptop so they are never lost.
- **Multilingual Input Processor**: Translates and scales prompts from any language (e.g., Persian) into professional-grade, high-performing English prompts.

---

## How to Run on Your Laptop (Mac, Windows, or Linux)

Ensure you have **Python 3.8+** installed on your laptop, then execute the following simple steps:

### Step 1: Install Dependencies
Open your terminal or command prompt inside the `local_web_app` directory and run:
```bash
pip install -r requirements.txt
```

### Step 2: Launch the App
Run the Flask controller script:
```bash
python app.py
```

### Step 3: Open in Browser
Open your favorite web browser and go to:
```
http://127.0.0.1:5000
```

---

## Configuration & Safety
- **Direct API Call**: This application runs fully locally on your laptop. Your Gemini API Key is never sent to any third party—it is used directly to make calls to Google Generative AI endpoints.
- **Local Storage Key Preservation**: The API Key is securely cached in your local web browser's storage, so you do not have to copy-paste it every time you restart the app.
