import pytesseract
from PIL import Image
import platform
import os
from io import BytesIO

# Set the Tesseract executable path based on the operating system
if platform.system() == 'Windows':
    # Windows path
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
elif platform.system() == 'Darwin':  # macOS
    # Try common macOS installation paths
    possible_paths = [
        '/usr/local/bin/tesseract',
        '/opt/homebrew/bin/tesseract',
        '/usr/bin/tesseract'
    ]
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break
    # If not found, pytesseract will try to find it in PATH

def extract_ingredients(file_obj):
    try:
        # Reset stream position to beginning
        file_obj.seek(0)
        
        # Enable loading truncated images
        from PIL import ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        
        # Try multiple approaches to read the file
        # Approach 1: Try using Flask's file object directly
        try:
            file_obj.seek(0)
            image = Image.open(file_obj)
            # Verify it loaded correctly
            image.load()
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            text = pytesseract.image_to_string(image)
            return text
        except Exception as direct_error:
            # Approach 2: Read as bytes and use BytesIO
            file_obj.seek(0)
            file_content = file_obj.read()
            
            if not file_content:
                raise Exception("Empty file uploaded")
            
            # Check if we have valid image data
            if len(file_content) < 10:
                raise Exception("File too small to be a valid image")
            
            # Check file magic numbers
            header = file_content[:10]
            is_valid = False
            if header[:3] == b'\xff\xd8\xff':  # JPEG
                is_valid = True
            elif header[:8] == b'\x89PNG\r\n\x1a\n':  # PNG
                is_valid = True
            elif header[:6] in (b'GIF87a', b'GIF89a'):  # GIF
                is_valid = True
            elif header[:2] == b'BM':  # BMP
                is_valid = True
            elif header[:4] == b'RIFF' and header[8:12] == b'WEBP':  # WEBP
                is_valid = True
            
            if not is_valid:
                raise Exception(f"File does not appear to be a valid image. File header: {header.hex()}")
            
            # Create BytesIO and try again
            image_bytes = BytesIO(file_content)
            image_bytes.seek(0)
            
            image = Image.open(image_bytes)
            image.load()  # Force loading to verify
            
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            # Perform OCR
            text = pytesseract.image_to_string(image)
            return text
            
    except Exception as e:
        error_msg = str(e)
        # Provide helpful error message
        if "cannot identify image file" in error_msg.lower():
            raise Exception(f"Cannot identify image file. Please ensure you're uploading a valid, non-corrupted image file (PNG, JPG, JPEG, GIF, BMP, or WEBP). If the file works when opened in an image viewer, try saving it again or converting it to a different format.")
        raise Exception(f"Error processing image: {error_msg}")
