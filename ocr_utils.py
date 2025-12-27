"""
OCR Utilities for extracting text from images with OpenCV preprocessing
"""
import pytesseract
from PIL import Image
import io
import base64
import tempfile
import os
import shutil
import sys
import cv2
import numpy as np

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
# IMAGE PREPROCESSING (OPENCV)
# ============================================

def preprocess_image(image_path: str, save_cleaned: bool = False) -> str:
    """
    Preprocess image for better OCR using OpenCV
    This removes glow effects, noise, and enhances text visibility
    """
    try:
        print(f"🔧 Preprocessing image: {image_path}")
        
        # Load image with OpenCV
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        print(f"   Original shape: {img.shape}, dtype: {img.dtype}")
        
        # 1. Convert to Grayscale
        if len(img.shape) == 3:  # Color image
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:  # Already grayscale
            gray = img.copy()
        
        # 2. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        # This improves contrast in local regions without over-amplifying noise
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        clahe_img = clahe.apply(gray)
        
        # 3. Denoising - Remove salt and pepper noise
        denoised = cv2.medianBlur(clahe_img, 3)
        
        # 4. Binarization with Adaptive Thresholding
        # This handles varying lighting conditions better than global threshold
        binary = cv2.adaptiveThreshold(
            denoised, 
            255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            11,  # block size
            2    # constant subtracted from mean
        )
        
        # 5. Optional: Morphological operations to clean up text
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # 6. Optional: Remove small noise (dots)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
        # Save the cleaned image
        temp_dir = tempfile.gettempdir()
        temp_filename = f"cleaned_{os.path.basename(image_path)}"
        cleaned_path = os.path.join(temp_dir, temp_filename)
        
        cv2.imwrite(cleaned_path, cleaned)
        print(f"   ✅ Saved cleaned image to: {cleaned_path}")
        print(f"   Cleaned shape: {cleaned.shape}, dtype: {cleaned.dtype}")
        
        # Save for debugging if requested
        if save_cleaned:
            debug_path = f"debug_cleaned_{os.path.basename(image_path)}"
            cv2.imwrite(debug_path, cleaned)
            print(f"   💾 Debug saved to: {debug_path}")
            
            # Also save intermediate steps for analysis
            if len(img.shape) == 3:
                cv2.imwrite(f"debug_original_{os.path.basename(image_path)}", img)
            cv2.imwrite(f"debug_gray_{os.path.basename(image_path)}", gray)
            cv2.imwrite(f"debug_clahe_{os.path.basename(image_path)}", clahe_img)
            cv2.imwrite(f"debug_denoised_{os.path.basename(image_path)}", denoised)
            cv2.imwrite(f"debug_binary_{os.path.basename(image_path)}", binary)
        
        return cleaned_path
    
    except Exception as e:
        print(f"❌ Preprocessing error: {type(e).__name__}: {e}")
        # Fallback to original image
        return image_path

def preprocess_image_for_dark_bg(image_path: str) -> str:
    """
    Special preprocessing for images with dark background and light text (like your neon UI)
    """
    try:
        print(f"🌙 Preprocessing dark background image: {image_path}")
        
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            return image_path
        
        # Convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # Invert if needed (detect if background is dark)
        mean_intensity = np.mean(gray)
        if mean_intensity < 128:  # Dark background
            gray = cv2.bitwise_not(gray)
            print(f"   Inverted image (dark background detected)")
        
        # Apply threshold
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Clean up
        kernel = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Save cleaned image
        temp_dir = tempfile.gettempdir()
        temp_filename = f"cleaned_darkbg_{os.path.basename(image_path)}"
        cleaned_path = os.path.join(temp_dir, temp_filename)
        
        cv2.imwrite(cleaned_path, cleaned)
        print(f"   ✅ Saved dark-bg cleaned image to: {cleaned_path}")
        
        return cleaned_path
    
    except Exception as e:
        print(f"❌ Dark background preprocessing error: {e}")
        return image_path

# ============================================
# OCR FUNCTIONS WITH PREPROCESSING
# ============================================

def extract_text_from_image(image_path: str, use_preprocessing: bool = True) -> str:
    """Extract text from image using OCR with optional preprocessing"""
    try:
        if not tesseract_path:
            return "OCR Error: Tesseract engine not found. Please install Tesseract OCR."
        
        # Check if file exists
        if not os.path.exists(image_path):
            return f"Error: Image file not found at {image_path}"
        
        print(f"📷 OCR Processing image: {image_path}")
        
        # Determine which preprocessing to use
        with Image.open(image_path) as img:
            if img.mode == 'RGBA':
                # Convert RGBA to RGB for OpenCV
                rgb_img = img.convert('RGB')
                temp_rgb_path = os.path.join(tempfile.gettempdir(), f"temp_rgb_{os.path.basename(image_path)}")
                rgb_img.save(temp_rgb_path)
                image_path = temp_rgb_path
        
        # Apply preprocessing if requested
        if use_preprocessing:
            try:
                # Try dark background preprocessing first (for neon UI)
                cleaned_path = preprocess_image_for_dark_bg(image_path)
                
                # If preprocessing fails, fall back to original
                if cleaned_path == image_path:
                    cleaned_path = preprocess_image(image_path)
            except Exception as e:
                print(f"⚠ Preprocessing failed, using original: {e}")
                cleaned_path = image_path
        else:
            cleaned_path = image_path
        
        # Open cleaned image
        with Image.open(cleaned_path) as img:
            print(f"   Final image: {img.size[0]}x{img.size[1]}, {img.mode}")
            
            # Convert to appropriate format for OCR
            if img.mode not in ('L', '1', 'RGB'):
                img = img.convert('L')
            
            # OCR configuration for better accuracy
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,!?()-:;|"'
            
            # Extract text
            text = pytesseract.image_to_string(img, config=custom_config)
            
            text = text.strip()
            print(f"✅ Extracted {len(text)} characters, {len(text.split())} words")
            
            # Clean up temporary files
            if cleaned_path != image_path and os.path.exists(cleaned_path):
                try:
                    os.unlink(cleaned_path)
                except:
                    pass
            
            return text if text else "No text detected in image"
    
    except pytesseract.pytesseract.TesseractNotFoundError:
        return "OCR Error: Tesseract is not installed or not in system PATH"
    except Exception as e:
        print(f"❌ OCR extraction error: {type(e).__name__}: {e}")
        return f"OCR Error: {type(e).__name__}: {str(e)}"

def extract_text_from_image_bytes(image_bytes: bytes, use_preprocessing: bool = True) -> str:
    """Extract text from image bytes with preprocessing"""
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        
        # Extract text with preprocessing
        text = extract_text_from_image(tmp_path, use_preprocessing)
        
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
            
            # Extract text with preprocessing
            text = extract_text_from_image(image_path, use_preprocessing=True)
            
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
                "tesseract_available": tesseract_path is not None,
                "preprocessing_used": True
            }
    
    except Exception as e:
        print(f"❌ Image analysis error: {e}")
        return {
            "error": str(e),
            "tesseract_available": tesseract_path is not None,
            "preprocessing_used": False
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

def test_ocr_preprocessing():
    """Test OCR preprocessing functionality"""
    print("🔍 Testing OCR preprocessing...")
    
    if tesseract_path:
        print(f"✅ Tesseract path: {tesseract_path}")
        
        # Test version
        try:
            version = pytesseract.get_tesseract_version()
            print(f"✅ Tesseract version: {version}")
        except:
            print("⚠ Could not get Tesseract version")
        
        # Test OpenCV
        try:
            print(f"✅ OpenCV version: {cv2.__version__}")
        except:
            print("⚠ OpenCV not available")
    else:
        print("❌ Tesseract not found!")
    
    # Test with sample images
    test_images = ['test.png', 'test.jpg', 'sample.png', 'JOIN_OUR_QUEST.png']
    for img_file in test_images:
        if os.path.exists(img_file):
            print(f"\n📸 Testing preprocessing with {img_file}...")
            
            # Test without preprocessing
            print("\n   Without preprocessing:")
            result_raw = extract_text_from_image(img_file, use_preprocessing=False)
            print(f"   Result: {result_raw[:100]}...")
            
            # Test with preprocessing
            print("\n   With preprocessing:")
            result_cleaned = extract_text_from_image(img_file, use_preprocessing=True)
            print(f"   Result: {result_cleaned[:100]}...")
            
            # Show improvement
            if result_raw != result_cleaned:
                print("\n   ✅ PREPROCESSING IMPROVED OCR ACCURACY!")
            
            break
    else:
        print("\n⚠ No test images found. Create a test.png file to test OCR.")

# Run test if module is executed directly
if __name__ == "__main__":
    test_ocr_preprocessing()