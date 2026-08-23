# Prompt Architect — Standalone Laptop App

This is a beautiful, elite prompt engineering and system integration workbench built strictly for your laptop. It allows you to transform raw prompts and ideas into highly optimized, structured English prompts, complete with comprehensive architectural breakdowns and ready-to-run API integration code snippets.

## Features
- **Elite Prompt Engineering Heuristics**: Automatically injects structural constraints, context settings, custom output definitions, and Chain of Thought parameters.
- **Universal SDK Code Generator**: Renders copyable Python code tailored directly to your target provider (Gemini, ChatGPT GPT-4o, Claude 3.5, or general requests).
- **Persistent Local Library**: Saves your architected prompts to a local JSON file (`prompt_library.json`) on your laptop so they are never lost.
- **Multilingual Input Processor**: Translates and scales prompts from any language (e.g., Persian) into professional-grade, high-performing English prompts.
- **Smart Model Categorization**: Intelligent filtering and recommendations for different use cases:
  - 💻 **Coding**: Best models for programming and code generation
  - 👁️ **Vision**: Optimal models for image analysis and visual understanding
  - 💬 **Chat**: Ideal models for casual conversation and general Q&A
  - 📊 **Analysis**: Top models for technical analysis and data interpretation
- **Advanced Chat Features**:
  - ✏️ **Edit Messages**: Modify your previous messages and regenerate responses
  - 🔄 **Regenerate**: Regenerate AI responses with a single click
  - 📎 **Image Support**: Attach and analyze images with vision-capable models

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

---

## Usage Guide

### Model Selection & Categories
The app intelligently categorizes available models to help you choose the best one for your task:

1. **Filter by Category**: Click on category buttons (All, Coding, Vision, Chat, Analysis) to filter models
2. **Smart Recommendations**: The app automatically suggests the best model for each category
3. **Model Icons**: Each model displays an icon indicating its primary use case:
   - 💻 for coding-focused models
   - 👁️ for vision/image analysis models
   - 💬 for chat/conversation models
   - 📊 for technical analysis models

### Chat Features
- **Edit Messages**: Click the ✏️ button on any user message to edit it. This will clear subsequent messages and allow you to resend with modifications.
- **Regenerate Response**: Click the 🔄 button on any AI response to generate a new answer for the same prompt.
- **Image Attachments**: Use the attachment button to upload images for analysis with vision-capable models.
- **Copy Code**: Click the copy button on code blocks to instantly copy code to your clipboard.

### Tips for Best Results
- Use **Coding** category models for programming tasks, debugging, and code generation
- Select **Vision** models when working with images, diagrams, or visual content
- Choose **Chat** models for casual conversations, brainstorming, and general questions
- Pick **Analysis** models for technical documentation, data interpretation, and research tasks
