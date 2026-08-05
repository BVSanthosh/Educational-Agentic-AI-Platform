from fastapi import HTTPException, status
from llama_index.core.workflow import Context
from uuid import UUID, uuid4
from sqlalchemy import update, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.services.summary_agent.models import summary_workflow
from app.models import Space
 
async def get_answer_and_persist(user_input: str, user_id: UUID, space_id: UUID, db: AsyncSession):
    ctx = Context(summary_workflow)
    
    try:
        response = await summary_workflow.run(user_msg=user_input, ctx=ctx)
        final_text = str(response).strip()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing summary agent: {str(e)}"
        )
        
    agent_message = {
        "id": uuid4(),
        "role": "agent",
        "content": final_text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    try:
        query = (
            update(Space)
            .where(Space.id == space_id, Space.user_id == user_id)
            .values(
                data=func.insert_jsonb(
                    Space.data,
                    "{messages, -1}",
                    func.to_jsonb(agent_message),
                    True
                ),
                updated_at=func.now()
            )
        )
        await db.execute(query)
        await db.commit()
    except Exception as db_err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist agent response: {str(db_err)}",
        )
    
    return final_text