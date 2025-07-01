# main.py

import logging
from fastapi import FastAPI, Request
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

from config import HOST, PORT
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

@app.post("/slack/events")
async def slack_events(req: Request):
    """Handle Slack events."""
    return await slack_handler.handle(req)

@slack_app.event("app_mention")
async def handle_mention(event, say, logger):
    """Handle Slack app mentions."""
    try:
        user_message = event["text"]
        logger.info(f"Received mention: {user_message}")
        
        # Process the message through the chatbot service
        response = chatbot_service.process_user_message(user_message)
        
        # Send the response back to Slack
        await say(response)
        logger.info("Response sent successfully")
        
    except Exception as e:
        logger.error(f"Error handling mention: {e}")
        await say("❌ Sorry, I had trouble answering that.")

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
