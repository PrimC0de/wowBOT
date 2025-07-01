import json
import re
import logging
from typing import List, Dict, Optional, Tuple
import openai
import numpy as np

from config import (
    OPENAI_API_KEY, OPENAI_MODEL, EMBEDDING_MODEL,
    CLASSIFIER_PROMPT, TRANSLATOR_PROMPT, RERANK_PROMPT,
    VENDOR_EXTRACTOR_PROMPT, ASSISTANT_PROMPT
)

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service class for all OpenAI API interactions."""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for a text using OpenAI's embedding model."""
        try:
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text
            )
            return np.array(response.data[0].embedding).astype("float32")
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise
    
    def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        """Make a chat completion request to OpenAI."""
        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=temperature,
                messages=messages
            )
            content = response.choices[0].message.content
            if content is None:
                logger.warning("OpenAI returned None content")
                return ""
            return content.strip()
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise
    
    def classify_document_type(self, prompt: str) -> str:
        """Classify the document type for a given prompt."""
        messages = [
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        result = self.chat_completion(messages)
        logger.info(f"Document classification result: {result}")
        
        if "sop" in result.lower():
            return "sop"
        elif "pengadaan" in result.lower():
            return "pengadaan"
        elif "vra" in result.lower():
            return "vra"
        else:
            return "vmc"
    
    def translate_to_indonesian(self, text: str) -> str:
        """Translate text to Indonesian."""
        messages = [
            {"role": "system", "content": TRANSLATOR_PROMPT},
            {"role": "user", "content": text}
        ]
        return self.chat_completion(messages)
    
    def rerank_chunks(self, query: str, chunks: List[str], top_n: int = 3) -> str:
        """Rerank chunks by relevance to the query and return top N as combined text."""
        scored_chunks = []
        
        for i, chunk in enumerate(chunks):
            prompt = (
                f"Question:\n{query}\n\n"
                f"Chunk:\n{chunk}\n\n"
                "On a scale of 1 to 10, how relevant is this chunk to the question? "
                "Only respond with the number (no explanation)."
            )
            
            messages = [
                {"role": "system", "content": RERANK_PROMPT},
                {"role": "user", "content": prompt}
            ]
            
            try:
                score_text = self.chat_completion(messages)
                match = re.search(r"\b([1-9]|10)\b", score_text)
                score = int(match.group()) if match else 0
            except Exception as e:
                logger.warning(f"Error scoring chunk {i}: {e}")
                score = 0
            
            scored_chunks.append((score, chunk))
        
        # Sort by score descending and return top N chunks
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_chunks = [chunk for score, chunk in scored_chunks[:top_n]]
        
        return "\n\n".join(top_chunks)
    
    def extract_vendor_info(self, prompt: str) -> Optional[Dict[str, str]]:
        """Extract vendor and risk type information from a prompt."""
        messages = [
            {"role": "system", "content": VENDOR_EXTRACTOR_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        try:
            result = self.chat_completion(messages)
            return json.loads(result)
        except Exception as e:
            logger.warning(f"Vendor extraction failed: {e}")
            return None
    
    def generate_response(self, context: str, question: str) -> str:
        """Generate a response using the assistant prompt and context."""
        messages = [
            {"role": "system", "content": ASSISTANT_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{question}"}
        ]
        return self.chat_completion(messages) 