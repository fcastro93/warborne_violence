"""
S3 utility functions for image storage and management
"""
import boto3
import os
from django.conf import settings
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

class S3Manager:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self.environment = settings.ENVIRONMENT
        self.images_folder = settings.S3_IMAGES_FOLDER
    
    def upload_image(self, file_obj, filename, content_type='image/png'):
        """
        Upload an image to S3 with environment-based folder structure
        
        Args:
            file_obj: File object to upload
            filename: Name of the file (will be prefixed with environment folder)
            content_type: MIME type of the file
            
        Returns:
            str: S3 URL of the uploaded file, or None if upload failed
        """
        try:
            # Create S3 key with environment folder structure
            s3_key = f"{self.images_folder}/{filename}"
            
            # Upload file to S3
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'public-read'
                }
            )
            
            # Return public URL
            s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}"
            logger.info(f"Successfully uploaded {filename} to S3: {s3_url}")
            return s3_url
            
        except ClientError as e:
            logger.error(f"Error uploading {filename} to S3: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading {filename} to S3: {e}")
            return None
    
    def delete_image(self, filename):
        """
        Delete an image from S3
        
        Args:
            filename: Name of the file to delete (without environment folder prefix)
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            s3_key = f"{self.images_folder}/{filename}"
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Successfully deleted {filename} from S3")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting {filename} from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting {filename} from S3: {e}")
            return False
    
    def list_images(self, prefix=None):
        """
        List all images in the S3 bucket for the current environment
        
        Args:
            prefix: Optional prefix to filter images
            
        Returns:
            list: List of image filenames
        """
        try:
            s3_prefix = f"{self.images_folder}/"
            if prefix:
                s3_prefix += prefix
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=s3_prefix
            )
            
            images = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Remove the environment folder prefix from the key
                    filename = obj['Key'].replace(f"{self.images_folder}/", "")
                    images.append(filename)
            
            return images
            
        except ClientError as e:
            logger.error(f"Error listing images from S3: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing images from S3: {e}")
            return []
    
    def get_image_url(self, filename):
        """
        Get the public URL for an image stored in S3
        
        Args:
            filename: Name of the image file
            
        Returns:
            str: Public S3 URL for the image
        """
        s3_key = f"{self.images_folder}/{filename}"
        return f"https://{self.bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}"
    
    def create_folder_structure(self):
        """
        Create the initial folder structure in S3 (dev/images/ and prod/images/)
        This is mainly for documentation - S3 doesn't actually have folders
        """
        try:
            # Create a placeholder file to establish the folder structure
            for env in ['dev', 'prod']:
                placeholder_key = f"{env}/images/.gitkeep"
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=placeholder_key,
                    Body=b'# This file establishes the folder structure\n',
                    ContentType='text/plain'
                )
                logger.info(f"Created folder structure for {env}/images/")
            
            return True
            
        except ClientError as e:
            logger.error(f"Error creating S3 folder structure: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating S3 folder structure: {e}")
            return False

# Global S3 manager instance
s3_manager = S3Manager()
