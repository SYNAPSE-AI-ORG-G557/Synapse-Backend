from abc import ABC, abstractmethod
from typing import Dict, Any

class OCRServiceInterface(ABC):
    """Interface for OCR services."""
    
    @abstractmethod
    async def extract_text_from_image(self, image_data: str) -> str:
        """
        Extract text from a base64 encoded image.
        
        Args:
            image_data: Base64 encoded image data
            
        Returns:
            Extracted text from the image
        """
        pass
    
    @abstractmethod
    async def process_image_with_caption(self, image_data: str) -> Dict[str, Any]:
        """
        Process image to extract both text and generate caption.
        
        Args:
            image_data: Base64 encoded image data
            
        Returns:
            Dictionary containing extracted text and image caption
        """
        pass
