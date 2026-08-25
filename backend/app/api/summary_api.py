import tempfile
import os
import aioboto3
from uuid import UUID, uuid4
from fastapi import HTTPException, status,Depends
from fastapi.responses import StreamingResponse
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Annotated, AsyncGenerator
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update, func, String, cast
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.summary_agent.ingestion_pipeline import stream_embed_and_summarise
from app.services.summary_agent.summary_agent import stream_get_answer_and_persist
from app.utils import get_current_usr
from app.core.database import get_db
from app.models import User, Space 
from app.schemas import SummaryRequest, PresignedUrlRequest, ProcessS3DocumentRequest
from app.core.config import env

router = APIRouter(prefix="/api/summary", tags=["Summary"])

boto_session = aioboto3.Session()

@router.post("/presigned-url")
async def get_presigned_url(
    request: PresignedUrlRequest,
    current_user: Annotated[User, Depends(get_current_usr)], 
    session: Annotated[AsyncSession, Depends(get_db)]
):
    space_query = select(Space).where(Space.id == request.space_id, Space.user_id == current_user.id)
    space = (await session.scalars(space_query)).one_or_none()
    
    if not space:
        raise HTTPException(status_code=400, detail="Space couldn't be found")
        
    unique_id = uuid4().hex
    s3_key = f"summary/{current_user.id}/{request.space_id}_{unique_id}_{request.filename}"

    try:
        async with boto_session.client("s3") as s3:
            # generate_presigned_post allows strict file size conditions
            presigned_post = await s3.generate_presigned_post(
                Bucket=env.AWS_S3_BUCKET_NAME,
                Key=s3_key,
                Fields={"Content-Type": request.content_type},
                Conditions=[
                    {"Content-Type": request.content_type},
                    ["content-length-range", 1, 10485760]  # 1 byte to 10 MB limit strictly enforced by AWS
                ],
                ExpiresIn=300
            )
            
        # presigned_post returns a dict with 'url' and 'fields'
        return {"upload_data": presigned_post, "s3_key": s3_key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL: {str(e)}")


async def generate_and_cleanup_stream(filename: str, s3_key: str, space_id: UUID, user_id: UUID):
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = tmp.name
            
        async with boto_session.client("s3") as s3:
            await s3.download_file(env.AWS_S3_BUCKET_NAME, s3_key, tmp_path)

        # PASS s3_key TO THE FUNCTION HERE:
        async for chunk in stream_embed_and_summarise(filename, tmp_path, s3_key, space_id, user_id):
            yield chunk

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/process-document")
async def process_document(
    request: ProcessS3DocumentRequest,
    current_user: Annotated[User, Depends(get_current_usr)], 
    session: Annotated[AsyncSession, Depends(get_db)]
) -> StreamingResponse:
    
    space_query = select(Space).where(Space.id == request.space_id, Space.user_id == current_user.id)
    space = (await session.scalars(space_query)).one_or_none()
    
    if not space:
        raise HTTPException(status_code=400, detail="Space couldn't be found")

    try:
        update_status_query = (
            update(Space)
            .where(Space.id == request.space_id, Space.user_id == current_user.id)
            .values(
                data=func.jsonb_set(
                    Space.data,
                    cast(["status"], ARRAY(String)),
                    cast('"processing"', JSONB), 
                    True  
                ),
                updated_at=func.now(),
                upload_status="chat"
            )
        )
        await session.execute(update_status_query)
        await session.commit()
    except Exception as db_err:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update processing status: {str(db_err)}")
    
    return StreamingResponse(
        generate_and_cleanup_stream(request.filename, request.s3_key, space.id, current_user.id),
        media_type="text/event_stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
            
@router.post("/{space_id}/query")
async def answer_query(
    space_id: UUID, 
    body: SummaryRequest, 
    current_user: Annotated[User, Depends(get_current_usr)], 
    session: Annotated[AsyncSession, Depends(get_db)]
) -> StreamingResponse:
    
    # 1. Verify Space exists
    space_query = select(Space).where(Space.id == space_id, Space.user_id == current_user.id)
    space = (await session.scalars(space_query)).one_or_none()
    
    if not space:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Space couldn't be found"
        )
        
    # 2. Persist the User's message to the database immediately
    user_message = {
        "id": str(uuid4()),
        "role": "user",
        "content": body.user_input,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        update_user_message = (
            update(Space)
            .where(Space.id == space_id, Space.user_id == current_user.id)
            .values(
                data=func.jsonb_insert(
                    Space.data, 
                    cast(["messages", "-1"], ARRAY(String)),
                    cast(user_message, JSONB),
                    True
                ),
                updated_at=func.now()
            )
        )
        await session.execute(update_user_message)
        await session.commit()
    except Exception as db_err:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist user input: {str(db_err)}"
        )
        
    stream_generator: AsyncGenerator[str, None] = stream_get_answer_and_persist(
        user_input=body.user_input,
        user_id=current_user.id,
        space_id=space_id,
        thread_id=str(space.thread_id)
    )

    # 3. Return the Streaming Response
    return StreamingResponse(
        stream_generator,
        media_type="text/event_stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )