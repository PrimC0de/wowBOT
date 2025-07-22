# Google Sheets Integration Setup Guide

This guide will help you set up your Slackbot to answer questions based on your Google Sheets data.

## Prerequisites

1. Access to Google Cloud Console
2. Your Google Sheets document
3. Proper environment variables configured

## Step 1: Create Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

4. Create a service account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the service account details
   - Click "Create and Continue"
   - Skip role assignment for now
   - Click "Done"

5. Generate a key for the service account:
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create New Key"
   - Choose "JSON" format
   - Download the JSON file and save it as `credentials.json` in your project root

## Step 2: Configure Google Sheets Access

1. Open your Google Sheets document
2. Copy the Sheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit#gid=0
   ```
   
3. Share the sheet with your service account:
   - In your Google Sheets, click "Share"
   - Add the service account email (found in the JSON file under "client_email")
   - Give it "Editor" permissions

## Step 3: Set Environment Variables

Create a `.env` file in your project root with the following variables:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Google Sheets Configuration
GOOGLE_SHEETS_CREDENTIALS=credentials.json
GOOGLE_SHEETS_ID=your-sheet-id-from-step-2
```

## Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 5: Test the Integration

1. Start your bot:
   ```bash
   python main.py
   ```

2. Test the health endpoint:
   ```bash
   curl http://localhost:3000/health
   ```

3. Check the status endpoint to verify Google Sheets connection:
   ```bash
   curl http://localhost:3000/status
   ```

## Step 6: Test in Slack

Once your bot is running, try these example queries in Slack:

- `@yourbot show me the spreadsheet data`
- `@yourbot find information about [company name]`
- `@yourbot search for [any term from your spreadsheet]`
- `@yourbot what data do you have?`

## How It Works

The bot will automatically detect when a query is asking about spreadsheet data based on keywords like:
- data, spreadsheet, table, list, records
- find, search, show me, get, retrieve, lookup
- vendor, company, contact, email, phone, address
- And more...

When a spreadsheet query is detected, the bot will:
1. Extract search terms from your question
2. Search across all columns in your spreadsheet
3. Format the results and use AI to provide a natural language answer

## Troubleshooting

### Common Issues:

1. **"Failed to initialize GoogleSheetsService"**
   - Check that your `credentials.json` file is in the correct location
   - Verify the service account email has access to the spreadsheet

2. **"Error retrieving data"**
   - Confirm the `GOOGLE_SHEETS_ID` is correct
   - Make sure the Google Sheets API is enabled in your Google Cloud project

3. **"No matching data found"**
   - The search terms might not match any data in your spreadsheet
   - Try using different keywords or check your spreadsheet content

### Debugging:

Check the logs for detailed error messages. The bot logs all operations including:
- Query detection
- Search term extraction
- Spreadsheet searches
- AI responses

## Advanced Configuration

You can customize the behavior by modifying these settings in `config.py`:

```python
# Spreadsheet Configuration
SPREADSHEET_QUERY_THRESHOLD = 0.7  # Confidence threshold for detecting spreadsheet queries
MAX_SPREADSHEET_RESULTS = 10  # Maximum number of spreadsheet results to show
```

## Spreadsheet Data Structure

Your spreadsheet can have any column structure. The bot will automatically:
- Read all column headers
- Search across all text content
- Format results in a readable way

For best results, ensure your spreadsheet has:
- Clear column headers
- Consistent data formatting
- No completely empty rows in the middle of your data

## Security Notes

- Keep your `credentials.json` file secure and never commit it to version control
- Use environment variables for all sensitive configuration
- Regularly rotate your service account keys
- Limit spreadsheet access to only necessary permissions