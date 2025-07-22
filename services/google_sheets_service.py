import logging
from typing import List, Dict, Any, Optional
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEETS_CREDENTIALS, GOOGLE_SHEETS_ID

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """Service for interacting with Google Sheets for vendor data."""
    def __init__(self):
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDENTIALS, scopes=scopes)
            client = gspread.authorize(creds)
            self.spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
            self.sheet = self.spreadsheet.sheet1
            logger.info("Google Sheets connection established.")
        except Exception as e:
            logger.error(f"Failed to initialize GoogleSheetsService: {e}")
            raise

    def get_all_data(self, worksheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all data from the specified worksheet or main sheet."""
        try:
            if worksheet_name:
                worksheet = self.spreadsheet.worksheet(worksheet_name)
            else:
                worksheet = self.sheet
            
            records = worksheet.get_all_records()
            logger.info(f"Retrieved {len(records)} records from {'worksheet: ' + worksheet_name if worksheet_name else 'main sheet'}.")
            return records
        except Exception as e:
            logger.error(f"Error retrieving all data: {e}")
            return []

    def search_data(self, query: str, worksheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for data across all columns that contains the query string."""
        try:
            records = self.get_all_data(worksheet_name)
            matching_rows = []
            
            query_lower = query.lower()
            for record in records:
                # Search across all values in the record
                if any(query_lower in str(value).lower() for value in record.values()):
                    matching_rows.append(record)
            
            logger.info(f"Found {len(matching_rows)} records matching query '{query}'.")
            return matching_rows
        except Exception as e:
            logger.error(f"Error searching data: {e}")
            return []

    def get_vendor_data(self, vendor_name: str) -> List[Dict[str, Any]]:
        """Return all vendor records matching the vendor_name (case-insensitive substring match)."""
        try:
            records = self.sheet.get_all_records()
            vendor_rows = [r for r in records if vendor_name.lower() in r.get("Nama Perusahaan", "").lower()]
            logger.info(f"Found {len(vendor_rows)} records for vendor '{vendor_name}'.")
            return vendor_rows
        except Exception as e:
            logger.error(f"Error retrieving vendor data: {e}")
            return []

    def get_column_names(self, worksheet_name: Optional[str] = None) -> List[str]:
        """Get all column names from the specified worksheet."""
        try:
            if worksheet_name:
                worksheet = self.spreadsheet.worksheet(worksheet_name)
            else:
                worksheet = self.sheet
            
            headers = worksheet.row_values(1)  # Get first row (headers)
            logger.info(f"Retrieved {len(headers)} column names.")
            return headers
        except Exception as e:
            logger.error(f"Error retrieving column names: {e}")
            return []

    def format_data_for_context(self, data: List[Dict[str, Any]], max_rows: int = 10) -> str:
        """Format spreadsheet data into a readable text format for the LLM context."""
        if not data:
            return "No matching data found in the spreadsheet."
        
        # Limit the number of rows to avoid context overflow
        limited_data = data[:max_rows]
        
        # Format the data
        formatted_text = "Spreadsheet Data:\n\n"
        
        for i, row in enumerate(limited_data, 1):
            formatted_text += f"Record {i}:\n"
            for key, value in row.items():
                if value:  # Only include non-empty values
                    formatted_text += f"  {key}: {value}\n"
            formatted_text += "\n"
        
        if len(data) > max_rows:
            formatted_text += f"... and {len(data) - max_rows} more records.\n"
        
        return formatted_text

    def append_feedback(self, user: str, channel: str, thread_ts: str, feedback: str, question: str, answer: str):
        """Append a feedback entry to the Feedback worksheet (or main sheet if Feedback does not exist)."""
        try:
            # Try to use a worksheet named 'Feedback', else use the main sheet
            try:
                worksheet = self.spreadsheet.worksheet('Feedback')
            except Exception:
                worksheet = self.sheet
            worksheet.append_row([
                user, channel, thread_ts, feedback, question, answer
            ])
            logger.info(f"Appended feedback from user {user} to Google Sheets.")
        except Exception as e:
            logger.error(f"Error appending feedback: {e}")

    def get_worksheet_names(self) -> List[str]:
        """Get all worksheet names in the spreadsheet."""
        try:
            worksheets = self.spreadsheet.worksheets()
            names = [ws.title for ws in worksheets]
            logger.info(f"Found {len(names)} worksheets: {names}")
            return names
        except Exception as e:
            logger.error(f"Error retrieving worksheet names: {e}")
            return [] 