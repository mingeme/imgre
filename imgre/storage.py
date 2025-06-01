"""
S3 storage module for imgre.
Handles S3 operations like uploading, copying, and downloading objects.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_s3.client import S3Client

logger = logging.getLogger(__name__)


class S3Storage:
    """
    Handles S3 storage operations.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the S3 storage handler with the provided configuration.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.bucket: str = config["s3"]["bucket"]
        self.s3_client: S3Client = self._create_s3_client()
        self.url_format: str = self._get_url_format()

    def _create_s3_client(self) -> S3Client:
        """
        Create and return an S3 client using the configuration.

        Returns:
            S3Client: Boto3 S3 client instance
        """
        s3_config = self.config["s3"]

        # Create session with credentials if provided
        session_kwargs = {}
        if s3_config["access_key"] and s3_config["secret_key"]:
            session_kwargs["aws_access_key_id"] = s3_config["access_key"]
            session_kwargs["aws_secret_access_key"] = s3_config["secret_key"]

        if s3_config["region"]:
            session_kwargs["region_name"] = s3_config["region"]

        session = boto3.Session(**session_kwargs)

        # Create S3 client
        client_kwargs = {}
        if s3_config["endpoint"]:
            client_kwargs["endpoint_url"] = s3_config["endpoint"]

        return session.client("s3", **client_kwargs)

    def _get_url_format(self) -> str:
        """
        Determine the S3 URL format based on the configuration.
        """
        s3_config = self.config["s3"]
        bucket = s3_config["bucket"]
        endpoint = s3_config["endpoint"]
        region = s3_config["region"]

        if endpoint:
            # Custom S3 endpoint
            # Remove http:// or https:// prefix if present
            if endpoint.startswith(("http://", "https://")):
                endpoint = endpoint.split("://")[1]
            return f"https://{bucket}.{endpoint}/{{key}}"
        else:
            # Standard AWS S3
            return f"https://{bucket}.s3.{region}.amazonaws.com/{{key}}"

    def upload_file(
        self,
        file_path: Union[str, Path],
        object_key: Optional[str] = None,
        content_type: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Upload a file to S3.

        Args:
            file_path: Path to the file to upload
            object_key: S3 object key (path in bucket), defaults to filename
            content_type: Content type of the file
            **kwargs: Additional arguments to pass to S3 put_object

        Returns:
            URL of the uploaded file
        """
        file_path = Path(file_path)

        # Use filename as object key if not provided
        if not object_key:
            object_key = file_path.name

        # Determine content type if not provided
        if not content_type:
            if file_path.suffix.lower() in (".jpg", ".jpeg"):
                content_type = "image/jpeg"
            elif file_path.suffix.lower() == ".png":
                content_type = "image/png"
            elif file_path.suffix.lower() == ".webp":
                content_type = "image/webp"
            else:
                content_type = "application/octet-stream"

        # Upload file
        try:
            with open(file_path, "rb") as f:
                self.s3_client.put_object(
                    Bucket=self.bucket,
                    Key=object_key,
                    Body=f,
                    ContentType=content_type,
                    **kwargs,
                )

            # Return URL
            return self.url_format.format(key=object_key)

        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            raise

    def upload_bytes(
        self,
        data: bytes,
        object_key: str,
        content_type: str = "application/octet-stream",
        **kwargs,
    ) -> str:
        """
        Upload bytes data to S3.

        Args:
            data: Bytes data to upload
            object_key: S3 object key (path in bucket)
            content_type: Content type of the data
            **kwargs: Additional arguments to pass to S3 put_object

        Returns:
            URL of the uploaded file
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=data,
                ContentType=content_type,
                **kwargs,
            )

            # Return URL
            return self.url_format.format(key=object_key)

        except ClientError as e:
            logger.error(f"Error uploading bytes to S3: {e}")
            raise

    def copy_object(self, source_key: str, target_key: str, **kwargs) -> str:
        """
        Copy an object within the same bucket.

        Args:
            source_key: Source object key
            target_key: Target object key
            **kwargs: Additional arguments to pass to S3 copy_object

        Returns:
            URL of the copied object
        """
        try:
            self.s3_client.copy_object(
                Bucket=self.bucket,
                CopySource={"Bucket": self.bucket, "Key": source_key},
                Key=target_key,
                **kwargs,
            )

            # Return URL
            return self.url_format.format(key=target_key)

        except ClientError as e:
            logger.error(f"Error copying object in S3: {e}")
            raise

    def download_object(self, object_key: str) -> bytes:
        """
        Download an object from S3.

        Args:
            object_key: S3 object key

        Returns:
            Object data as bytes
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=object_key)
            return response["Body"].read()

        except ClientError as e:
            logger.error(f"Error downloading object from S3: {e}")
            raise

    # The copy_with_transform method has been moved to the copy.py command file

    def delete_object(self, object_key: str) -> None:
        """
        Delete an object from S3.

        Args:
            object_key: S3 object key to delete
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=object_key)
            logger.info(f"Deleted object from S3: {object_key}")
        except ClientError as e:
            logger.error(f"Error deleting object from S3: {e}")
            raise

    def list_objects(
        self,
        prefix: Optional[str] = None,
        max_keys: int = 1000,
        continuation_token: Optional[str] = None,
        delimiter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List objects in the S3 bucket.

        Args:
            prefix: Prefix to filter objects by
            max_keys: Maximum number of keys to return
            continuation_token: Token for pagination
            delimiter: Character used to group keys

        Returns:
            Dictionary containing the list results
        """
        try:
            params = {"Bucket": self.bucket, "MaxKeys": max_keys}

            if prefix is not None:
                params["Prefix"] = prefix

            if continuation_token is not None:
                params["ContinuationToken"] = continuation_token

            if delimiter is not None:
                params["Delimiter"] = delimiter

            response = self.s3_client.list_objects_v2(**params)

            # Format the response
            result = {
                "objects": [],
                "prefixes": [],
                "is_truncated": response.get("IsTruncated", False),
                "next_token": response.get("NextContinuationToken"),
            }

            # Process objects
            for obj in response.get("Contents", []):
                size_mb = obj.get("Size", 0) / (1024 * 1024)
                last_modified = obj.get("LastModified")

                result["objects"].append(
                    {
                        "key": obj.get("Key"),
                        "size": obj.get("Size"),
                        "size_formatted": f"{size_mb:.2f} MB",
                        "last_modified": last_modified,
                        "url": self.url_format.format(key=obj.get("Key")),
                    }
                )

            # Process common prefixes (folders)
            for prefix_obj in response.get("CommonPrefixes", []):
                result["prefixes"].append(prefix_obj.get("Prefix"))

            return result

        except ClientError as e:
            logger.error(f"Error listing objects in S3: {e}")
            raise
