import os
import requests
from dotenv import load_dotenv
from typing import Optional

from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import ChatOpenAI

load_dotenv()


def search_web_with_serpapi(query):
    """
    Performs a web search using the SERPAPI to get context from the internet.
    """
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


def call_llama_on_groq(query, doc_context="", web_context="", knowledge_context=""):
    """
    Calls the LLaMA model via Groq with all available context to generate a final answer.
    """
    template = """You are a helpful assistant. Your goal is to answer a user's query using up to three sources of context: a provided document, web search results, and a local knowledge base of files.

User Question: {query}

document context:
{doc_context_block}
web context:
{web_context_block}
knowledge context:
{knowledge_context_block}

**Instructions:**
1. Synthesize the information from the available contexts to provide a comprehensive and relevant answer to the user's query.
2. You have access to a "Knowledge Base Context" which contains content from files. The filename is provided with the 'Source:' tag for each entry.
3. **Crucially, you should only recommend attaching a file under specific conditions:**
    a. The user's request (in the "User Question") explicitly asks for a document or suggests sending one.
    b. A document in the knowledge base is a near-perfect match for the query and serves as an essential reference that cannot be summarized effectively in the email body (e.g., a full PDF report, a detailed specification sheet).
4. If these conditions are met, and only then, you MUST signal that the best-matching file should be attached.
5. To signal the attachment, end your entire response with the exact tag on a new line: [ATTACH_FILE: <filename>], replacing `<filename>` with the correct source filename from the knowledge base context.
6. Do not hallucinate filenames. Only use the exact filename provided in the 'Source:' tag from the knowledge base context.
7. Do not mention the attachment tag in the conversational part of your response. First provide the complete answer, then add the tag on a new line if necessary. If no attachment is needed, do not add the tag.

Respond in a clear and concise manner with relevant insights.
"""
    prompt = PromptTemplate.from_template(template)
    full_prompt = prompt.format(
        query=query,
        doc_context_block=f"Document Context:\n{doc_context}" if doc_context else "",
        web_context_block=f"Web Context:\n{web_context}" if web_context else "",
        knowledge_context_block=f"Knowledge Base Context:\n{knowledge_context}" if knowledge_context else ""
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


def info_responder_agent(
    query: str,
    doc_content: Optional[bytes] = None,
    doc_filename: Optional[str] = None,
    knowledge_retriever: Optional[VectorStoreRetriever] = None
):
    """
    Responds to a query using web search, an optionally provided document,
    and a user-specific knowledge base (if consent is given).
    """
    # ✅ Google Embeddings instance
    embeddings = GoogleGenerativeAIEmbeddings(
        model="embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )

    # ---- DOCUMENT CONTEXT ----
    doc_context = ""
    if doc_content and doc_filename:
        # Only attempt to decode known text file extensions
        text_extensions = ['.txt', '.md', '.json', '.csv', '.py', '.js', '.html', '.xml']
        is_text_file = any(doc_filename.lower().endswith(ext) for ext in text_extensions)

        if is_text_file:
            try:
                # Attempt to decode the file as text
                decoded_content = doc_content.decode('utf-8')
                doc = Document(
                    page_content=decoded_content,
                    metadata={"source": doc_filename}
                )
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=500,
                    chunk_overlap=50
                )
                chunks = splitter.split_documents([doc])

                vectorstore = FAISS.from_documents(chunks, embeddings)
                relevant_docs = vectorstore.similarity_search(query, k=3)
                doc_context = "\n\n".join([doc.page_content for doc in relevant_docs])
            except Exception as e:
                # Handle cases where decoding or processing fails
                doc_context = f"Error processing the provided text file '{doc_filename}': {e}"
        else:
            # For binary or unknown files, just acknowledge the file's presence
            doc_context = f"A binary file named '{doc_filename}' was provided. Its content cannot be read as text, but the agent is aware of its presence."

    # ---- KNOWLEDGE BASE CONTEXT ----
    knowledge_context = ""
    if knowledge_retriever:
        print("📚 Searching the user's local knowledge base...")
        try:
            # Rebuild FAISS retriever using Google embeddings for consistency
            retrieved_docs = knowledge_retriever.invoke(query)
            knowledge_context = "\n\n".join(
                [f"Source: {doc.metadata['source']}\nContent: {doc.page_content}" for doc in retrieved_docs]
            )
        except Exception as e:
            knowledge_context = f"Error searching knowledge base: {e}"

    # ---- WEB CONTEXT ----
    print("🌐 Searching the web...")
    web_context = search_web_with_serpapi(query)

    # ---- LLaMA GENERATION ----
    print("🧠 Generating response from LLaMA...")
    return call_llama_on_groq(query, doc_context, web_context, knowledge_context)