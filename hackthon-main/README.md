# Voyager application

Frontend: `frontend/` (Next.js). Backend: `backend/` (FastAPI).

See the [root setup guide](../README.md) for exact Windows commands, port troubleshooting and Groq Free-plan configuration. `python -m pip install -r requirements.txt` also works from this directory.

The dashboard chatbot and co-pilot share the backend Groq client. Set `GROQ_API_KEY` in `backend/.env`; no API key is sent to the browser. Run the frontend with `npm.cmd --prefix frontend run dev`. Start the backend using the root guide's launcher command.

See [EXPERIENCES_IMPLEMENTATION.md](EXPERIENCES_IMPLEMENTATION.md) for the activity catalog handoff.
