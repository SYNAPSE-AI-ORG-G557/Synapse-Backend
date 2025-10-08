#!/usr/bin/env python3
"""
Test script for OCR service integration.
This script tests the OCR service directly without going through the API.
"""

import asyncio
import base64
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.services.real.ocr_service import RealOCRService

async def test_ocr_service():
    """Test the OCR service with a sample image."""
    print("Initializing OCR service...")
    ocr_service = RealOCRService()
    
    # Create a simple test image (white background with black text)
    from PIL import Image, ImageDraw, ImageFont
    import io
    
    # Create a simple test image
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a default font, fallback to basic if not available
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    # Draw some text
    text = "Hello World!\nThis is a test image for OCR."
    draw.text((50, 50), text, fill='black', font=font)
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_bytes = buffer.getvalue()
    base64_data = base64.b64encode(img_bytes).decode('utf-8')
    
    print("Testing text extraction...")
    try:
        extracted_text = await ocr_service.extract_text_from_image(base64_data)
        print(f"Extracted text: '{extracted_text}'")
    except Exception as e:
        print(f"Error in text extraction: {e}")
    
    print("\nTesting image processing with caption...")
    try:
        result = await ocr_service.process_image_with_caption(base64_data)
        print(f"OCR Result:")
        print(f"  Text: '{result['text']}'")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Caption: '{result['caption']}'")
    except Exception as e:
        print(f"Error in image processing: {e}")

if __name__ == "__main__":
    print("OCR Service Test")
    print("=" * 50)
    asyncio.run(test_ocr_service())
