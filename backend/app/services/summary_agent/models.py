from llama_index.core import VectorStoreIndex
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.llms.google_genai import GoogleGenAI 
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from app.core.config import env

llm = GoogleGenAI(model="gemini-2.5-flash", api_key=env.GEMINI_API_KEY)
embed_model = GoogleGenAIEmbedding(model_name="gemini-embedding-2", api_key=env.GEMINI_API_KEY)
splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)

PG_CONN_STRING = env.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

vector_store = PGVectorStore.from_params(
    connection_string=PG_CONN_STRING, 
    async_connection_string=env.DATABASE_URL,
    table_name="document_chunks",
    embed_dim=3072,
    perform_setup=False,
)

index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store,
    embed_model=embed_model
)

def search_document(search_query: str, space_id: str) -> str:
    """
    Search the uploaded document in pgvector to retrieve relevant facts, figures, 
    context, and excerpts necessary to answer the user's question.
    """
    
    filters = MetadataFilters(
        filters=[ExactMatchFilter(key="space_id", value=space_id)]
    )
    query_engine = index.as_query_engine(
        similarity_top_k=3,
        filters=filters,
        llm=llm
    )
    retrival_response = query_engine.query(search_query)
    
    return str(retrival_response)

summary_workflow = FunctionAgent(
    llm=llm,
    tools=[search_document],
    system_prompt=(
        "You are an expert Q&A assistant for a provided document. "
        "Always use the 'search_document' tool to fetch information from "
        "the document before answering the user's question."
    )
)