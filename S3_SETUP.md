# S3 Image Storage Setup Guide

This guide explains how to configure AWS S3 for image storage in the Warborne Guild Tools project.

## Overview

The S3 integration provides:
- **Environment-based folder structure**: `dev/images/` and `prod/images/`
- **Automatic image uploads** from bot servers
- **Public access** to uploaded images
- **File validation** (type and size limits)
- **Staff-only upload permissions**

## Folder Structure

```
your-s3-bucket/
├── dev/
│   └── images/
│       ├── player_avatars/
│       ├── consumable_icons/
│       ├── equipment_icons/
│       └── ...
└── prod/
    └── images/
        ├── player_avatars/
        ├── consumable_icons/
        ├── equipment_icons/
        └── ...
```

## Configuration

### 1. Environment Variables

Add these variables to your `.env` file:

```bash
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_STORAGE_BUCKET_NAME=your-s3-bucket-name
AWS_S3_REGION_NAME=us-east-1
ENVIRONMENT=dev  # or 'prod' for production
```

### 2. AWS IAM Permissions

Create an IAM user with the following policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:PutObjectAcl"
            ],
            "Resource": "arn:aws:s3:::your-bucket-name/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::your-bucket-name"
        }
    ]
}
```

### 3. S3 Bucket Configuration

1. **Create S3 bucket** with public read access
2. **Enable CORS** for web access:

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": []
    }
]
```

3. **Bucket Policy** for public read access:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::your-bucket-name/*"
        }
    ]
}
```

## Setup Commands

### Initialize S3 Structure

```bash
# Create folder structure with placeholder files
python manage.py setup_s3_structure --create-placeholders

# Test connection only
python manage.py setup_s3_structure --bucket-name your-bucket-name
```

### Install Dependencies

```bash
pip install boto3==1.34.0 django-storages==1.14.2
```

## API Usage

### Upload Image (Staff Only)

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "image=@path/to/image.png" \
  -F "filename=my_image.png" \
  https://your-domain.com/api/upload-image/
```

**Response:**
```json
{
    "success": true,
    "message": "Image uploaded successfully",
    "filename": "my_image.png",
    "url": "https://your-bucket.s3.us-east-1.amazonaws.com/dev/images/my_image.png"
}
```

### Programmatic Usage

```python
from warborne_tools.s3_utils import s3_manager

# Upload image
with open('image.png', 'rb') as f:
    url = s3_manager.upload_image(f, 'my_image.png', 'image/png')

# Get image URL
url = s3_manager.get_image_url('my_image.png')

# List images
images = s3_manager.list_images()

# Delete image
success = s3_manager.delete_image('my_image.png')
```

## File Validation

- **Allowed types**: JPEG, PNG, GIF, WebP
- **Maximum size**: 10MB
- **Naming**: Auto-generated UUID if not provided

## Environment Separation

- **Development**: Images stored in `dev/images/`
- **Production**: Images stored in `prod/images/`
- **Automatic routing** based on `ENVIRONMENT` variable

## Security

- **Staff-only uploads**: Only authenticated staff users can upload
- **File validation**: Type and size checking
- **Public read access**: Images are publicly accessible via URL
- **Environment isolation**: Dev and prod images are separated

## Troubleshooting

### Common Issues

1. **Access Denied**: Check IAM permissions and bucket policy
2. **CORS Errors**: Verify CORS configuration on S3 bucket
3. **Connection Failed**: Check AWS credentials and region
4. **File Too Large**: Reduce file size (max 10MB)

### Debug Commands

```bash
# Test S3 connection
python manage.py setup_s3_structure

# Check existing images
python manage.py shell
>>> from warborne_tools.s3_utils import s3_manager
>>> s3_manager.list_images()
```

## Migration from Local Storage

If migrating from local static files:

1. **Upload existing images** to S3 using the API
2. **Update image URLs** in database/models
3. **Update frontend** to use S3 URLs
4. **Remove local files** after verification

## Monitoring

- **CloudWatch**: Monitor S3 usage and costs
- **Access logs**: Enable S3 access logging
- **Cost alerts**: Set up billing alerts for unexpected usage
