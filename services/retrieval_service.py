import logging
from typing import List, Tuple, Dict
import faiss
import numpy as np

from config import FAISS_INDEXES, CHUNK_FILES, TOP_K, TOP_N_RERANK
from services.openai_service import OpenAIService
from services.google_sheets_service import GoogleSheetsService

logger = logging.getLogger(__name__)

class RetrievalService:
    """Service class for all retrieval-related operations."""
    
    def __init__(self):
        self.openai_service = OpenAIService()
        self.faiss_indexes = {}
        self.chunks = {}
        self._load_indexes_and_chunks()
        self.sheets_service = GoogleSheetsService()
    
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
    
    async def retrieve_similar_chunks(self, query: str, doc_type: str = "sop", top_k: int = TOP_K) -> List[str]:
        """Retrieve top K similar chunks for a query and document type."""
        try:
            # Get embedding for the query
            query_embedding = await self.openai_service.get_embedding(query)
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

    def _is_pr_query(self, query: str) -> bool:
        """Detect if the query is about PR (purchase request) or related sheets."""
        lowered = query.lower()
        return ("pr " in lowered or lowered.startswith("pr") or "purchase request" in lowered or "purchase requisition" in lowered)

    def _find_relevant_pr_rows(self, query: str, sheet_data: List[Dict]) -> List[Dict]:
        import re
        pr_number_match = re.search(r"pr\s*#?\s*(\d+)", query.lower())
        if pr_number_match:
            pr_number = pr_number_match.group(1)
            return [row for row in sheet_data if str(row.get("Request #", "")).strip() == pr_number][:10]
        # Use all words longer than 2 chars as keywords
        keywords = [kw for kw in re.findall(r'\w+', query.lower()) if len(kw) > 2]
        relevant_rows = []
        # First, try to match all keywords
        for row in sheet_data:
            row_text = ' '.join(str(v).lower() for v in row.values())
            if all(kw in row_text for kw in keywords):
                relevant_rows.append(row)
        # If no rows match all keywords, try any keyword
        if not relevant_rows:
            for row in sheet_data:
                row_text = ' '.join(str(v).lower() for v in row.values())
                if any(kw in row_text for kw in keywords):
                    relevant_rows.append(row)
        return relevant_rows[:10] if relevant_rows else sheet_data[-5:]

    async def process_query(self, query: str) -> str:
        """Process a query through the complete hybrid retrieval pipeline."""
        try:
            # Step 1: Translate to Indonesian if needed
            translated_query = await self.openai_service.translate_to_indonesian(query)
            logger.info(f"Original query: {query}")
            logger.info(f"Translated query: {translated_query}")

            # Step 2: Classify document type
            doc_type = await self.openai_service.classify_document_type(translated_query)
            logger.info(f"Classified document type: {doc_type}")

            # Step 3: Retrieve similar chunks from policies
            retrieved_chunks = await self.retrieve_similar_chunks(translated_query, doc_type)
            context_text = await self.openai_service.rerank_chunks(
                translated_query, retrieved_chunks, TOP_N_RERANK
            )

            # Step 4: If query is about PR, also retrieve from PR sheet
            sheet_context = ""
            if self._is_pr_query(query):
                pr_rows = self.sheets_service.get_sheet_data("PR")
                relevant_rows = self._find_relevant_pr_rows(query, pr_rows)
                if relevant_rows:
                    sheet_context = "\n\nPR Sheet Data (relevant rows):\n"
                    for row in relevant_rows:
                        sheet_context += str(row) + "\n"

            # Step 5: Combine both sources
            full_context = context_text
            if sheet_context:
                full_context += sheet_context
            return full_context
        except Exception as e:
            logger.error(f"Error in process_query: {e}")
            raise

    def get_available_document_types(self) -> List[str]:
        """Get list of available document types."""
        return list(self.faiss_indexes.keys())
    
    def get_chunk_count(self, doc_type: str) -> int:
        """Get the number of chunks for a document type."""
        return len(self.chunks.get(doc_type, [])) 