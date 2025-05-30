# imgre - Image Optimization and S3 Management Tool

A Python port of the [imgood](https://github.com/mingeme/imgood) project, providing a powerful command-line tool for image optimization, format conversion, and S3 object management.

## Features

* Image compression and resizing
* Format conversion (WebP, JPEG, PNG)
* S3 upload with customizable paths
* S3 object copying with format conversion
* Configuration via TOML files and environment variables
* Support for custom S3-compatible storage services

## Prerequisites

* Python 3.8 or later
* Pillow library for image processing

## Installation

```bash
# Using UV (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

## Commands

imgre provides the following commands:

* `up`: Upload images to S3 with optional compression and format conversion
* `cp`: Copy objects within S3 with optional format conversion and resizing
* `ls`: List objects in the S3 bucket with optional filtering and pagination

## Configuration

imgre supports configuration through:

1. Configuration files (`config.toml`)
2. Environment variables

### Configuration File Locations

The tool looks for a `config.toml` file in the following locations (in order):

1. Current directory (`./config.toml`)
2. User's home directory (`~/.imgre/config.toml`)
3. XDG config directory (`~/.config/imgre/config.toml`)

### Example Configuration

```toml
# S3 Configuration
[s3]
# S3 bucket name (required)
bucket = "my-images-bucket"

# S3 endpoint URL (for non-AWS S3 services)
# Format: https://s3.example.com
# Leave empty for AWS S3
endpoint = "https://s3.bitiful.net"

# AWS region (required for AWS S3)
region = "us-east-1"

# AWS credentials
# These can be left empty if using environment variables or AWS credential files
access_key = "your-access-key"
secret_key = "your-secret-key"

# Default image processing options
[image]
# Default format for conversions
format = "webp"

# Default quality (1-100)
quality = 80

# Default resize behavior
# "fit" - Resize to fit within dimensions
# "fill" - Resize to fill dimensions (may crop)
# "exact" - Resize to exact dimensions (may distort)
resize_mode = "fit"
```

## Usage

### Upload Command (`up`)

Upload images to S3 with optional compression and format conversion.

```bash
imgre up [options]
```

#### Upload Options

* `-i, --input TEXT`: Path to the input image file (required)
* `-k, --key TEXT`: S3 object key (path in bucket), defaults to filename
* `-c, --compress`: Compress image before uploading
* `-q, --quality INTEGER`: Quality of the compressed image (1-100) (default 80)
* `-w, --width INTEGER`: Width of the output image (0 for original)
* `-h, --height INTEGER`: Height of the output image (0 for original)
* `-f, --format TEXT`: Convert to format (webp, jpeg, png) (default "webp")

#### Examples

Upload an image with default settings:

```bash
imgre up -i sample.jpg
```

Upload with compression and custom key:

```bash
imgre up -i sample.jpg -k images/2025/05/sample.jpg -c -q 85
```

Upload with resizing (converts to WebP format by default):

```bash
imgre up -i sample.jpg -c -w 800 -h 600
```

### Copy Command (`cp`)

Copy objects within S3 with optional format conversion and resizing.

```bash
imgre cp [options]
```

#### Copy Options

* `-s, --source TEXT`: Source S3 object key to copy (required)
* `-t, --target TEXT`: Target S3 object key (destination), defaults to source-copy
* `-f, --format TEXT`: Convert to format (webp, jpeg, png) (default "webp")
* `-q, --quality INTEGER`: Quality of the converted image (1-100) (default 80)
* `-w, --width INTEGER`: Width of the output image (0 for original)
* `-h, --height INTEGER`: Height of the output image (0 for original)

#### Copy Command Examples

Copy an object with default settings (converts to WebP):

```bash
imgre cp -s images/original.jpg
```

Copy with specific format and target key:

```bash
imgre cp -s images/original.jpg -t images/copy.png -f png
```

Copy with resizing and quality adjustment:

```bash
imgre cp -s images/original.jpg -w 1200 -h 800 -q 90
```

### List Command (`ls`)

List objects in the S3 bucket with optional filtering and pagination.

```bash
imgre ls [options]
```

#### List Options

* `-p, --prefix TEXT`: Prefix to filter objects by
* `-d, --delimiter TEXT`: Character used to group keys (e.g., '/' for folder-like hierarchy)
* `-m, --max-keys INTEGER`: Maximum number of keys to return (default: 1000)
* `-t, --token TEXT`: Continuation token for pagination
* `--url`: Show URLs for objects
* `--recursive`: List objects recursively (ignores delimiter)

#### List Command Examples

List all objects in the bucket:

```bash
imgre ls
```

List objects in a specific "folder":

```bash
imgre ls -p images/
```

List objects recursively with a prefix:

```bash
imgre ls -p images/ --recursive
```

Show URLs for objects:

```bash
imgre ls --url
```

## URL Format

When using custom S3 endpoints, imgre generates URLs in the format:

```text
https://{bucket}.{endpoint}/{key}
```

For example, with bucket `imgre` and endpoint `s3.example.com`, the URL would be:

```text
https://imgre.s3.example.com/path/to/image.jpg
```

For AWS S3, the standard format is used:

```text
https://{bucket}.s3.{region}.amazonaws.com/{key}
```

## License

MIT
