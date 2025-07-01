import logging
from typing import Optional, Dict, Any

from services.retrieval_service import RetrievalService
from services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

class ChatbotService:
    """Main service class that controls the chatbot functionality."""
    
    def __init__(self):
        self.retrieval_service = RetrievalService()
        self.openai_service = OpenAIService()
    
    def process_user_message(self, user_message: str) -> str:
        """Process a user message and return a response."""
        try:
            # Extract the actual prompt from the Slack message
            prompt = self._extract_prompt_from_message(user_message)
            
            if not prompt:
                return "Hi! Please ask me something after mentioning me."
            
            # Check if it's a vendor question (future feature)
            vendor_info = self._check_vendor_question(prompt)
            if vendor_info:
                return self._handle_vendor_question(vendor_info)
            
            # Process the query through retrieval pipeline
            context_text = self.retrieval_service.process_query(prompt)
            
            # Generate response using the context
            response = self.openai_service.generate_response(context_text, prompt)
            
            logger.info(f"Generated response for prompt: {prompt[:100]}...")
            return response
            
        except Exception as e:
            logger.error(f"Error processing user message: {e}")
            return "❌ Sorry, I had trouble answering that."
    
    def _extract_prompt_from_message(self, user_message: str) -> str:
        """Extract the actual prompt from Slack."""
        try:
            # Remove the bot mention part
            if ">" in user_message:
                prompt = user_message.split(">", 1)[-1].strip()
            else:
                prompt = user_message.strip()
            return prompt
        except Exception as e:
            logger.error(f"Error extracting prompt: {e}")
            return ""
    
    def _check_vendor_question(self, prompt: str) -> Optional[Dict[str, str]]:
        """Check if the prompt is asking about a vendor."""
        try:
            return self.openai_service.extract_vendor_info(prompt)
        except Exception as e:
            logger.warning(f"Error checking vendor question: {e}")
            return None
    
    def _handle_vendor_question(self, vendor_info: Dict[str, str]) -> str:
        """Handle vendor-related questions (placeholder for future implementation)."""
        # This is a placeholder for vendor handling logic
        # You can implement this when you're ready to use vendor data
        vendor_name = vendor_info.get("vendor", "Unknown")
        risk_type = vendor_info.get("type", "Unknown")
        
        return (
            f"Vendor question detected for {vendor_name} ({risk_type.upper()}). "
            "Vendor lookup functionality is currently disabled. "
            "Please contact procurement@superbank.id for vendor information."
        )
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status information."""
        try:
            return {
                "available_document_types": self.retrieval_service.get_available_document_types(),
                "chunk_counts": {
                    doc_type: self.retrieval_service.get_chunk_count(doc_type)
                    for doc_type in self.retrieval_service.get_available_document_types()
                },
                "status": "operational"
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"status": "error", "message": str(e)} 