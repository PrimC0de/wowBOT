import logging
from typing import List, Dict, Any
import gspread
import os
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from config import GOOGLE_SHEETS_ID

logger = logging.getLogger(__name__)

# --- New OAuth 2.0 Authentication ---
def get_oauth_credentials():
    """Gets user credentials using OAuth 2.0 flow."""
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists("token.json"):
        creds = UserCredentials.from_authorized_user_file("token.json")
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret.json",  # Make sure you have this file
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds
# --- End of New Authentication ---

class GoogleSheetsService:
    """Service for interacting with Google Sheets for procurement data."""
    def __init__(self):
        try:
            # --- Use the new OAuth function ---
            creds = get_oauth_credentials()
            client = gspread.authorize(creds)
            if not GOOGLE_SHEETS_ID:
                raise ValueError("GOOGLE_SHEETS_ID is not set in the environment.")
            self.spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)  # <-- Set spreadsheet
            self.sheet = self.spreadsheet.sheet1  # Default to first sheet
            logger.info("Google Sheets connection established using OAuth.")
        except Exception as e:
            logger.error(f"Failed to initialize GoogleSheetsService: {e}")
            raise

    def get_sheet_data(self, sheet_name: str, vendor_name: str = None) -> List[Dict[str, Any]]:
        """Return all records from the specified worksheet as a list of dicts. Optionally filter by vendor_name."""
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            records = worksheet.get_all_records()
            if vendor_name:
                vendor_rows = []
                for r in records:
                    company_name = r.get("Nama Perusahaan", "")
                    if isinstance(company_name, str) and vendor_name.lower() in company_name.lower():
                        vendor_rows.append(r)
                logger.info(f"Found {len(vendor_rows)} records for vendor '{vendor_name}'.")
                return vendor_rows
            return records
        except Exception as e:
            logger.error(f"Error retrieving data from sheet '{sheet_name}': {e}")
            return []

    def append_feedback(self, user: str, channel: str, thread_ts: str, feedback: str, question: str, answer: str):
        """Append a feedback entry to the Feedback worksheet (or main sheet if Feedback does not exist)."""
        try:
            # Try to use a worksheet named 'Feedback', else use the main sheet
            try:
                worksheet = self.spreadsheet.worksheet('Feedback')
            except Exception:
                worksheet = self.spreadsheet.sheet1
            worksheet.append_row([
                user, channel, thread_ts, feedback, question, answer
            ])
            logger.info(f"Appended feedback from user {user} to Google Sheets.")
        except Exception as e:
            logger.error(f"Error appending feedback: {e}")

    def record_vote(self, thread_ts: str, user_id: str, vote_type: str):
        """Record a vote and increment the appropriate counter in 'Feedback Count' sheet."""
        try:
            # Get or create the 'Feedback Count' worksheet
            try:
                feedback_count_sheet = self.spreadsheet.worksheet('Feedback Count')
            except Exception:
                # Create the sheet if it doesn't exist
                feedback_count_sheet = self.spreadsheet.add_worksheet(title='Feedback Count', rows=10, cols=10)
                # Add headers
                feedback_count_sheet.update('A1:D3', [
                    ['', '', 'Count', ''],
                    ['', '', '', ''],
                    ['', '', 'Useful', 'Not Useful']
                ])
                logger.info("Created 'Feedback Count' sheet with headers")
            
            # Get current values from C3 (useful) and C4 (not useful)
            try:
                useful_count = int(feedback_count_sheet.cell(3, 3).value or 0)
                not_useful_count = int(feedback_count_sheet.cell(3, 4).value or 0)
            except (ValueError, TypeError):
                useful_count = 0
                not_useful_count = 0
            
            # Increment the appropriate counter
            if vote_type == "useful":
                useful_count += 1
                feedback_count_sheet.update_cell(3, 3, useful_count)
                logger.info(f"Incremented useful count to {useful_count} in 'Feedback Count' sheet")
            elif vote_type == "not_useful":
                not_useful_count += 1
                feedback_count_sheet.update_cell(3, 4, not_useful_count)
                logger.info(f"Incremented not useful count to {not_useful_count} in 'Feedback Count' sheet")
            
            # Log individual vote in the main Feedback sheet for tracking
            try:
                feedback_sheet = self.spreadsheet.worksheet('Feedback')
            except Exception:
                feedback_sheet = self.spreadsheet.sheet1
            
            feedback_sheet.append_row([
                user_id, thread_ts, vote_type, "vote_record", "", ""
            ])
            logger.info(f"Recorded {vote_type} vote from user {user_id} in feedback log")
            
        except Exception as e:
            logger.error(f"Error recording vote: {e}")

    def has_user_voted(self, thread_ts: str, user_id: str) -> bool:
        """Check if a user has already voted on a specific thread."""
        try:
            # Check in the main Feedback sheet for vote records
            try:
                worksheet = self.spreadsheet.worksheet('Feedback')
            except Exception:
                worksheet = self.spreadsheet.sheet1
            
            # Get all records and check if this user has voted on this thread
            records = worksheet.get_all_records()
            for record in records:
                if (record.get('user', '') == user_id and 
                    record.get('channel', '') == thread_ts and 
                    record.get('feedback', '') == 'vote_record'):
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking if user has voted: {e}")
            return False 