from typing import Annotated
from fastapi import APIRouter, status, Depends, HTTPException
from pydantic import BaseModel

from src.services.real.ocr_service import RealOCRService

router = APIRouter()

class ImageProcessRequest(BaseModel):
    image_data: str  # Base64 encoded image
    include_caption: bool = True

class ImageProcessResponse(BaseModel):
    text: str
    confidence: float
    caption: str = ""
    success: bool
    message: str = ""

# Global OCR service instance
_ocr_service = None

def get_ocr_service() -> RealOCRService:
    """Get or create OCR service instance."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = RealOCRService()
    return _ocr_service

@router.post(
    "/process-image",
    response_model=ImageProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Process image with OCR and optional captioning",
)
async def process_image(
    request: ImageProcessRequest,
    ocr_service: Annotated[RealOCRService, Depends(get_ocr_service)]
):
    """
    Process an image to extract text using OCR and optionally generate a caption.
    
    Args:
        request: Contains base64 encoded image data and processing options
        ocr_service: OCR service dependency
        
    Returns:
        Extracted text, confidence score, and optional caption
    """
    try:
        if request.include_caption:
            result = await ocr_service.process_image_with_caption(request.image_data)
            return ImageProcessResponse(
                text=result["text"],
                confidence=result["confidence"],
                caption=result["caption"],
                success=True,
                message="Image processed successfully with OCR and captioning"
            )
        else:
            text = await ocr_service.extract_text_from_image(request.image_data)
            return ImageProcessResponse(
                text=text,
                confidence=0.0,  # Not available for text-only extraction
                caption="",
                success=True,
                message="Image processed successfully with OCR"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image: {str(e)}"
        )

@router.post(
    "/extract-text",
    response_model=ImageProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract text from image using OCR",
)
async def extract_text(
    request: ImageProcessRequest,
    ocr_service: Annotated[RealOCRService, Depends(get_ocr_service)]
):
    """
    Extract text from an image using OCR only (no captioning).
    
    Args:
        request: Contains base64 encoded image data
        ocr_service: OCR service dependency
        
    Returns:
        Extracted text and confidence score
    """
    try:
        text = await ocr_service.extract_text_from_image(request.image_data)
        return ImageProcessResponse(
            text=text,
            confidence=0.0,  # Not available for text-only extraction
            caption="",
            success=True,
            message="Text extracted successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text: {str(e)}"
        )
