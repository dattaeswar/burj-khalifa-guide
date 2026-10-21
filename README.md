# 🏙️ Burj Khalifa Guide

A specialized, factual web chatbot dedicated exclusively to the construction, engineering, architecture, workforce, and history of the **Burj Khalifa** (828 m).

Its knowledge is strictly grounded in `Burj_Khalifa_Encyclopedia.pdf` using **DeepSeek** (`deepseek-chat`) via the official `openai` Python SDK with Server-Sent Events (SSE) streaming.

---

## ⚡ Quickstart Setup (Under 6 Steps)

### Step 1: Clone or Navigate to the Directory
```bash
cd "chatbot with deepseek"
```

### Step 2: Create and Activate a Virtual Environment
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the example environment file and insert your DeepSeek API key:
```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```
Edit `.env`:
```env
DEEPSEEK_API_KEY=sk-your-actual-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

### Step 5: Ingest the Knowledge Base
Extracts the 12 numbered encyclopedia sections from `Burj_Khalifa_Encyclopedia.pdf` into `data/knowledge_base.md` and `data/chunks.json`:
```bash
python ingest.py
```

### Step 6: Start the Server
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser and navigate to **[http://localhost:8000](http://localhost:8000)**.

---

## 🔄 How to Refresh the Knowledge Base

If you update `Burj_Khalifa_Encyclopedia.pdf` or modify section parsing:
```bash
python ingest.py
```
This automatically updates `data/knowledge_base.md` and `data/chunks.json`. Restart the server to load the updated knowledge base.

---

## 🚀 How to Deploy to Vercel

You can deploy this application directly to **Vercel** with zero extra configuration:

1. Push this repository to **GitHub**.
2. Go to **[vercel.com/new](https://vercel.com/new)** and import your repository.
3. In **Settings -> Environment Variables**, add:
   - `DEEPSEEK_API_KEY` = `your_deepseek_api_key`
   - `DEEPSEEK_BASE_URL` = `https://api.deepseek.com` (optional, default)
   - `DEEPSEEK_MODEL` = `deepseek-chat` (optional, default)
4. Click **Deploy**. Vercel will automatically detect `vercel.json` and `api/index.py`, bundle the Python dependencies, and provide you with a live URL (e.g. `https://your-burj-guide.vercel.app`) to share!

---

## 🏛️ System Features & Security

- **Strict Knowledge Grounding**: Answers only from `Burj_Khalifa_Encyclopedia.pdf`. Out-of-scope questions are politely declined.
- **Source Attribution**: Factual answers cite their exact section (e.g., `Source: Section 4, When Construction Started`).
- **Prompt Injection Defense**: Guarded against instructions to reveal system prompts or bypass topic boundaries.
- **Privacy & Security**: API keys are strictly confined to the backend server environment and are **never** logged, sent to the browser, or included in client assets.
- **Modern Navy & Gold Theme**: Inspired by Dubai's skyline with responsive layouts, typography from Google Fonts (`Outfit` & `Inter`), light/dark theme toggle, and progressive token streaming.
