"""
OCR Utilities for extracting text from images
"""
import pytesseract
from PIL import Image
import io
import base64
import tempfile
import os

def extract_text_from_image(image_path: str) -> str:
    """Extract text from image using OCR"""
    try:
        # Open image
        with Image.open(image_path) as img:
            # Convert to grayscale for better OCR
            if img.mode != 'L':
                img = img.convert('L')
            
            # Use pytesseract to extract text
            text = pytesseract.image_to_string(img)
            
            return text.strip()
    
    except Exception as e:
        print(f"OCR extraction error: {e}")
        return ""

def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """Extract text from image bytes"""
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        
        # Extract text
        text = extract_text_from_image(tmp_path)
        
        # Clean up
        os.unlink(tmp_path)
        
        return text
    
    except Exception as e:
        print(f"OCR from bytes error: {e}")
        return ""

def analyze_image_content(image_path: str) -> dict:
    """Analyze image content with OCR and basic analysis"""
    try:
        with Image.open(image_path) as img:
            # Basic image info
            info = {
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "width": img.width,
                "height": img.height,
                "has_alpha": img.mode in ('RGBA', 'LA', 'P')
            }
            
            # Extract text
            text = extract_text_from_image(image_path)
            
            # Analyze if image contains text
            contains_text = len(text.strip()) > 0
            
            return {
                "image_info": info,
                "extracted_text": text,
                "contains_text": contains_text,
                "text_length": len(text),
                "word_count": len(text.split()) if text else 0
            }
    
    except Exception as e:
        print(f"Image analysis error: {e}")
        return {"error": str(e)}