"""
Configuration module for imgre.
Handles loading configuration from files and environment variables.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# For Python < 3.11, use tomli instead of tomllib
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


def get_config_paths() -> list[Path]:
    """
    Get a list of possible configuration file paths in order of priority.
    """
    paths = [
        Path.cwd() / "config.toml",  # Current directory
        Path.home() / ".imgre" / "config.toml",  # User's home directory
    ]

    # XDG config directory
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        paths.append(Path(xdg_config_home) / "imgre" / "config.toml")
    else:
        paths.append(Path.home() / ".config" / "imgre" / "config.toml")

    return paths


def load_config() -> Dict[str, Any]:
    """
    Load configuration from TOML files and environment variables.
    Returns a dictionary with the merged configuration.
    """
    config = {
        "s3": {
            "bucket": None,
            "endpoint": None,
            "region": "us-east-1",
            "access_key": None,
            "secret_key": None,
        },
        "image": {
            "format": "webp",
            "quality": 80,
            "resize_mode": "fit",
        },
    }

    # Try to load from config files
    for config_path in get_config_paths():
        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    file_config = tomllib.load(f)

                # Update config with values from file
                if "s3" in file_config:
                    config["s3"].update(file_config["s3"])
                if "image" in file_config:
                    config["image"].update(file_config["image"])

                break  # Stop after the first valid config file
            except Exception as e:
                print(f"Error loading config from {config_path}: {e}", file=sys.stderr)

    # Override with environment variables
    env_mapping = {
        "IMGRE_S3_BUCKET": ("s3", "bucket"),
        "IMGRE_S3_ENDPOINT": ("s3", "endpoint"),
        "IMGRE_S3_REGION": ("s3", "region"),
        "IMGRE_S3_ACCESS_KEY": ("s3", "access_key"),
        "IMGRE_S3_SECRET_KEY": ("s3", "secret_key"),
        "IMGRE_IMAGE_FORMAT": ("image", "format"),
        "IMGRE_IMAGE_QUALITY": ("image", "quality"),
        "IMGRE_IMAGE_RESIZE_MODE": ("image", "resize_mode"),
    }

    for env_var, (section, key) in env_mapping.items():
        value = os.environ.get(env_var)
        if value is not None:
            # Convert to int for numeric values
            if key == "quality":
                try:
                    value = int(value)
                except ValueError:
                    pass
            config[section][key] = value

    # Also check for standard AWS environment variables
    if not config["s3"]["access_key"]:
        config["s3"]["access_key"] = os.environ.get("AWS_ACCESS_KEY_ID")
    if not config["s3"]["secret_key"]:
        config["s3"]["secret_key"] = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not config["s3"]["region"]:
        config["s3"]["region"] = (
            os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
            or "us-east-1"
        )

    return config


def get_s3_url_format(config: Dict[str, Any]) -> str:
    """
    Determine the S3 URL format based on the configuration.
    """
    bucket = config["s3"]["bucket"]
    endpoint = config["s3"]["endpoint"]
    region = config["s3"]["region"]

    if endpoint:
        # Custom S3 endpoint
        # Remove http:// or https:// prefix if present
        if endpoint.startswith(("http://", "https://")):
            endpoint = endpoint.split("://")[1]
        return f"https://{bucket}.{endpoint}/{{key}}"
    else:
        # Standard AWS S3
        return f"https://{bucket}.s3.{region}.amazonaws.com/{{key}}"


def validate_config(config: Dict[str, Any]) -> Optional[str]:
    """
    Validate the configuration and return an error message if invalid.
    """
    if not config["s3"]["bucket"]:
        return "S3 bucket name is required"

    # Validate image format
    valid_formats = ["webp", "jpeg", "jpg", "png"]
    if config["image"]["format"].lower() not in valid_formats:
        return f"Invalid image format: {config['image']['format']}. Must be one of: {', '.join(valid_formats)}"

    # Validate quality
    quality = config["image"]["quality"]
    if not isinstance(quality, int) or quality < 1 or quality > 100:
        return f"Invalid quality value: {quality}. Must be an integer between 1 and 100"

    # Validate resize mode
    valid_modes = ["fit", "fill", "exact"]
    if config["image"]["resize_mode"].lower() not in valid_modes:
        return f"Invalid resize mode: {config['image']['resize_mode']}. Must be one of: {', '.join(valid_modes)}"

    return None
