import cv2
import numpy as np
import pytesseract
from PIL import Image
import os
import shutil

# ============================================
# 1. PATH CONFIGURATION
# ============================================
def find_tesseract_path():
    """Dynamically find Tesseract on Railway or Local"""
    possible_paths = [
        shutil.which("tesseract"), 
        "/root/.nix-profile/bin/tesseract", # Standard Nixpacks path
        "/usr/bin/tesseract",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    ]
    for path in possible_paths:
        if path and os.path.exists(path):
            return path
    return None

tesseract_path = find_tesseract_path()
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

# ============================================
# 2. PREPROCESSING LOGIC
# ============================================
def preprocess_image(image_path):
    """Clean the image using OpenCV to improve OCR accuracy"""
    img = cv2.imread(image_path)
    if img is None:
        return image_path
    
    # Convert to Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Binarization (Otsu's Threshold) to remove 'glow' and noise
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    temp_path = "cleaned_for_ocr.png"
    cv2.imwrite(temp_path, thresh)
    return temp_path

# ============================================
# 3. EXPORTED FUNCTIONS (REQUIRED BY APP.PY)
# ============================================

def extract_text_from_image(image_path: str) -> str:
    """The main function called by app.py to get text"""
    try:
        if not tesseract_path:
            return "OCR Error: Tesseract engine not found."

        # Apply the OpenCV cleaning
        processed_path = preprocess_image(image_path)
        
        # Run OCR
        with Image.open(processed_path) as img:
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(img, config=custom_config)
            return text.strip() if text.strip() else "No text detected."
            
    except Exception as e:
        return f"OCR Error: {str(e)}"

def analyze_image_content(image_path: str) -> dict:
    """The second function required by app.py line 32"""
    text = extract_text_from_image(image_path)
    return {
        "extracted_text": text,
        "ocr_status": "success" if len(text) > 20 else "check_image",
        "tesseract_available": tesseract_path is not None
    }