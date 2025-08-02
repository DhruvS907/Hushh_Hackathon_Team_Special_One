import os
import base64
import numpy as np
from sklearn.preprocessing import normalize
import google.generativeai as genai
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import faiss
import pickle
from datetime import timedelta
import datetime

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, List, Sequence, Annotated
from langgraph.graph.message import add_messages


# Set Gemini API key
os.environ["GOOGLE_API_KEY"] = "your-gemini-api-key"  # 🔐 Replace with your key
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Setup Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    if os.path.exists('token.pkl'):
        with open('token.pkl', 'rb') as token:
            creds = pickle.load(token)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=8080)
        with open('token.pkl', 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

# Fetch past sent emails
def fetch_sent_emails(service, max_results=100):
    results = service.users().messages().list(userId='me', labelIds=['SENT'], maxResults=max_results).execute()
    messages = results.get('messages', [])

    emails = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_data['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        body = ''
        payload = msg_data['payload']

        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
        else:
            data = payload.get('body', {}).get('data')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        if body.strip():
            emails.append({"subject": subject, "body": body})
    return emails

# Gemini embedding
def get_gemini_embedding(text: str) -> np.ndarray:
    model = genai.get_model("gemini-embedding-001")
    response = model.embed_content(content=text, task_type="RETRIEVAL_DOCUMENT")
    return np.array(response["embedding"])

# Weighted embedding
def get_weighted_embedding(subject, body, subject_weight=0.3, body_weight=0.7) -> np.ndarray:
    subject_emb = get_gemini_embedding(subject)
    body_emb = get_gemini_embedding(body)
    combined = subject_weight * subject_emb + body_weight * body_emb
    return normalize([combined])[0]

# Build FAISS index
def build_faiss_index(emails):
    dim = len(get_gemini_embedding("test"))  # 768
    index = faiss.IndexFlatL2(dim)
    metadata = []

    for email in emails:
        emb = get_weighted_embedding(email["subject"], email["body"])
        index.add(np.array([emb]).astype('float32'))
        metadata.append(email)

    return index, metadata

# Search
def search_similar_email(query_subject, query_body, index, metadata, k=3):
    query_emb = get_weighted_embedding(query_subject, query_body)
    D, I = index.search(np.array([query_emb]).astype('float32'), k)
    return [metadata[i] for i in I[0]]

# Fetching unread emails
def get_unread_emails(service):
    today = datetime.utcnow()
    query = f"is:unread after:{int((today - timedelta(days=1)).timestamp())}"
    
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])

    emails = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_data['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
        snippet = msg_data.get('snippet', '')

        # Default to empty body
        body = ''

        # Check parts for actual email body (text/plain)
        payload = msg_data.get("payload", {})
        parts = payload.get("parts", [])
        
        if parts:
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
        else:
            # If no parts, check body directly
            data = payload.get('body', {}).get('data')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        emails.append({
            'subject': subject,
            'sender': sender,
            'snippet': snippet,
            'body': body
        })
    return emails

## --> Constructing the state variable
class AgentState:
    messages = Annotated[Sequence[BaseMessage], add_messages]
    top_3_similar_messages: List[dict]
    current_email = List[str]