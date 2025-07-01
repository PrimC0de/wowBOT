import logging
from typing import List, Tuple, Dict
import faiss
import numpy as np

from config import FAISS_INDEXES, CHUNK_FILES, TOP_K, TOP_N_RERANK
from services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

class RetrievalService:
    """Service class for all retrieval-related operations."""
    
    def __init__(self):
        self.openai_service = OpenAIService()
        self.faiss_indexes = {}
        self.chunks = {}
        self._load_indexes_and_chunks()
    
    def _load_indexes_and_chunks(self):
        """Load all FAISS indexes and chunk files."""
        for doc_type, index_path in FAISS_INDEXES.items():
            try:
                self.faiss_indexes[doc_type] = faiss.read_index(index_path)
                logger.info(f"Loaded FAISS index for {doc_type}")
            except Exception as e:
                logger.error(f"Failed to load FAISS index for {doc_type}: {e}")
                raise
        
        for doc_type, chunk_path in CHUNK_FILES.items():
            try:
                with open(chunk_path, "r", encoding="utf-8") as f:
                    self.chunks[doc_type] = f.read().split("\n\n")
                logger.info(f"Loaded chunks for {doc_type}: {len(self.chunks[doc_type])} chunks")
            except Exception as e:
                logger.error(f"Failed to load chunks for {doc_type}: {e}")
                raise
    
    def get_chunks_and_index(self, doc_type: str) -> Tuple[faiss.Index, List[str]]:
        """Get the FAISS index and chunk list for a given document type."""
        if doc_type not in self.faiss_indexes or doc_type not in self.chunks:
            logger.warning(f"Document type {doc_type} not found, defaulting to sop")
            doc_type = "sop"
        
        return self.faiss_indexes[doc_type], self.chunks[doc_type]
    
    def retrieve_similar_chunks(self, query: str, doc_type: str = "sop", top_k: int = TOP_K) -> List[str]:
        """Retrieve top K similar chunks for a query and document type."""
        try:
            # Get embedding for the query
            query_embedding = self.openai_service.get_embedding(query)
            query_embedding = query_embedding.reshape(1, -1)
            
            # Get the appropriate index and chunks
            index, chunks = self.get_chunks_and_index(doc_type)
            
            # Search for similar chunks
            distances, indices = index.search(query_embedding, top_k)
            
            # Return the retrieved chunks
            retrieved_chunks = [chunks[i] for i in indices[0] if i < len(chunks)]
            logger.info(f"Retrieved {len(retrieved_chunks)} chunks for doc_type: {doc_type}")
            
            return retrieved_chunks
            
        except Exception as e:
            logger.error(f"Error in retrieve_similar_chunks: {e}")
            raise
    
    def process_query(self, query: str) -> str:
        """Process a query through the complete retrieval pipeline."""
        try:
            # Step 1: Translate to Indonesian if needed
            translated_query = self.openai_service.translate_to_indonesian(query)
            logger.info(f"Original query: {query}")
            logger.info(f"Translated query: {translated_query}")
            
            # Step 2: Classify document type
            doc_type = self.openai_service.classify_document_type(translated_query)
            logger.info(f"Classified document type: {doc_type}")
            
            # Step 3: Retrieve similar chunks
            retrieved_chunks = self.retrieve_similar_chunks(translated_query, doc_type)
            
            # Step 4: Rerank chunks and get top N
            context_text = self.openai_service.rerank_chunks(
                translated_query, retrieved_chunks, TOP_N_RERANK
            )
            
            return context_text
            
        except Exception as e:
            logger.error(f"Error in process_query: {e}")
            raise
    
    def get_available_document_types(self) -> List[str]:
        """Get list of available document types."""
        return list(self.faiss_indexes.keys())
    
    def get_chunk_count(self, doc_type: str) -> int:
        """Get the number of chunks for a document type."""
        return len(self.chunks.get(doc_type, [])) 