"""
OCR Utilities for extracting text from images
"""
import pytesseract
from PIL import Image
import io
import base64
import tempfile
import os
import shutil
import sys

# ============================================
# CRITICAL: Configure pytesseract path
# ============================================

def find_tesseract_path():
    """
    Dynamically find Tesseract executable on any system.
    This is why your OCR was failing!
    """
    # Common Tesseract paths
    possible_paths = [
        # Railway/Unix systems
        shutil.which("tesseract"),  # System PATH
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        # Windows systems
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    
    for path in possible_paths:
        if path and os.path.exists(path):
            print(f"✓ Tesseract found at: {path}")
            return path
    
    print("✗ WARNING: Tesseract OCR engine not found!")
    print("   - On Railway: Add NIXPACKS_PKGS=tesseract to environment variables")
    print("   - On Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
    print("   - On Linux: sudo apt-get install tesseract-ocr")
    return None

# Set the tesseract command path
tesseract_path = find_tesseract_path()
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
else:
    print("⚠ OCR will fail: Tesseract not found")

# ============================================
# OCR Functions
# ============================================

def extract_text_from_image(image_path: str) -> str:
    """Extract text from image using OCR"""
    try:
        if not tesseract_path:
            return "OCR Error: Tesseract engine not found. Please install Tesseract OCR."
        
        # Check if file exists
        if not os.path.exists(image_path):
            return f"Error: Image file not found at {image_path}"
        
        # Open image
        with Image.open(image_path) as img:
            print(f"📷 Processing image: {image_path} ({img.size[0]}x{img.size[1]}, {img.mode})")
            
            # Preprocess for better OCR
            if img.mode not in ('L', '1'):  # Not grayscale or black/white
                img = img.convert('L')  # Convert to grayscale
            
            # Optional: Enhance image for better OCR
            # img = img.point(lambda x: 0 if x < 128 else 255, '1')  # Binarization
            
            # Extract text with configuration
            custom_config = r'--oem 3 --psm 6'  # OEM 3 = Default, PSM 6 = Assume uniform block of text
            text = pytesseract.image_to_string(img, config=custom_config)
            
            text = text.strip()
            print(f"✅ Extracted {len(text)} characters, {len(text.split())} words")
            
            return text if text else "No text detected in image"
    
    except pytesseract.pytesseract.TesseractNotFoundError:
        return "OCR Error: Tesseract is not installed or not in system PATH"
    except Exception as e:
        print(f"❌ OCR extraction error: {type(e).__name__}: {e}")
        return f"OCR Error: {type(e).__name__}: {str(e)}"

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
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        return text
    
    except Exception as e:
        print(f"❌ OCR from bytes error: {e}")
        return f"Error processing image bytes: {str(e)}"

def analyze_image_content(image_path: str) -> dict:
    """Analyze image content with OCR and basic analysis"""
    try:
        if not os.path.exists(image_path):
            return {"error": f"Image file not found: {image_path}"}
        
        with Image.open(image_path) as img:
            # Basic image info
            info = {
                "format": img.format or "Unknown",
                "mode": img.mode,
                "size": img.size,
                "width": img.width,
                "height": img.height,
                "has_alpha": img.mode in ('RGBA', 'LA', 'P', 'PA'),
                "is_grayscale": img.mode in ('L', '1', 'LA'),
            }
            
            # Extract text
            text = extract_text_from_image(image_path)
            
            # Check if text extraction was successful
            if "Error:" in text or "not found" in text:
                ocr_status = "failed"
                contains_text = False
            else:
                ocr_status = "success" if text and text != "No text detected in image" else "no_text"
                contains_text = ocr_status == "success"
            
            # Calculate metrics
            text_length = len(text) if text else 0
            word_count = len(text.split()) if text and "Error:" not in text else 0
            
            return {
                "image_info": info,
                "extracted_text": text,
                "ocr_status": ocr_status,
                "contains_text": contains_text,
                "text_length": text_length,
                "word_count": word_count,
                "tesseract_available": tesseract_path is not None
            }
    
    except Exception as e:
        print(f"❌ Image analysis error: {e}")
        return {
            "error": str(e),
            "tesseract_available": tesseract_path is not None
        }

def save_image_from_base64(base64_string: str, output_path: str) -> bool:
    """Save base64 encoded image to file"""
    try:
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decode and save
        image_data = base64.b64decode(base64_string)
        with open(output_path, 'wb') as f:
            f.write(image_data)
        return True
    except Exception as e:
        print(f"Error saving base64 image: {e}")
        return False

# Test function for debugging
def test_ocr():
    """Test OCR functionality"""
    print("🔍 Testing OCR configuration...")
    
    if tesseract_path:
        print(f"✅ Tesseract path: {tesseract_path}")
        
        # Test version
        try:
            version = pytesseract.get_tesseract_version()
            print(f"✅ Tesseract version: {version}")
        except:
            print("⚠ Could not get Tesseract version")
    else:
        print("❌ Tesseract not found!")
    
    # Test with a simple image if available
    test_images = ['test.png', 'test.jpg', 'sample.png']
    for img_file in test_images:
        if os.path.exists(img_file):
            print(f"\n📸 Testing with {img_file}...")
            result = analyze_image_content(img_file)
            print(f"Result: {result}")
            break

# Run test if module is executed directly
if __name__ == "__main__":
    test_ocr()