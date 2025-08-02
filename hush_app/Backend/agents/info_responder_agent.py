import os
import requests
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain_core.documents import Document

load_dotenv()

# 🔍 SERPAPI Search (no changes)
def search_web_with_serpapi(query):
    params = {
        "q": query,
        "api_key": os.getenv("SERPAPI_API_KEY"),
        "engine": "google",
    }
    response = requests.get("https://serpapi.com/search", params=params)
    results = response.json()

    snippets = []
    for result in results.get("organic_results", [])[:5]:
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        link = result.get("link", "")
        if snippet:
            snippets.append(f"- {title}: {snippet} ({link})")
    return "\n".join(snippets)

# 🤖 Groq Call with Combined Context (no changes)
def call_llama_on_groq(query, doc_context="", web_context=""):
    template = """You are a helpful assistant that answers queries based on the given context.

              User Question:
              {query}

              {doc_context_block}

              {web_context_block}

              Respond in a clear and concise manner with relevant insights."""

    prompt = PromptTemplate.from_template(template)

    full_prompt = prompt.format(
        query=query,
        doc_context_block=f"Document Context:\n{doc_context}" if doc_context else "",
        web_context_block=f"Web Context:\n{web_context}" if web_context else "",
    )

    llm = ChatOpenAI(
        openai_api_key=os.getenv("GROQ_API_KEY"),
        openai_api_base="https://api.groq.com/openai/v1",
        model_name="llama3-70b-8192",
        temperature=0.4,
        max_tokens=2048,
    )
    response = llm.invoke(full_prompt)
    print(response.content)
    return response.content.strip()

# 🧠 Final Agent (Updated)
def info_responder_agent(query, doc_content: bytes = None, doc_filename: str = None):
    """
    Responds to a query using web search and an optionally provided document's content.

    Args:
        query (str): The user's question.
        doc_content (bytes, optional): The raw byte content of the document. Defaults to None.
        doc_filename (str, optional): The filename of the document (used for context). Defaults to None.
    """
    doc_context = ""
    
    # --- FIX: Process document content directly instead of a path ---
    if doc_content:
        print("🔍 Retrieving relevant chunks from provided document content...")
        try:
            # Decode content and create a LangChain Document
            decoded_content = doc_content.decode('utf-8', errors='ignore')
            doc = Document(page_content=decoded_content, metadata={"source": doc_filename or "uploaded_file"})

            # Chunking
            splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            chunks = splitter.split_documents([doc])

            # Embeddings & Retrieval
            embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
            vectorstore = FAISS.from_documents(chunks, embeddings)
            relevant_docs = vectorstore.similarity_search(query, k=3)
            doc_context = "\n\n".join([doc.page_content for doc in relevant_docs])
        except Exception as e:
            doc_context = f"Error processing the document: {e}"

    print("🌐 Searching the web...")
    web_context = search_web_with_serpapi(query)

    print("🧠 Generating response from LLaMA...")
    return call_llama_on_groq(query, doc_context, web_context)