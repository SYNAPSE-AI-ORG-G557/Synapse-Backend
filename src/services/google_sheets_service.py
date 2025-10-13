import asyncio
import gspread
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
import io
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import structlog

log = structlog.get_logger(__name__)

class GoogleSheetsService:
    def __init__(self, user_token: str):
        self.user_token = user_token
        self.credentials = None
        self.gc = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize gspread client with user credentials"""
        try:
            # Create credentials object from user token
            self.credentials = Credentials(
                token=self.user_token,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
            )
            
            # Initialize gspread client
            self.gc = gspread.authorize(self.credentials)
            log.info("Google Sheets client initialized successfully")
            
        except Exception as e:
            log.error(f"Failed to initialize Google Sheets client: {str(e)}")
            raise e
    
    async def create_spreadsheet(self, title: str, sheet_names: List[str] = None) -> Dict[str, Any]:
        """Create a new spreadsheet"""
        try:
            if sheet_names is None:
                sheet_names = ['Sheet1']
            
            # Create spreadsheet
            spreadsheet = self.gc.create(title)
            
            # Rename default sheet and add additional sheets
            if len(sheet_names) > 0:
                spreadsheet.sheet1.update_title(sheet_names[0])
                
                # Add additional sheets
                for i, sheet_name in enumerate(sheet_names[1:], 1):
                    spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=26)
            
            # Share with user (make it accessible)
            spreadsheet.share('', perm_type='anyone', role='writer')
            
            return {
                "success": True,
                "spreadsheet_id": spreadsheet.id,
                "spreadsheet_url": spreadsheet.url,
                "title": title,
                "sheet_names": sheet_names
            }
            
        except Exception as e:
            log.error(f"Error creating spreadsheet: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def open_spreadsheet(self, spreadsheet_id: str) -> Dict[str, Any]:
        """Open an existing spreadsheet by ID"""
        try:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            
            # Get worksheet information
            worksheets = []
            for worksheet in spreadsheet.worksheets():
                worksheets.append({
                    "id": worksheet.id,
                    "title": worksheet.title,
                    "row_count": worksheet.row_count,
                    "col_count": worksheet.col_count
                })
            
            return {
                "success": True,
                "spreadsheet_id": spreadsheet.id,
                "spreadsheet_url": spreadsheet.url,
                "title": spreadsheet.title,
                "worksheets": worksheets
            }
            
        except Exception as e:
            log.error(f"Error opening spreadsheet: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_worksheet_data(self, spreadsheet_id: str, worksheet_title: str = None, range_name: str = None) -> Dict[str, Any]:
        """Get data from a worksheet"""
        try:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            
            if worksheet_title:
                worksheet = spreadsheet.worksheet(worksheet_title)
            else:
                worksheet = spreadsheet.sheet1
            
            if range_name:
                data = worksheet.get(range_name)
            else:
                data = worksheet.get_all_values()
            
            return {
                "success": True,
                "data": data,
                "worksheet_title": worksheet.title,
                "row_count": len(data),
                "col_count": len(data[0]) if data else 0
            }
            
        except Exception as e:
            log.error(f"Error getting worksheet data: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_worksheet_data(self, spreadsheet_id: str, data: List[List[Any]], 
                                  worksheet_title: str = None, range_name: str = None) -> Dict[str, Any]:
        """Update data in a worksheet"""
        try:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            
            if worksheet_title:
                worksheet = spreadsheet.worksheet(worksheet_title)
            else:
                worksheet = spreadsheet.sheet1
            
            if range_name:
                worksheet.update(range_name, data)
            else:
                # Clear existing data and add new data
                worksheet.clear()
                worksheet.update('A1', data)
            
            return {
                "success": True,
                "message": f"Updated {len(data)} rows in worksheet '{worksheet.title}'",
                "rows_updated": len(data)
            }
            
        except Exception as e:
            log.error(f"Error updating worksheet data: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def append_data(self, spreadsheet_id: str, data: List[List[Any]], 
                         worksheet_title: str = None) -> Dict[str, Any]:
        """Append data to the end of a worksheet"""
        try:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            
            if worksheet_title:
                worksheet = spreadsheet.worksheet(worksheet_title)
            else:
                worksheet = spreadsheet.sheet1
            
            # Append rows
            worksheet.append_rows(data)
            
            return {
                "success": True,
                "message": f"Appended {len(data)} rows to worksheet '{worksheet.title}'",
                "rows_appended": len(data)
            }
            
        except Exception as e:
            log.error(f"Error appending data: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_chart(self, spreadsheet_id: str, chart_config: Dict[str, Any], 
                          worksheet_title: str = None) -> Dict[str, Any]:
        """Create a chart in a worksheet"""
        try:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            
            if worksheet_title:
                worksheet = spreadsheet.worksheet(worksheet_title)
            else:
                worksheet = spreadsheet.sheet1
            
            # Create chart using gspread's chart functionality
            chart = worksheet.add_chart(chart_config)
            
            return {
                "success": True,
                "message": f"Chart created in worksheet '{worksheet.title}'",
                "chart_id": chart.get('chartId')
            }
            
        except Exception as e:
            log.error(f"Error creating chart: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def format_cells(self, spreadsheet_id: str, format_config: Dict[str, Any], 
                          worksheet_title: str = None, range_name: str = None) -> Dict[str, Any]:
        """Format cells in a worksheet"""
        try:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            
            if worksheet_title:
                worksheet = spreadsheet.worksheet(worksheet_title)
            else:
                worksheet = spreadsheet.sheet1
            
            if range_name:
                worksheet.format(range_name, format_config)
            else:
                # Format entire worksheet
                worksheet.format('A:Z', format_config)
            
            return {
                "success": True,
                "message": f"Formatted cells in worksheet '{worksheet.title}'"
            }
            
        except Exception as e:
            log.error(f"Error formatting cells: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def add_worksheet(self, spreadsheet_id: str, title: str, rows: int = 1000, cols: int = 26) -> Dict[str, Any]:
        """Add a new worksheet to a spreadsheet"""
        try:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)
            
            return {
                "success": True,
                "message": f"Added worksheet '{title}' to spreadsheet",
                "worksheet_id": worksheet.id,
                "worksheet_title": worksheet.title
            }
            
        except Exception as e:
            log.error(f"Error adding worksheet: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_worksheet(self, spreadsheet_id: str, worksheet_title: str) -> Dict[str, Any]:
        """Delete a worksheet from a spreadsheet"""
        try:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(worksheet_title)
            spreadsheet.del_worksheet(worksheet)
            
            return {
                "success": True,
                "message": f"Deleted worksheet '{worksheet_title}' from spreadsheet"
            }
            
        except Exception as e:
            log.error(f"Error deleting worksheet: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def share_spreadsheet(self, spreadsheet_id: str, email: str, role: str = 'reader') -> Dict[str, Any]:
        """Share a spreadsheet with another user"""
        try:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            spreadsheet.share(email, perm_type='user', role=role)
            
            return {
                "success": True,
                "message": f"Shared spreadsheet with {email} as {role}"
            }
            
        except Exception as e:
            log.error(f"Error sharing spreadsheet: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_spreadsheets(self) -> Dict[str, Any]:
        """List all spreadsheets accessible to the user"""
        try:
            spreadsheets = self.gc.list_spreadsheet_files()
            
            return {
                "success": True,
                "spreadsheets": spreadsheets,
                "count": len(spreadsheets)
            }
            
        except Exception as e:
            log.error(f"Error listing spreadsheets: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "spreadsheets": [],
                "count": 0
            }
    
    async def export_to_csv(self, spreadsheet_id: str, worksheet_title: str = None, 
                           filename: str = None) -> Dict[str, Any]:
        """Export a worksheet to CSV format"""
        try:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            
            if worksheet_title:
                worksheet = spreadsheet.worksheet(worksheet_title)
            else:
                worksheet = spreadsheet.sheet1
            
            # Get all data
            data = worksheet.get_all_values()
            
            # Convert to CSV format
            csv_content = []
            for row in data:
                csv_content.append(','.join(f'"{cell}"' for cell in row))
            
            csv_text = '\n'.join(csv_content)
            
            if not filename:
                filename = f"{spreadsheet.title}_{worksheet.title}.csv"
            
            return {
                "success": True,
                "csv_content": csv_text,
                "filename": filename,
                "row_count": len(data)
            }
            
        except Exception as e:
            log.error(f"Error exporting to CSV: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def import_from_csv(self, spreadsheet_id: str, csv_content: str, 
                             worksheet_title: str = None) -> Dict[str, Any]:
        """Import CSV data into a worksheet"""
        try:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
            
            if worksheet_title:
                worksheet = spreadsheet.worksheet(worksheet_title)
            else:
                worksheet = spreadsheet.sheet1
            
            # Parse CSV content
            rows = []
            for line in csv_content.strip().split('\n'):
                # Simple CSV parsing (for more complex CSV, use csv module)
                row = [cell.strip('"') for cell in line.split(',')]
                rows.append(row)
            
            # Clear existing data and add new data
            worksheet.clear()
            worksheet.update('A1', rows)
            
            return {
                "success": True,
                "message": f"Imported {len(rows)} rows from CSV",
                "rows_imported": len(rows)
            }
            
        except Exception as e:
            log.error(f"Error importing from CSV: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

