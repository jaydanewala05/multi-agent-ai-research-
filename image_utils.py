"""
Image utilities for AI multi-agent system
"""
import base64
from PIL import Image
import io

def resize_image(image_path: str, max_size: tuple = (800, 800)) -> str:
    """Resize image and return base64 string"""
    try:
        with Image.open(image_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert to bytes
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return img_str
    except Exception as e:
        print(f"Image resize error: {e}")
        return ""

def get_dominant_colors(image_path: str, num_colors: int = 5) -> list:
    """Get dominant colors from image"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if not already
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize for faster processing
            img = img.resize((100, 100))
            
            # Get colors
            colors = img.getcolors(maxcolors=10000)
            if colors:
                # Sort by frequency
                colors.sort(key=lambda x: x[0], reverse=True)
                # Get top colors
                dominant = [f"#{color[1][0]:02x}{color[1][1]:02x}{color[1][2]:02x}" 
                           for _, color in colors[:num_colors]]
                return dominant
            return []
    except Exception as e:
        print(f"Color extraction error: {e}")
        return []