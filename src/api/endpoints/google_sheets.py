from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from src.core.dependencies import get_current_user_sync
from src.services.google_sheets_service import GoogleSheetsService
import structlog

log = structlog.get_logger(__name__)
router = APIRouter()

# Pydantic models for request validation
class CreateSpreadsheetRequest(BaseModel):
    title: str
    sheet_names: Optional[List[str]] = None

class UpdateDataRequest(BaseModel):
    spreadsheet_id: str
    data: List[List[Any]]
    worksheet_title: Optional[str] = None
    range_name: Optional[str] = None

class AppendDataRequest(BaseModel):
    spreadsheet_id: str
    data: List[List[Any]]
    worksheet_title: Optional[str] = None

class GetDataRequest(BaseModel):
    spreadsheet_id: str
    worksheet_title: Optional[str] = None
    range_name: Optional[str] = None

class AddWorksheetRequest(BaseModel):
    spreadsheet_id: str
    title: str
    rows: Optional[int] = 1000
    cols: Optional[int] = 26

class ShareSpreadsheetRequest(BaseModel):
    spreadsheet_id: str
    email: str
    role: Optional[str] = 'reader'

class ExportCSVRequest(BaseModel):
    spreadsheet_id: str
    worksheet_title: Optional[str] = None
    filename: Optional[str] = None

class ImportCSVRequest(BaseModel):
    spreadsheet_id: str
    csv_content: str
    worksheet_title: Optional[str] = None

@router.post("/create-spreadsheet")
async def create_spreadsheet(
    request: CreateSpreadsheetRequest,
    user = Depends(get_current_user_sync)
):
    """Create a new Google Spreadsheet"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        sheets_service = GoogleSheetsService(user.google_access_token)
        result = await sheets_service.create_spreadsheet(
            title=request.title,
            sheet_names=request.sheet_names
        )
        
        if result["success"]:
            log.info("Spreadsheet created successfully", 
                    user_id=user.uuid, 
                    spreadsheet_id=result["spreadsheet_id"])
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error creating spreadsheet", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to create spreadsheet: {str(e)}")

@router.post("/open-spreadsheet")
async def open_spreadsheet(
    request: Request,
    user = Depends(get_current_user_sync)
):
    """Open an existing spreadsheet by ID"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        body = await request.json()
        spreadsheet_id = body.get("spreadsheet_id")
        
        if not spreadsheet_id:
            raise HTTPException(status_code=400, detail="spreadsheet_id is required")
        
        sheets_service = GoogleSheetsService(user.google_access_token)
        result = await sheets_service.open_spreadsheet(spreadsheet_id)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error opening spreadsheet", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to open spreadsheet: {str(e)}")

@router.post("/get-data")
async def get_worksheet_data(
    request: GetDataRequest,
    user = Depends(get_current_user_sync)
):
    """Get data from a worksheet"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        sheets_service = GoogleSheetsService(user.google_access_token)
        result = await sheets_service.get_worksheet_data(
            spreadsheet_id=request.spreadsheet_id,
            worksheet_title=request.worksheet_title,
            range_name=request.range_name
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error getting worksheet data", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to get worksheet data: {str(e)}")

@router.post("/update-data")
async def update_worksheet_data(
    request: UpdateDataRequest,
    user = Depends(get_current_user_sync)
):
    """Update data in a worksheet"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        sheets_service = GoogleSheetsService(user.google_access_token)
        result = await sheets_service.update_worksheet_data(
            spreadsheet_id=request.spreadsheet_id,
            data=request.data,
            worksheet_title=request.worksheet_title,
            range_name=request.range_name
        )
        
        if result["success"]:
            log.info("Worksheet data updated successfully", 
                    user_id=user.uuid, 
                    spreadsheet_id=request.spreadsheet_id)
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error updating worksheet data", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to update worksheet data: {str(e)}")

@router.post("/append-data")
async def append_data(
    request: AppendDataRequest,
    user = Depends(get_current_user_sync)
):
    """Append data to the end of a worksheet"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        sheets_service = GoogleSheetsService(user.google_access_token)
        result = await sheets_service.append_data(
            spreadsheet_id=request.spreadsheet_id,
            data=request.data,
            worksheet_title=request.worksheet_title
        )
        
        if result["success"]:
            log.info("Data appended successfully", 
                    user_id=user.uuid, 
                    spreadsheet_id=request.spreadsheet_id)
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error appending data", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to append data: {str(e)}")

@router.post("/add-worksheet")
async def add_worksheet(
    request: AddWorksheetRequest,
    user = Depends(get_current_user_sync)
):
    """Add a new worksheet to a spreadsheet"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        sheets_service = GoogleSheetsService(user.google_access_token)
        result = await sheets_service.add_worksheet(
            spreadsheet_id=request.spreadsheet_id,
            title=request.title,
            rows=request.rows,
            cols=request.cols
        )
        
        if result["success"]:
            log.info("Worksheet added successfully", 
                    user_id=user.uuid, 
                    spreadsheet_id=request.spreadsheet_id)
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error adding worksheet", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to add worksheet: {str(e)}")

@router.post("/delete-worksheet")
async def delete_worksheet(
    request: Request,
    user = Depends(get_current_user_sync)
):
    """Delete a worksheet from a spreadsheet"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        body = await request.json()
        spreadsheet_id = body.get("spreadsheet_id")
        worksheet_title = body.get("worksheet_title")
        
        if not spreadsheet_id or not worksheet_title:
            raise HTTPException(status_code=400, detail="spreadsheet_id and worksheet_title are required")
        
        sheets_service = GoogleSheetsService(user.google_access_token)
        result = await sheets_service.delete_worksheet(spreadsheet_id, worksheet_title)
        
        if result["success"]:
            log.info("Worksheet deleted successfully", 
                    user_id=user.uuid, 
                    spreadsheet_id=spreadsheet_id)
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error deleting worksheet", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to delete worksheet: {str(e)}")

@router.post("/share-spreadsheet")
async def share_spreadsheet(
    request: ShareSpreadsheetRequest,
    user = Depends(get_current_user_sync)
):
    """Share a spreadsheet with another user"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        sheets_service = GoogleSheetsService(user.google_access_token)
        result = await sheets_service.share_spreadsheet(
            spreadsheet_id=request.spreadsheet_id,
            email=request.email,
            role=request.role
        )
        
        if result["success"]:
            log.info("Spreadsheet shared successfully", 
                    user_id=user.uuid, 
                    spreadsheet_id=request.spreadsheet_id)
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error sharing spreadsheet", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to share spreadsheet: {str(e)}")

@router.get("/list-spreadsheets")
async def list_spreadsheets(user = Depends(get_current_user_sync)):
    """List all spreadsheets accessible to the user"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        sheets_service = GoogleSheetsService(user.google_access_token)
        result = await sheets_service.list_spreadsheets()
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error listing spreadsheets", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to list spreadsheets: {str(e)}")

@router.post("/export-csv")
async def export_to_csv(
    request: ExportCSVRequest,
    user = Depends(get_current_user_sync)
):
    """Export a worksheet to CSV format"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        sheets_service = GoogleSheetsService(user.google_access_token)
        result = await sheets_service.export_to_csv(
            spreadsheet_id=request.spreadsheet_id,
            worksheet_title=request.worksheet_title,
            filename=request.filename
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error exporting to CSV", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to export to CSV: {str(e)}")

@router.post("/import-csv")
async def import_from_csv(
    request: ImportCSVRequest,
    user = Depends(get_current_user_sync)
):
    """Import CSV data into a worksheet"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        sheets_service = GoogleSheetsService(user.google_access_token)
        result = await sheets_service.import_from_csv(
            spreadsheet_id=request.spreadsheet_id,
            csv_content=request.csv_content,
            worksheet_title=request.worksheet_title
        )
        
        if result["success"]:
            log.info("CSV data imported successfully", 
                    user_id=user.uuid, 
                    spreadsheet_id=request.spreadsheet_id)
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error importing from CSV", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to import from CSV: {str(e)}")

@router.post("/format-cells")
async def format_cells(
    request: Request,
    user = Depends(get_current_user_sync)
):
    """Format cells in a worksheet"""
    try:
        if not user.google_access_token:
            raise HTTPException(status_code=400, detail="Google account not connected")
        
        body = await request.json()
        spreadsheet_id = body.get("spreadsheet_id")
        format_config = body.get("format_config", {})
        worksheet_title = body.get("worksheet_title")
        range_name = body.get("range_name")
        
        if not spreadsheet_id:
            raise HTTPException(status_code=400, detail="spreadsheet_id is required")
        
        sheets_service = GoogleSheetsService(user.google_access_token)
        result = await sheets_service.format_cells(
            spreadsheet_id=spreadsheet_id,
            format_config=format_config,
            worksheet_title=worksheet_title,
            range_name=range_name
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
        
    except Exception as e:
        log.error("Error formatting cells", error=str(e), user_id=user.uuid)
        raise HTTPException(status_code=500, detail=f"Failed to format cells: {str(e)}")

@router.get("/status")
async def get_sheets_status(user = Depends(get_current_user_sync)):
    """Get Google Sheets integration status"""
    try:
        if not user.google_access_token:
            return {
                "connected": False,
                "message": "Google account not connected",
                "sheets_enabled": False
            }
        
        # Test connection by listing spreadsheets
        sheets_service = GoogleSheetsService(user.google_access_token)
        result = await sheets_service.list_spreadsheets()
        
        if result["success"]:
            return {
                "connected": True,
                "sheets_enabled": True,
                "spreadsheet_count": result["count"],
                "message": "Google Sheets integration is working"
            }
        else:
            return {
                "connected": True,
                "sheets_enabled": False,
                "message": f"Sheets integration error: {result['error']}"
            }
        
    except Exception as e:
        return {
            "connected": False,
            "sheets_enabled": False,
            "message": f"Error checking Sheets status: {str(e)}"
        }

