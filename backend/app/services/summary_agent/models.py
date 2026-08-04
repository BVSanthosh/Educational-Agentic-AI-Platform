from llama_index.core import Settings
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import TitleExtractor
from llama_index.llms.google_genai import GoogleGenAI
from app.core.config import env

llm = GoogleGenAI(
    model="gemini-2.5-flash",
    api_key=env.GEMINI_API_KEY
)
embed_model = GoogleGenAIEmbedding(
    model_name="gemini-embedding-2",
    api_key=env.GEMINI_API_KEY,
)

Settings.llm = llm
Settings.embed_model = embed_model

splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
extractor = TitleExtractor()