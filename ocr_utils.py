import cv2
import numpy as np
from PIL import Image
import pytesseract
from PIL import Image
import os
import shutil

# Ensure this function name is EXACTLY as written below
def extract_text_from_image(image_path: str) -> str:
    """Extract text from image using OCR"""
    # ... rest of your code ...

def preprocess_image(image_path):
    # Load image with OpenCV
    img = cv2.imread(image_path)
    
    # 1. Convert to Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Increase Contrast & Binarization (Otsu's Threshold)
    # This makes the background pure white and text pure black
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 3. Save the cleaned image temporarily
    temp_path = "cleaned_task.png"
    cv2.imwrite(temp_path, thresh)
    return temp_path

