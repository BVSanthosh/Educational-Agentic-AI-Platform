import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.workflow import Context
from llama_index.vector_stores.chroma import ChromaVectorStore
from app.services.summary_agent.models import llm
 
async def get_answer(query: str, doc_id: str):
    db = chromadb.PersistentClient(path="./chromadb")
    chroma_collection = db.get_or_create_collection(doc_id)
    vectore_store = ChromaVectorStore(chroma_collection=chroma_collection)

    index = VectorStoreIndex.from_vector_store(vector_store=vectore_store)
    query_engine = index.as_query_engine(similarity_top_k=3)

    def get_embeddings(search_query: str):
        """
        Search the uploaded document to retrieve relevant facts, figures, context, 
        and excerpts necessary to answer the user's question.
        """
        retrieval_response = query_engine.query(search_query)
        return str(retrieval_response)

    workflow = FunctionAgent(
        llm=llm,
        tools=[get_embeddings],
        system_prompt=(
            "You are an expert Q&A assistant for a provided document. "
            "Always use the 'search_document' tool to fetch information from "
            "the document before answering the user's question."
        )
    )
    ctx = Context(workflow)

    response = await workflow.run(user_msg=query, ctx=ctx)
    return str(response)