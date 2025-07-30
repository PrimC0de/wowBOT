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

    async def _assess_policy_relevance(self, query: str, policy_chunks: List[str]) -> float:
        """Assess how well policy content answers the specific query using LLM."""
        if not policy_chunks:
            return 0.0
        
        try:
            relevance_prompt = """
                You are a relevance assessor. Given a user question and policy content, determine how well the policy content DIRECTLY answers the specific question asked.

                Score from 0.0 to 1.0 where:
                - 0.0-0.3: Policy content doesn't answer the question at all or is completely irrelevant
                - 0.4-0.5: Policy content is somewhat related but doesn't directly answer the question
                - 0.6-0.7: Policy content partially answers the question but lacks specific details
                - 0.8-0.9: Policy content provides a good answer to the question
                - 1.0: Policy content provides a comprehensive and direct answer to the question

                IMPORTANT: Only give high scores (0.8+) if the policy content contains the SPECIFIC answer to the question. General background information, definitions, or procedural overviews are not enough. The content must directly address what the user is asking for.

                Question: "{query}"
                Policy Content:
                {policy_content}

                Respond with only the score (e.g., "0.4").
                """
            combined_policy = "\n\n".join(policy_chunks[:3])
            messages = [
                {"role": "system", "content": relevance_prompt.format(query=query, policy_content=combined_policy)},
                {"role": "user", "content": query}
            ]
            result = await self.openai_service.chat_completion(messages)
            try:
                score = float(result.strip())
                return max(0.0, min(1.0, score))
            except ValueError:
                logger.warning(f"Could not parse relevance score: {result}")
                return 0.5
        except Exception as e:
            logger.error(f"Error assessing policy relevance: {e}")
            return 0.0

    async def process_query(self, query: str) -> str:
        """Process a query through the complete hybrid retrieval pipeline with FAQ fallback."""
        try:
            # Step 1: Translate to Indonesian if needed
            translated_query = await self.openai_service.translate_to_indonesian(query)
            logger.info(f"Original query: {query}")
            logger.info(f"Translated query: {translated_query}")

            # Step 2: Hybrid classification: rule-based for links, AI for others
            link_keywords = [
                'link', 'form', 'where can i find', 'i need the', 'how do i access', 'give me the',
                'pr form', 'oracle', 'catalogue', 'item numbers', 'waiver of competition', 'woc',
                'bpa list', 'catalog', 'procurement tools', 'resources', 'submission form', 'portal', 'system'
            ]
            query_lower = query.lower()
            has_link_keywords = any(keyword in query_lower for keyword in link_keywords)
            if has_link_keywords:
                doc_type = 'links'
                logger.info(f"Hybrid classification: 'links' (keyword detected)")
            else:
                doc_type = await self.openai_service.classify_document_type(translated_query)
            logger.info(f"Classified document type: {doc_type}")

            # Step 3: Retrieve similar chunks from policies (ALWAYS try policies first)
            retrieved_chunks = await self.retrieve_similar_chunks(translated_query, doc_type)
            policy_context = await self.openai_service.rerank_chunks(
                translated_query, retrieved_chunks, TOP_N_RERANK
            )

            # Step 4: Assess policy relevance
            policy_relevance = await self._assess_policy_relevance(translated_query, retrieved_chunks)
            logger.info(f"Policy relevance score: {policy_relevance}")

            # Step 5: Always search for FAQ content as a potential better answer
            faq_context = ""
            logger.info("Searching for FAQ content as potential better answer")
            faq_context = await self._search_faq_content(translated_query)
            if faq_context:
                logger.info(f"FAQ content found: {len(faq_context)} characters")
                logger.info(f"FAQ content preview: {faq_context[:200]}...")
            else:
                logger.warning("No FAQ content found")

            # Step 6: If query is about PR, also retrieve from PR sheet
            sheet_context = ""
            if self._is_pr_query(query):
                pr_rows = self.sheets_service.get_sheet_data("PR")
                relevant_rows = self._find_relevant_pr_rows(query, pr_rows)
                if relevant_rows:
                    sheet_context = "\n\nPR Sheet Data (relevant rows):\n"
                    for row in relevant_rows:
                        sheet_context += str(row) + "\n"

            # Step 7: Combine sources with priority (FAQ first if available, then Policy)
            full_context = ""
            if faq_context:
                full_context += f"FAQ Information (Direct Answer):\n{faq_context}\n\n"
                if policy_context:
                    full_context += f"Additional Policy Context:\n{policy_context}\n\n"
            elif policy_context:
                full_context += f"Policy Information:\n{policy_context}\n\n"
            
            if sheet_context:
                full_context += sheet_context

            return full_context.strip()
            
        except Exception as e:
            logger.error(f"Error in process_query: {e}")
            raise

    async def _search_faq_content(self, query: str) -> str:
        """Search for FAQ content across all document types using semantic similarity."""
        all_faq_chunks = []
        
        # Search across all document types for FAQ content
        for doc_type in ["sop", "pengadaan", "vra", "vmc", "links"]:
            try:
                # Get more chunks to increase chances of finding FAQ content
                chunks = await self.retrieve_similar_chunks(query, doc_type, top_k=20)
                
                # Filter for FAQ content using semantic similarity and Q&A patterns
                faq_chunks = []
                for chunk in chunks:
                    chunk_lower = chunk.lower()
                    
                    # Look for FAQ section headers and Q&A patterns
                    has_faq_header = any(pattern in chunk_lower for pattern in [
                        "frequently asked questions", "## frequently asked questions"
                    ])
                    
                    has_qa_pattern = any(pattern in chunk_lower for pattern in [
                        "**q:", "**a:", "q:", "a:"
                    ])
                    
                    # Include chunk if it has FAQ header OR Q&A pattern
                    if has_faq_header or has_qa_pattern:
                        faq_chunks.append(chunk)
                        logger.info(f"FAQ chunk found in {doc_type}: {chunk[:100]}...")
                
                if faq_chunks:
                    all_faq_chunks.extend(faq_chunks)
                    logger.info(f"Found {len(faq_chunks)} FAQ chunks in {doc_type}")
                    
            except Exception as e:
                logger.error(f"Error searching FAQ content in {doc_type}: {e}")
                continue
        
        # Rerank FAQ chunks to get the most relevant ones
        if all_faq_chunks:
            logger.info(f"Total FAQ chunks found: {len(all_faq_chunks)}")
            return await self.openai_service.rerank_chunks(query, all_faq_chunks, top_n=3)
        
        logger.warning("No FAQ content found")
        return ""

    def get_available_document_types(self) -> List[str]:
        """Get list of available document types."""
        return list(self.faiss_indexes.keys())
    
    def get_chunk_count(self, doc_type: str) -> int:
        """Get the number of chunks for a document type."""
        return len(self.chunks.get(doc_type, [])) 