import os
import logging
import numpy as np
import faiss
from typing import List, Optional
import tiktoken

from config import CHUNK_FILES, FAISS_INDEXES, KNOWLEDGE_FILES, EMBEDDING_MODEL, OPENAI_API_KEY
from services.openai_service import OpenAIService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Chunking Functions ---
def split_text_into_chunks(text: str, max_tokens: int = 1200, overlap: int = 150) -> List[str]:
    """Split text into chunks based on token count with overlap."""
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    words = text.split()
    chunks = []
    current_chunk = []
    current_tokens = 0

    for word in words:
        word_tokens = len(encoding.encode(word + " "))
        if current_tokens + word_tokens > max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk = current_chunk[-overlap:]
            current_tokens = sum(len(encoding.encode(w + " ")) for w in current_chunk)
        current_chunk.append(word)
        current_tokens += word_tokens
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

def chunk_knowledge_file(input_path: str, output_path: str, max_tokens: int = 1200, overlap: int = 150):
    """Read a .txt file, split into chunks, and save as .chunks.txt."""
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()
    chunks = split_text_into_chunks(text, max_tokens, overlap)
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(chunk + "\n\n")
    logger.info(f"✅ {input_path} split into {len(chunks)} chunks and saved to {output_path}")


def process_all_knowledge_files(knowledge_map: dict, chunk_map: dict, max_tokens: int = 1200, overlap: int = 150):
    """Process all knowledge .txt files, save chunk files, and print a summary."""
    for doc_type, input_path in knowledge_map.items():
        output_path = chunk_map[doc_type]
        chunk_knowledge_file(input_path, output_path, max_tokens, overlap)
    logger.info("All knowledge files chunked successfully.")

# --- Embedding Functions (unchanged) ---
def load_chunks(chunk_file: str) -> List[str]:
    """Load chunks from a file, splitting by double newlines."""
    with open(chunk_file, "r", encoding="utf-8") as f:
        chunks = f.read().split("\n\n")
    return [chunk.strip() for chunk in chunks if chunk.strip()]

async def generate_embeddings_for_chunks(chunks: List[str], openai_service: OpenAIService) -> np.ndarray:
    """Generate embeddings for a list of chunks using OpenAIService. Uses batch encoding if available."""
    # Try to use batch encoding if the OpenAIService uses Hugging Face
    if hasattr(openai_service, 'hf_model'):
        try:
            import numpy as np
            logger.info(f"Batch encoding {len(chunks)} chunks with Hugging Face model...")
            # Hugging Face models are not async, so run in thread executor
            import asyncio
            loop = asyncio.get_event_loop()
            def encode():
                return openai_service.hf_model.encode(chunks, show_progress_bar=True)
            embeddings = await loop.run_in_executor(None, encode)
            logger.info(f"Batch encoded {len(chunks)} chunks.")
            return np.vstack(embeddings)
        except Exception as e:
            logger.error(f"Batch encoding failed, falling back to per-chunk: {e}")
    # Fallback: per-chunk encoding (async)
    embeddings = []
    for i, chunk in enumerate(chunks):
        try:
            emb = await openai_service.get_embedding(chunk)
            embeddings.append(emb)
            if (i + 1) % 10 == 0 or i == len(chunks) - 1:
                logger.info(f"Embedded {i + 1}/{len(chunks)} chunks...")
        except Exception as e:
            logger.error(f"Failed to embed chunk {i}: {e}")
            embeddings.append(np.zeros((384,), dtype=np.float32))  # fallback for MiniLM
    return np.vstack(embeddings)

def save_faiss_index(embeddings: np.ndarray, index_path: str):
    """Save embeddings to a FAISS index file."""
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    faiss.write_index(index, index_path)
    logger.info(f"Saved FAISS index to {index_path} (dim={dim}, n={embeddings.shape[0]})")

async def process_document_type(doc_type: str, openai_service: OpenAIService):
    """Process a single document type: load chunks, embed, and save FAISS index."""
    chunk_file = CHUNK_FILES[doc_type]
    index_path = FAISS_INDEXES[doc_type]
    logger.info(f"Processing document type: {doc_type}")
    chunks = load_chunks(chunk_file)
    logger.info(f"Loaded {len(chunks)} chunks from {chunk_file}")
    embeddings = await generate_embeddings_for_chunks(chunks, openai_service)
    save_faiss_index(embeddings, index_path)
    logger.info(f"Completed processing for {doc_type}\n")

async def main(doc_types: Optional[List[str]] = None, chunk: bool = False):
    """Main function to optionally chunk knowledge files and generate embeddings/FAISS indexes."""
    # Map of document type to knowledge .txt file
    if chunk:
        logger.info("Chunking knowledge files...")
        process_all_knowledge_files(KNOWLEDGE_FILES, CHUNK_FILES)
    openai_service = OpenAIService()
    if doc_types is None:
        doc_types = list(CHUNK_FILES.keys())
    logger.info(f"Generating embeddings for document types: {doc_types}")
    for doc_type in doc_types:
        await process_document_type(doc_type, openai_service)
    logger.info("All embeddings and indexes generated successfully.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate OpenAI embeddings and FAISS indexes for document chunks.")
    parser.add_argument(
        "--doc_types",
        nargs="*",
        help="List of document types to process (default: all)",
        default=None
    )
    parser.add_argument(
        "--chunk",
        action="store_true",
        help="Run the chunking step before embedding generation."
    )
    args = parser.parse_args()
    import asyncio
    asyncio.run(main(args.doc_types, chunk=args.chunk))
