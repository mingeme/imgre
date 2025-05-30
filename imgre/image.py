"""
Image processing module for imgre.
Handles image resizing, compression, and format conversion.
"""

import io
from pathlib import Path
from typing import Optional, Tuple, Union, BinaryIO

from PIL import Image

# Mapping of format names to PIL format strings
FORMAT_MAP = {
    "webp": "WEBP",
    "jpeg": "JPEG",
    "jpg": "JPEG",
    "png": "PNG",
}

class ImageProcessor:
    """
    Handles image processing operations like resizing, compression, and format conversion.
    """
    
    @staticmethod
    def open_image(image_path: Union[str, Path]) -> Image.Image:
        """
        Open an image file and return a PIL Image object.
        """
        return Image.open(image_path)
    
    @staticmethod
    def process_image(
        img: Image.Image,
        width: Optional[int] = None,
        height: Optional[int] = None,
        format: str = "webp",
        quality: int = 80,
        resize_mode: str = "fit"
    ) -> bytes:
        """
        Process an image with the specified parameters.
        
        Args:
            img: PIL Image object
            width: Target width (None to maintain aspect ratio)
            height: Target height (None to maintain aspect ratio)
            format: Output format (webp, jpeg, png)
            quality: Output quality (1-100)
            resize_mode: Resize mode (fit, fill, exact)
            
        Returns:
            Processed image as bytes
        """
        # Create a copy to avoid modifying the original
        img = img.copy()
        
        # Normalize format
        format = format.lower()
        if format not in FORMAT_MAP:
            raise ValueError(f"Unsupported format: {format}")
        pil_format = FORMAT_MAP[format]
        
        # Resize if dimensions are provided
        if width or height:
            img = ImageProcessor.resize_image(img, width, height, resize_mode)
        
        # Save to bytes buffer
        buffer = io.BytesIO()
        
        # Save with appropriate options
        if pil_format == "JPEG":
            img = img.convert("RGB")  # JPEG doesn't support alpha channel
            img.save(buffer, format=pil_format, quality=quality, optimize=True)
        elif pil_format == "PNG":
            img.save(buffer, format=pil_format, optimize=True)
        elif pil_format == "WEBP":
            img.save(buffer, format=pil_format, quality=quality, method=4)
        else:
            img.save(buffer, format=pil_format)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    @staticmethod
    def resize_image(
        img: Image.Image,
        width: Optional[int] = None,
        height: Optional[int] = None,
        resize_mode: str = "fit"
    ) -> Image.Image:
        """
        Resize an image according to the specified parameters.
        
        Args:
            img: PIL Image object
            width: Target width (None to maintain aspect ratio)
            height: Target height (None to maintain aspect ratio)
            resize_mode: Resize mode (fit, fill, exact)
            
        Returns:
            Resized PIL Image object
        """
        orig_width, orig_height = img.size
        
        # If both dimensions are None or 0, return the original
        if not width and not height:
            return img
        
        # If only one dimension is specified, calculate the other to maintain aspect ratio
        if width and not height:
            height = int(orig_height * (width / orig_width))
        elif height and not width:
            width = int(orig_width * (height / orig_height))
        
        # Ensure width and height are integers
        width = int(width) if width else orig_width
        height = int(height) if height else orig_height
        
        # Resize based on the specified mode
        if resize_mode == "exact":
            # Resize to exact dimensions (may distort)
            return img.resize((width, height), Image.LANCZOS)
        
        elif resize_mode == "fill":
            # Resize to fill dimensions (may crop)
            img_ratio = orig_width / orig_height
            target_ratio = width / height
            
            if img_ratio > target_ratio:
                # Image is wider than target, scale by height and crop width
                new_width = int(height * img_ratio)
                new_height = height
                resized = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Crop to target width
                left = (new_width - width) // 2
                right = left + width
                return resized.crop((left, 0, right, height))
            else:
                # Image is taller than target, scale by width and crop height
                new_width = width
                new_height = int(width / img_ratio)
                resized = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Crop to target height
                top = (new_height - height) // 2
                bottom = top + height
                return resized.crop((0, top, width, bottom))
        
        else:  # "fit" (default)
            # Resize to fit within dimensions (maintain aspect ratio)
            img_ratio = orig_width / orig_height
            target_ratio = width / height
            
            if img_ratio > target_ratio:
                # Image is wider than target, constrain by width
                new_width = width
                new_height = int(width / img_ratio)
            else:
                # Image is taller than target, constrain by height
                new_width = int(height * img_ratio)
                new_height = height
            
            return img.resize((new_width, new_height), Image.LANCZOS)
    
    @staticmethod
    def get_image_format(image_path: Union[str, Path]) -> str:
        """
        Determine the format of an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Format string (webp, jpeg, png)
        """
        with Image.open(image_path) as img:
            format = img.format.lower()
            
            if format == "jpeg":
                return "jpg"
            return format
    
    @staticmethod
    def get_content_type(format: str) -> str:
        """
        Get the MIME content type for a given image format.
        
        Args:
            format: Image format (webp, jpeg/jpg, png)
            
        Returns:
            MIME content type
        """
        format = format.lower()
        if format in ("jpg", "jpeg"):
            return "image/jpeg"
        elif format == "png":
            return "image/png"
        elif format == "webp":
            return "image/webp"
        else:
            return "application/octet-stream"
