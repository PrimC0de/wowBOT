# main.py

import logging
from fastapi import FastAPI, Request
import os
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

from config import HOST, PORT, ASSISTANT_PROMPT
from services.chatbot_service import ChatbotService
import asyncio
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
chatbot_service = ChatbotService()

# Load Slack tokens from environment
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]

# Initialize Slack app in Socket Mode
slack_app = AsyncApp(token=SLACK_BOT_TOKEN)

# Initialize FastAPI (for non-Slack endpoints)
app = FastAPI(title="Superbank Procurement Assistant", version="1.0.0")

# --- Thread-aware conversation history ---
thread_histories = {} 

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

def markdown_to_slack(text):
    """Convert Markdown bold (**bold**) to Slack bold (*bold*), _italic_ to _italic_, and [text](url) to <url|text>."""
    # Convert **bold** to *bold*
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    # Convert _italic_ (Markdown) to _italic_ (Slack)
    text = re.sub(r'_(.*?)_', r'_\1_', text)
    # Convert [text](url) to <url|text> for Slack
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<\2|\1>', text)
    return text

@slack_app.event("app_mention")
async def handle_mention(event, say, logger):
    """Handle Slack app mentions."""
    try:
        user_message = event["text"]
        thread_ts = event.get("thread_ts") or event["ts"]
        user_id = event.get("user", None)

        # Add user message to thread history
        add_to_thread_history(thread_ts, "user", user_message)

        # Build contextual query from thread history
        contextual_query = get_thread_context(thread_ts)

        # Use contextual_query for retrieval
        context = await chatbot_service.retrieval_service.process_query(contextual_query)

        # Build LLM messages with thread history
        messages = [{"role": "system", "content": ASSISTANT_PROMPT}]
        messages.extend(thread_histories[thread_ts])
        messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{user_message}"})

        # Generate answer using OpenAIService
        answer = await chatbot_service.openai_service.chat_completion(messages)

        # Add bot answer to thread history
        add_to_thread_history(thread_ts, "assistant", answer)

        # Prepend user_id 
        if user_id:
            display_text = f"<@{user_id}>\n" + answer
        else:
            display_text = answer

        # Convert Markdown to Slack formatting
        display_text = markdown_to_slack(display_text)

        # Send the answer with feedback buttons using Block Kit
        await say(
            text=display_text,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": display_text
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "👍 Helpful"},
                            "style": "primary",
                            "value": "helpful",
                            "action_id": "feedback_helpful"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "👎 Not Helpful"},
                            "style": "danger",
                            "value": "not_helpful",
                            "action_id": "feedback_not_helpful"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "💬 Give Feedback"},
                            "value": "give_feedback",
                            "action_id": "feedback_text"
                        }
                    ]
                }
            ],
            thread_ts=thread_ts
        )
        logger.info("Response sent successfully")
        
    except Exception as e:
        logger.error(f"Error handling mention: {e}")
        await say("❌ Sorry, I had trouble answering that.", thread_ts=event.get("thread_ts") or event["ts"])

# Feedback button handlers
@slack_app.action("feedback_helpful")
async def handle_helpful_feedback(ack, body, client):
    await ack()
    user = body["user"]["id"]
    channel = body["channel"]["id"]
    thread_ts = body.get("message", {}).get("thread_ts") or body.get("message", {}).get("ts")
    await client.chat_postEphemeral(
        channel=channel,
        user=user,
        text="Thanks for your feedback!",
        thread_ts=thread_ts
    )

@slack_app.action("feedback_not_helpful")
async def handle_not_helpful_feedback(ack, body, client):
    await ack()
    user = body["user"]["id"]
    channel = body["channel"]["id"]
    thread_ts = body.get("message", {}).get("thread_ts") or body.get("message", {}).get("ts")
    await client.chat_postEphemeral(
        channel=channel,
        user=user,
        text="Sorry to hear that. Your feedback has been noted.",
        thread_ts=thread_ts
    )

@slack_app.action("feedback_text")
async def open_feedback_modal(ack, body, client):
    await ack()
    trigger_id = body["trigger_id"]
    channel = body["channel"]["id"]
    thread_ts = body.get("message", {}).get("thread_ts") or body.get("message", {}).get("ts")
    await client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "submit_feedback",
            "private_metadata": f"{channel}|{thread_ts}",
            "title": {"type": "plain_text", "text": "Feedback"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "feedback_input",
                    "label": {"type": "plain_text", "text": "Your feedback"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "feedback"
                    }
                }
            ]
        }
    )

@slack_app.view("submit_feedback")
async def handle_feedback_submission(ack, body, view, client, logger):
    await ack()  # Always acknowledge first to avoid Slack UI errors
    user = body["user"]["id"]
    try:
        feedback = view["state"]["values"]["feedback_input"]["feedback"]["value"]
    except KeyError:
        logger.error(f"Feedback key missing in view state: {view['state']['values']}")
        channel, thread_ts = view["private_metadata"].split("|")
        await client.chat_postEphemeral(
            channel=channel,
            user=user,
            text="Sorry, we couldn't read your feedback. Please try again.",
            thread_ts=thread_ts
        )
        return
    channel, thread_ts = view["private_metadata"].split("|")
    # Optionally, get question/answer from thread_histories
    history = thread_histories.get(thread_ts, [])
    question = history[0]["content"] if history else ""
    answer = history[-1]["content"] if history else ""
    # Log feedback to Google Sheets
    try:
        from services.google_sheets_service import GoogleSheetsService
        sheets_service = GoogleSheetsService()
        sheets_service.append_feedback(user, channel, thread_ts, feedback, question, answer)
        await client.chat_postEphemeral(
            channel=channel,
            user=user,
            text="Thank you for your feedback! 💬",
            thread_ts=thread_ts
        )
    except Exception as e:
        logger.error(f"Error saving feedback to Google Sheets: {e}")
        await client.chat_postEphemeral(
            channel=channel,
            user=user,
            text="Sorry, there was an error saving your feedback. Please try again later.",
            thread_ts=thread_ts
        )

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
        status = await chatbot_service.get_system_status()
        return {"status": "healthy", "details": status}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.get("/status")
async def get_status():
    """Get detailed system status."""
    return await chatbot_service.get_system_status()

if __name__ == "__main__":
    async def main():
        logger.info("Starting Superbank Procurement Assistant in Socket Mode...")
        handler = AsyncSocketModeHandler(slack_app, SLACK_APP_TOKEN)
        await handler.start_async()

    asyncio.run(main())
