import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_MODEL_OPENAI = "openai/gpt-4.1"
OPENROUTER_MODEL_ANTHROPIC = "anthropic/claude-sonnet-4"
OPENROUTER_MODEL_DEEPSEEK = "deepseek/deepseek-r1"
OPENROUTER_MODEL_LLAMA = "meta-llama/llama-4-maverick"
OPENROUTER_MODEL_GEMINI = "google/gemini-2.5-flash"

LLAMA_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_MODEL = "text-embedding-3-small"

# Retrieval Configuration
TOP_K = 12
TOP_N_RERANK = 3

# File Paths
FAISS_INDEXES = {
    "sop": "data/_indexes/faiss_index_sop.index",
    "vmc": "data/_indexes/faiss_index_vmc.index", 
    "vra": "data/_indexes/faiss_index_vra.index",
    "pengadaan": "data/_indexes/faiss_index_pengadaan.index"
}

CHUNK_FILES = {
    "sop": "data/_chunks/sopchunks.txt",
    "vmc": "data/_chunks/vmcchunks.txt",
    "vra": "data/_chunks/vrachunks.txt", 
    "pengadaan": "data/_chunks/pengadaanchunks.txt"
}

KNOWLEDGE_FILES = {
    "sop": "data/_knowledge/sop.txt",
    "vmc": "data/_knowledge/vmc_knowledge.txt",
    "vra": "data/_knowledge/vra_knowledge.txt",
    "pengadaan": "data/_knowledge/pengadaan_knowledge.txt"
}


# Google Sheets Configuration
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "credentials.json")
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")

# System Prompts
CLASSIFIER_PROMPT = (
    "You are a smart document classifier for procurement policy documents with a fixed hierarchy:\n"
    "- VMC (Vendor Management Charter)\n"
    "- SOP (Standard Operating Procedures)\n"
    "- Pengadaan (Procurement Process)\n"
    "- VRA (Vendor Risk Assessment)\n\n"
    "When classifying a question, choose the highest relevant level in the hierarchy. "
    "For example:\n"
    "- If it's about the committee's internal structure, its ultimate authority, or the final approval on high-value and high-risk decisions, choose 'vmc'.\n"
    "- If it's about detailed, step-by-step operational workflows and approval flowcharts, particularly for the Vendor Risk Assessment (VRA) process, choose 'sop'.\n"
    "- If it's about all purchasing methods, financial thresholds, sourcing strategies, and the overall rules of engagement with vendors, choose 'pengadaan'.\n"
    "- If it's about understanding what specific risks to evaluate, use the Third-Party Risk Management Guideline (TPRA) or Vendor Risk Management Guideline (VRA); to understand the process of how to conduct the assessment, choose 'vra'.\n\n"
    "Always return exactly one of: vmc, sop, pengadaan, vra."
)

TRANSLATOR_PROMPT = (
    "Translate the following input into Indonesian. Only return the translated result. "
    "Do not explain or include extra output."
)

RERANK_PROMPT = (
    "You help assess chunk relevance. On a scale of 1 to 10, how relevant is this chunk to the question? "
    "Only respond with the number (no explanation)."
)

VENDOR_EXTRACTOR_PROMPT = (
    "You are a smart extractor. Given a question, extract the type (TPRA or VRA) "
    "and the vendor name if it exists. Always respond in JSON like: "
    '{"type": "tpra", "vendor": "PT. ABC"}'
    " or return null if no match."
)

ASSISTANT_PROMPT = (
    "You are a procurement assistant for Superbank Indonesia. "
    "Use the provided context to answer the user's question accurately and faithfully. "
    "If the context contains a clear answer, prioritize it and cite the relevant part. "
    "If you need to infer or reason based on the context, use a natural, conversational phrase to indicate this, such as 'Based on the information available...', 'It seems that...', 'As far as I can tell...', or 'From what I understand...'. "
    "Avoid repeating the same phrase and do not use formal language like 'The context does not explicitly state...'. "
    "Vary your wording to keep the conversation friendly and natural, but always make it clear when you are interpreting or deducing from the context. "
    "Never make up facts. Do not include general knowledge or assumptions that are not supported by the context. "
    "Always validate your answer against the provided context. If confidence is below 80%, say so and refer to procurement@superbank.id. If confidence is 80% or higher, do not include a referral unless the user asks for more information. "
    "Always offer another guidance or make sure that is what the user is trying to know after every response."
)

# Server Configuration
HOST = "0.0.0.0"
PORT = 3000 