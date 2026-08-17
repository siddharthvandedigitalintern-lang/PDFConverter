# Notes Ninja Auto-Redesigner API & Web Tool

The main application runs as a FastAPI service on port 8000. It extracts text from an educational PDF, uses Gemini to structure it sequentially (to avoid rate limits), and compiles the results into a beautiful document using the Notes Ninja WeasyPrint template kit.

## Processing Flow

`PDF Upload` ➔ `Text & Segment Extraction` ➔ `Gemini Structural Analysis (Sequential with Auto-Retry)` ➔ `Awaiting Cover Review` ➔ `WeasyPrint PDF Generation`

## Setup & Running

1. **Install Dependencies:**
   Ensure you have FastAPI and Uvicorn installed in your virtual environment:
   ```powershell
   .venv\Scripts\pip install fastapi uvicorn python-multipart
   .venv\Scripts\pip install -r requirements.txt
   ```

2. **Configure Environment:**
   Set up your `GEMINI_API_KEY` and WeasyPrint paths in the `.env` file.

3. **Start the Server:**
   ```powershell
   .venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

4. **Access the Web Interface:**
   Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your web browser.

## Key Features

- **Sequential Processing:** Units are processed one-by-one with cooldown delays to be gentle on Gemini Free Tier rate limits.
- **Smart Quota Retry:** If the Gemini API returns a `429 RESOURCE_EXHAUSTED` error, the app parses the exact wait time required and sleeps automatically before retrying, preventing processing failures.
- **Cover Page Review:** Allows reviewing and editing cover configuration metadata before committing to full rendering.
