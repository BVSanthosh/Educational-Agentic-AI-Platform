import aioboto3
from app.core.config import env
from uuid import uuid4

async def upload_document_to_s3(content: str, folder: str = "research_reports") -> dict:
    session = aioboto3.Session()
    file_name = f"{folder}/{uuid4()}.md"
    bucket_name = env.AWS_S3_BUCKET_NAME
    
    # Calculate exact byte size for your database model
    content_bytes = content.encode("utf-8")
    file_size_bytes = len(content_bytes)

    async with session.client('s3',
        aws_access_key_id=env.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=env.AWS_SECRET_ACCESS_KEY,
        region_name=env.AWS_REGION
    ) as s3:
        await s3.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=content_bytes,
            ContentType="text/markdown"
        )
        
        url = f"https://{bucket_name}.s3.{env.AWS_REGION}.amazonaws.com/{file_name}"
        
        return {
            "s3_key": file_name, 
            "url": url,
            "file_size_bytes": file_size_bytes,
            "mime_type": "text/markdown"
        }
        
async def read_document_from_s3(s3_key: str) -> str:
    """Fetches the complete text content of an S3 object into memory."""
    session = aioboto3.Session()
    bucket_name = env.AWS_S3_BUCKET_NAME
    
    async with session.client('s3',
        aws_access_key_id=env.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=env.AWS_SECRET_ACCESS_KEY,
        region_name=env.AWS_REGION
    ) as s3:  
        response = await s3.get_object(Bucket=bucket_name, Key=s3_key)
        async with response["Body"] as body:
            content_bytes = await body.read()
            return content_bytes.decode("utf-8")