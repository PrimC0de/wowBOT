import logging
from services.google_sheets_service import GoogleSheetsService
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def get_vendor_data(vendor_name: str) -> List[Dict[str, Any]]:
    """Get vendor data from Google Sheets for a given vendor name."""
    try:
        sheets_service = GoogleSheetsService()
        return sheets_service.get_vendor_data(vendor_name)
    except Exception as e:
        logger.error(f"Error getting vendor data for {vendor_name}: {e}")
        return []

