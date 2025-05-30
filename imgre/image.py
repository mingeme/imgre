"""
Image processing module for imgre.
Handles image resizing, compression, and format conversion using libvips.
"""

import pyvips
from pathlib import Path
from typing import Optional, Union

# Mapping of format names to libvips format strings
FORMAT_MAP = {
    "webp": "webp",
    "jpeg": "jpg",
    "jpg": "jpg",
    "png": "png",
}

# Mapping of resize modes to libvips resize operations
RESIZE_MAP = {
    "fit": "contain",  # Resize to fit within dimensions
    "fill": "cover",  # Resize to fill dimensions (may crop)
    "exact": "force",  # Resize to exact dimensions (may distort)
}


class ImageProcessor:
    """
    Handles image processing operations like resizing, compression, and format conversion.
    """

    @staticmethod
    def open_image(image_path: Union[str, Path]) -> pyvips.Image:
        """
        Open an image file and return a pyvips Image object.
        """
        return pyvips.Image.new_from_file(str(image_path))

    @staticmethod
    def process_image(
        img: pyvips.Image,
        width: Optional[int] = None,
        height: Optional[int] = None,
        format: str = "webp",
        quality: int = 80,
        resize_mode: str = "fit",
    ) -> bytes:
        """
        Process an image with the specified parameters.

        Args:
            img: pyvips Image object
            width: Target width (None to maintain aspect ratio)
            height: Target height (None to maintain aspect ratio)
            format: Output format (webp, jpeg, png)
            quality: Output quality (1-100)
            resize_mode: Resize mode (fit, fill, exact)

        Returns:
            Processed image as bytes
        """
        # Normalize format
        format = format.lower()
        if format not in FORMAT_MAP:
            raise ValueError(f"Unsupported format: {format}")
        vips_format = FORMAT_MAP[format]

        # Resize if dimensions are provided
        if width or height:
            img = ImageProcessor.resize_image(img, width, height, resize_mode)

        # Prepare save options based on format
        save_options = {}

        if vips_format == "jpg":
            save_options = {
                "Q": quality,  # Quality
                "optimize_coding": True,  # Optimize Huffman coding tables
                "strip": True,  # Strip metadata
                "interlace": True,  # Progressive JPEG
                "autorot": True,  # Auto-rotate based on EXIF orientation
            }
        elif vips_format == "png":
            save_options = {
                "compression": 9,  # Maximum compression
                "strip": True,  # Strip metadata
                "interlace": True,  # Progressive PNG
            }
        elif vips_format == "webp":
            save_options = {
                "Q": quality,  # Quality
                "effort": 6,  # Compression effort (replaces deprecated reduction_effort)
            }

        # Save to memory
        return img.write_to_buffer(f".{vips_format}", **save_options)

    @staticmethod
    def resize_image(
        img: pyvips.Image,
        width: Optional[int] = None,
        height: Optional[int] = None,
        resize_mode: str = "fit",
    ) -> pyvips.Image:
        """
        Resize an image according to the specified parameters.

        Args:
            img: pyvips Image object
            width: Target width (None to maintain aspect ratio)
            height: Target height (None to maintain aspect ratio)
            resize_mode: Resize mode (fit, fill, exact)

        Returns:
            Resized pyvips Image object
        """
        orig_width, orig_height = img.width, img.height

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

        # Get the appropriate vips resize mode
        vips_resize_mode = RESIZE_MAP.get(resize_mode, "contain")

        # Resize based on the specified mode
        if vips_resize_mode == "force":  # exact
            # Resize to exact dimensions (may distort)
            return img.resize(
                width / orig_width, height=height, vscale=height / orig_height
            )

        elif vips_resize_mode == "cover":  # fill
            # Resize to fill dimensions (may crop)
            # First resize to cover the target dimensions
            scale = max(width / orig_width, height / orig_height)
            resized = img.resize(scale)

            # Then crop to target dimensions
            left = (resized.width - width) // 2
            top = (resized.height - height) // 2

            return resized.crop(left, top, width, height)

        else:  # "contain" (fit, default)
            # Resize to fit within dimensions (maintain aspect ratio)
            scale = min(width / orig_width, height / orig_height)
            return img.resize(scale)

    @staticmethod
    def get_image_format(image_path: Union[str, Path]) -> str:
        """
        Determine the format of an image file.

        Args:
            image_path: Path to the image file

        Returns:
            Format string (webp, jpeg, png)
        """
        try:
            # Use pyvips to get image format
            image = pyvips.Image.new_from_file(str(image_path))
            # Get format from loader
            loader = image.get_typeof("vips-loader")
            if loader != 0:  # If loader property exists
                format = image.get("vips-loader").lower()
                if format == "jpegload":
                    return "jpg"
                elif format == "pngload":
                    return "png"
                elif format == "webpload":
                    return "webp"

            # Fallback: guess from file extension
            ext = Path(image_path).suffix.lower().lstrip(".")
            if ext in ("jpg", "jpeg"):
                return "jpg"
            elif ext in ("png", "webp"):
                return ext

            return "jpg"  # Default to jpg if can't determine
        except Exception:
            # If pyvips fails, guess from file extension
            ext = Path(image_path).suffix.lower().lstrip(".")
            if ext in ("jpg", "jpeg"):
                return "jpg"
            elif ext in ("png", "webp"):
                return ext
            return "jpg"  # Default to jpg if can't determine

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
