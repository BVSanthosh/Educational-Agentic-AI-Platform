import aioboto3
from uuid import uuid4
from app.core.config import env 

# Create a module-level session for reusing connections
boto_session = aioboto3.Session()

async def upload_document_to_s3(content: str, filename: str, folder: str) -> dict:
    """
    Uploads a markdown string directly from memory to AWS S3.
    """
    # Generate the unique S3 path
    s3_key = f"{folder}/{filename}_{uuid4()}.md"
    
    # Convert the string to bytes
    content_bytes = content.encode("utf-8")
    file_size = len(content_bytes)
    mime_type = "text/markdown"
    
    # Write directly to S3
    async with boto_session.client("s3") as s3:
        await s3.put_object(
            Bucket=env.AWS_S3_BUCKET_NAME,
            Key=s3_key,
            Body=content_bytes,
            ContentType=mime_type
        )
        
    # Construct a standard S3 object URL
    # Note: If your bucket is private, this URL won't be publicly accessible in a browser.
    # The application will use the `s3_key` to fetch it securely via the backend.
    s3_url = f"https://{env.AWS_S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"

    return {
        "s3_key": s3_key, 
        "url": s3_url, 
        "file_size_bytes": file_size,
        "mime_type": mime_type
    }

async def read_document_from_s3(s3_key: str) -> str:
    """
    Reads a document directly from AWS S3 into memory and returns it as a string.
    """
    async with boto_session.client("s3") as s3:
        response = await s3.get_object(
            Bucket=env.AWS_S3_BUCKET_NAME,
            Key=s3_key
        )
        
        # In aioboto3, the 'Body' is an async stream that must be awaited
        content_bytes = await response['Body'].read()
        return content_bytes.decode("utf-8")