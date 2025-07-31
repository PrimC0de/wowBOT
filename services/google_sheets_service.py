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

    def update_feedback_count(self, feedback_type: str):
        """Update feedback count in the 'Feedback Count' worksheet."""
        try:
            # Try to get or create the 'Feedback Count' worksheet
            try:
                worksheet = self.spreadsheet.worksheet('Feedback Count')
            except Exception:
                # Create the worksheet if it doesn't exist
                worksheet = self.spreadsheet.add_worksheet(title='Feedback Count', rows=10, cols=5)
                # Add headers
                worksheet.update('A1:C2', [
                    ['Feedback Analytics', '', ''],
                    ['Type', 'Count', 'Total']
                ])
                worksheet.update('A3:B4', [
                    ['Useful', '0'],
                    ['Not Useful', '0']
                ])
            
            # Determine which cell to update based on feedback type
            if feedback_type == "useful":
                cell = "C3"
            elif feedback_type == "not_useful":
                cell = "C4"
            else:
                logger.error(f"Invalid feedback type: {feedback_type}")
                return
            
            # Get current count and increment by 1
            current_value = worksheet.acell(cell).value
            try:
                current_count = int(current_value) if current_value else 0
            except ValueError:
                current_count = 0
            
            new_count = current_count + 1
            worksheet.update(cell, new_count)
            
            logger.info(f"Updated {feedback_type} feedback count to {new_count} in 'Feedback Count' sheet.")
            
        except Exception as e:
            logger.error(f"Error updating feedback count: {e}")

    def process_all_feedback_counts(self):
        """Process all useful/not useful feedback from all sources and update the 'Feedback Count' sheet."""
        try:
            # Initialize counters
            useful_count = 0
            not_useful_count = 0
            
            # Try to get existing feedback count worksheet
            try:
                count_worksheet = self.spreadsheet.worksheet('Feedback Count')
                # Get current counts
                useful_current = count_worksheet.acell('C3').value
                not_useful_current = count_worksheet.acell('C4').value
                
                useful_count = int(useful_current) if useful_current else 0
                not_useful_count = int(not_useful_current) if not_useful_current else 0
                
            except Exception:
                # Create the worksheet if it doesn't exist
                count_worksheet = self.spreadsheet.add_worksheet(title='Feedback Count', rows=10, cols=5)
                # Add headers and initial structure
                count_worksheet.update('A1:C2', [
                    ['Feedback Analytics', '', ''],
                    ['Type', 'Count', 'Total']
                ])
                count_worksheet.update('A3:B4', [
                    ['Useful', '0'],
                    ['Not Useful', '0']
                ])
            
            # Update the counts in the sheet
            count_worksheet.update_acell('C3', useful_count)
            count_worksheet.update_acell('C4', not_useful_count)
            
            logger.info(f"Processed feedback counts - Useful: {useful_count}, Not Useful: {not_useful_count}")
            
        except Exception as e:
            logger.error(f"Error processing all feedback counts: {e}") 