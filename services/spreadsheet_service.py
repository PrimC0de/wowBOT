import logging
from typing import List, Dict, Any, Optional
import re

from services.google_sheets_service import GoogleSheetsService
from services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

class SpreadsheetService:
    """Service for handling spreadsheet-based queries and analysis."""
    
    def __init__(self):
        self.sheets_service = GoogleSheetsService()
        self.openai_service = OpenAIService()
    
    def detect_spreadsheet_query(self, query: str) -> bool:
        """Detect if a query is asking about spreadsheet data."""
        spreadsheet_keywords = [
            'data', 'spreadsheet', 'table', 'list', 'records', 'database',
            'find', 'search', 'show me', 'get', 'retrieve', 'lookup',
            'vendor', 'company', 'nama perusahaan', 'contact', 'email',
            'phone', 'address', 'status', 'information', 'details'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in spreadsheet_keywords)
    
    def extract_search_terms(self, query: str) -> List[str]:
        """Extract potential search terms from the query."""
        # Remove common words and extract meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'about', 'what', 'who', 'where', 'when', 'why', 'how', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        
        # Extract words (alphanumeric sequences)
        words = re.findall(r'\b[a-zA-Z0-9]+\b', query.lower())
        
        # Filter out stop words and short words
        search_terms = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Also look for quoted strings (exact matches)
        quoted_terms = re.findall(r'"([^"]*)"', query)
        search_terms.extend(quoted_terms)
        
        return search_terms
    
    async def search_spreadsheet_data(self, query: str, worksheet_name: Optional[str] = None) -> str:
        """Search spreadsheet data and return formatted results."""
        try:
            # Extract search terms from the query
            search_terms = self.extract_search_terms(query)
            logger.info(f"Extracted search terms: {search_terms}")
            
            if not search_terms:
                # If no specific terms, try to get some general data
                data = self.sheets_service.get_all_data(worksheet_name)
                limited_data = data[:5]  # Show first 5 records
                return self.sheets_service.format_data_for_context(limited_data, max_rows=5)
            
            # Search for each term and combine results
            all_matches = []
            for term in search_terms:
                matches = self.sheets_service.search_data(term, worksheet_name)
                all_matches.extend(matches)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_matches = []
            for item in all_matches:
                # Create a simple hash from the row data
                item_hash = hash(str(sorted(item.items())))
                if item_hash not in seen:
                    seen.add(item_hash)
                    unique_matches.append(item)
            
            logger.info(f"Found {len(unique_matches)} unique matching records")
            
            # Format the results
            return self.sheets_service.format_data_for_context(unique_matches, max_rows=10)
            
        except Exception as e:
            logger.error(f"Error searching spreadsheet data: {e}")
            return f"Sorry, I encountered an error while searching the spreadsheet: {str(e)}"
    
    async def get_spreadsheet_summary(self) -> str:
        """Get a summary of the spreadsheet structure and data."""
        try:
            # Get worksheet names
            worksheets = self.sheets_service.get_worksheet_names()
            
            # Get column names from main sheet
            columns = self.sheets_service.get_column_names()
            
            # Get row count
            all_data = self.sheets_service.get_all_data()
            row_count = len(all_data)
            
            summary = f"""Spreadsheet Summary:
- Available worksheets: {', '.join(worksheets)}
- Main sheet columns: {', '.join(columns)}
- Total records in main sheet: {row_count}

Sample data:"""
            
            # Add a few sample records
            sample_data = all_data[:3] if all_data else []
            if sample_data:
                for i, record in enumerate(sample_data, 1):
                    summary += f"\n\nSample Record {i}:"
                    for key, value in record.items():
                        if value:  # Only show non-empty values
                            summary += f"\n  {key}: {value}"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting spreadsheet summary: {e}")
            return f"Sorry, I encountered an error while getting the spreadsheet summary: {str(e)}"
    
    async def answer_with_spreadsheet_data(self, query: str, spreadsheet_context: str) -> str:
        """Use OpenAI to answer a question based on spreadsheet data."""
        try:
            # Create a specialized prompt for spreadsheet queries
            system_prompt = """You are a helpful assistant that answers questions based on spreadsheet data. 
            Use the provided spreadsheet data to answer the user's question accurately. 
            If the data contains the answer, provide it clearly and concisely.
            If the data doesn't contain enough information to answer the question, say so.
            Format your response in a clear, readable way."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Spreadsheet data:\n{spreadsheet_context}\n\nQuestion: {query}"}
            ]
            
            response = await self.openai_service.chat_completion(messages)
            return response
            
        except Exception as e:
            logger.error(f"Error generating answer with spreadsheet data: {e}")
            return f"Sorry, I encountered an error while processing your question: {str(e)}"