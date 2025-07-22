#!/usr/bin/env python3
"""
Test script for Google Sheets integration.
Run this script to verify your Google Sheets setup is working properly.
"""

import asyncio
import logging
from services.google_sheets_service import GoogleSheetsService
from services.spreadsheet_service import SpreadsheetService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_google_sheets_connection():
    """Test the basic Google Sheets connection."""
    print("🔍 Testing Google Sheets connection...")
    
    try:
        sheets_service = GoogleSheetsService()
        print("✅ Google Sheets service initialized successfully")
        
        # Test getting worksheet names
        worksheets = sheets_service.get_worksheet_names()
        print(f"📊 Found worksheets: {worksheets}")
        
        # Test getting column names
        columns = sheets_service.get_column_names()
        print(f"📋 Column names: {columns}")
        
        # Test getting all data (limited to first 3 rows)
        all_data = sheets_service.get_all_data()
        print(f"📈 Total records: {len(all_data)}")
        
        if all_data:
            print("\n📄 Sample data (first 3 records):")
            for i, record in enumerate(all_data[:3], 1):
                print(f"  Record {i}:")
                for key, value in record.items():
                    if value:  # Only show non-empty values
                        print(f"    {key}: {value}")
                print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Google Sheets connection: {e}")
        return False

async def test_spreadsheet_service():
    """Test the spreadsheet service functionality."""
    print("\n🔍 Testing Spreadsheet Service...")
    
    try:
        spreadsheet_service = SpreadsheetService()
        print("✅ Spreadsheet service initialized successfully")
        
        # Test getting summary
        summary = await spreadsheet_service.get_spreadsheet_summary()
        print("📊 Spreadsheet Summary:")
        print(summary)
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Spreadsheet Service: {e}")
        return False

async def test_search_functionality():
    """Test the search functionality with sample queries."""
    print("\n🔍 Testing Search Functionality...")
    
    try:
        spreadsheet_service = SpreadsheetService()
        
        # Test queries
        test_queries = [
            "show me all data",
            "find company information",
            "search for vendors"
        ]
        
        for query in test_queries:
            print(f"\n🔎 Testing query: '{query}'")
            
            # Test query detection
            is_spreadsheet_query = spreadsheet_service.detect_spreadsheet_query(query)
            print(f"  Detected as spreadsheet query: {is_spreadsheet_query}")
            
            if is_spreadsheet_query:
                # Test search
                results = await spreadsheet_service.search_spreadsheet_data(query)
                print(f"  Search results preview: {results[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing search functionality: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Starting Google Sheets Integration Tests\n")
    print("="*60)
    
    # Test 1: Basic connection
    test1_passed = await test_google_sheets_connection()
    
    # Test 2: Spreadsheet service
    test2_passed = await test_spreadsheet_service()
    
    # Test 3: Search functionality
    test3_passed = await test_search_functionality()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY:")
    print(f"  Google Sheets Connection: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"  Spreadsheet Service: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print(f"  Search Functionality: {'✅ PASS' if test3_passed else '❌ FAIL'}")
    
    all_passed = test1_passed and test2_passed and test3_passed
    
    if all_passed:
        print("\n🎉 All tests passed! Your Google Sheets integration is ready.")
        print("💡 You can now use your bot to answer questions based on your spreadsheet data.")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")
        print("📖 Refer to SPREADSHEET_SETUP.md for troubleshooting help.")

if __name__ == "__main__":
    asyncio.run(main())