import json
import re
import logging
from typing import List, Dict, Optional
import openai
import numpy as np
import asyncio

from config import (
    OPENROUTER_API_KEY, OPENROUTER_MODEL_OPENAI, OPENROUTER_MODEL_ANTHROPIC, OPENROUTER_MODEL_DEEPSEEK, OPENROUTER_MODEL_LLAMA, OPENROUTER_MODEL_GEMINI,
    OPENAI_API_KEY, OPENAI_MODEL, EMBEDDING_MODEL,
    CLASSIFIER_PROMPT, TRANSLATOR_PROMPT, RERANK_PROMPT,
    VENDOR_EXTRACTOR_PROMPT, ASSISTANT_PROMPT
)

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service class for all OpenRouter API interactions (async version)."""
    
    def __init__(self, max_concurrent_requests: int = 5):
        self.openai_client = openai.AsyncOpenAI(
            api_key=OPENAI_API_KEY
        )
        self.openrouter_client = openai.AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
    
    async def get_embedding(self, text: str) -> np.ndarray:
        async with self.semaphore:
            try:
                response = await self.openai_client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=text
                )
                return np.array(response.data[0].embedding).astype("float32")
            except Exception as e:
                logger.error(f"Error getting embedding: {e}")
                raise
    
    async def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        async with self.semaphore:
            try:
                response = await self.openrouter_client.chat.completions.create(
                    model=OPENROUTER_MODEL_ANTHROPIC,
                    temperature=temperature,
                    messages=messages
                )
                content = response.choices[0].message.content
                if content is None:
                    logger.warning("OpenRouter returned None content")
                    return ""
                return content.strip()
            except Exception as e:
                logger.error(f"Error in chat completion: {e}")
                raise
    
    async def classify_document_type(self, prompt: str) -> str:
        messages = [
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": prompt}
        ]
        result = await self.chat_completion(messages)
        logger.info(f"Document classification result: {result}")
        if "sop" in result.lower():
            return "sop"
        elif "pengadaan" in result.lower():
            return "pengadaan"
        elif "vra" in result.lower():
            return "vra"
        else:
            return "vmc"
    
    async def translate_to_indonesian(self, text: str) -> str:
        messages = [
            {"role": "system", "content": TRANSLATOR_PROMPT},
            {"role": "user", "content": text}
        ]
        return await self.chat_completion(messages)
    
    async def rerank_chunks(self, query: str, chunks: List[str], top_n: int = 3) -> str:
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
                score_text = await self.chat_completion(messages)
                match = re.search(r"\b([1-9]|10)\b", score_text)
                score = int(match.group()) if match else 0
            except Exception as e:
                logger.warning(f"Error scoring chunk {i}: {e}")
                score = 0
            scored_chunks.append((score, chunk))
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_chunks = [chunk for score, chunk in scored_chunks[:top_n]]
        return "\n\n".join(top_chunks)
    
    async def extract_vendor_info(self, prompt: str) -> Optional[Dict[str, str]]:
        messages = [
            {"role": "system", "content": VENDOR_EXTRACTOR_PROMPT},
            {"role": "user", "content": prompt}
        ]
        try:
            result = await self.chat_completion(messages)
            return json.loads(result)
        except Exception as e:
            logger.warning(f"Vendor extraction failed: {e}")
            return None
    
    async def generate_response(self, context: str, question: str) -> str:
        messages = [
            {"role": "system", "content": ASSISTANT_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{question}"}
        ]
        return await self.chat_completion(messages) 