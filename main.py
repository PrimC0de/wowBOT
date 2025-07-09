# main.py

import logging
from fastapi import FastAPI, Request
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

from config import HOST, PORT, ASSISTANT_PROMPT
from services.chatbot_service import ChatbotService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
chatbot_service = ChatbotService()

# Initialize Slack and FastAPI
slack_app = AsyncApp()
slack_handler = AsyncSlackRequestHandler(slack_app)
app = FastAPI(title="Superbank Procurement Assistant", version="1.0.0")

# --- Thread-aware conversation history ---
thread_histories = {}  # {thread_ts: [ {"role": "user"/"assistant", "content": ...}, ... ] }

# Helper to add a message to thread history
def add_to_thread_history(thread_ts, role, content, max_turns=6):
    if thread_ts not in thread_histories:
        thread_histories[thread_ts] = []
    thread_histories[thread_ts].append({"role": role, "content": content})
    thread_histories[thread_ts] = thread_histories[thread_ts][-max_turns:]

# Helper to get concatenated thread context
def get_thread_context(thread_ts):
    history = thread_histories.get(thread_ts, [])
    # Optionally, only use user messages or alternate user/assistant turns
    context = " ".join([turn["content"] for turn in history])
    return context

@app.post("/slack/events")
async def slack_events(req: Request):
    """Handle Slack events."""
    return await slack_handler.handle(req)

@slack_app.event("app_mention")
async def handle_mention(event, say, logger):
    """Handle Slack app mentions."""
    try:
        user_message = event["text"]
        thread_ts = event.get("thread_ts") or event["ts"]

        # Add user message to thread history
        add_to_thread_history(thread_ts, "user", user_message)

        # Build contextual query from thread history
        contextual_query = get_thread_context(thread_ts)

        # Use contextual_query for retrieval
        context = chatbot_service.retrieval_service.process_query(contextual_query)

        # Build LLM messages with thread history
        messages = [{"role": "system", "content": ASSISTANT_PROMPT}]
        messages.extend(thread_histories[thread_ts])
        messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{user_message}"})

        # Generate answer using OpenAIService
        answer = chatbot_service.openai_service.chat_completion(messages)

        # Add bot answer to thread history
        add_to_thread_history(thread_ts, "assistant", answer)

        await say(answer, thread_ts=thread_ts)
        logger.info("Response sent successfully")
        
    except Exception as e:
        logger.error(f"Error handling mention: {e}")
        await say("❌ Sorry, I had trouble answering that.", thread_ts=event.get("thread_ts") or event["ts"])

@slack_app.command("/hello-bolt-python")
async def command(ack, body, respond):
    """Handle Slack slash commands."""
    await ack()
    await respond(f"Hi <@{body['user_id']}>!")

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Superbank Procurement Assistant is running!"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        status = chatbot_service.get_system_status()
        return {"status": "healthy", "details": status}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.get("/status")
async def get_status():
    """Get detailed system status."""
    return chatbot_service.get_system_status()

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Superbank Procurement Assistant...")
    uvicorn.run(app, host=HOST, port=PORT)
