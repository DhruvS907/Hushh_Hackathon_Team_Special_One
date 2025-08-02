import os
import json
import re
import base64
from datetime import timedelta, datetime
from typing import List, Dict
import concurrent.futures

# Required for handling token refresh
from google.auth.transport.requests import Request 
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def get_gmail_service():
    """
    Authenticates with the Gmail API and returns a service object.
    Creates or refreshes token.json.
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def call_llama_groq(prompt):
    """Invokes the Groq API with the specified prompt."""
    llm = ChatOpenAI(
        openai_api_key=os.environ["GROQ_API_KEY"],
        openai_api_base="https://api.groq.com/openai/v1",
        model="qwen/qwen3-32b",
        temperature=0.3,
    )
    response = llm.invoke(prompt)
    return response.content

def extract_json(response_text):
    """Extracts a JSON object from a string, ignoring surrounding text."""
    response_text = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL).strip()
    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            print("Invalid JSON structure in response.")
    else:
        print("No JSON found in response.")
    return None

def get_unread_emails(service):
    """Fetches unread emails from the last 24 hours using an efficient batch request."""
    today = datetime.now()
    query = f"is:unread after:{int((today - timedelta(days=1)).timestamp())}"
    
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])

    if not messages:
        return []

    all_emails_data = []

    def process_email_callback(request_id, response, exception):
        if exception:
            print(f"Error fetching email {request_id}: {exception}")
            return
        
        headers = response['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
        
        body = ''
        payload = response.get("payload", {})
        parts = payload.get("parts", [])
        
        if parts:
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
        else:
            data = payload.get('body', {}).get('data')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        all_emails_data.append({
            'id': response['id'],
            'threadId': response['threadId'],
            'subject': subject,
            'sender': sender,
            'snippet': response.get('snippet', ''),
            'body': body
        })

    batch = service.new_batch_http_request(callback=process_email_callback)

    for msg in messages:
        batch.add(service.users().messages().get(userId='me', id=msg['id'], format='full'))

    batch.execute()
    return all_emails_data

def summarize_emails(emails: List[Dict]) -> List[Dict]:
    """Generates a summary and determines the intent for a list of emails concurrently."""
    email_intents = [
        "Scheduling or rescheduling a meeting or event", "Following up on a previous conversation or task",
        "Requesting information or clarification", "Providing requested information or sharing details",
        "Requesting approval for a task or document", "Declining or cancelling a meeting or request",
        "Invoices, payments, or billing-related matters", "Raising or addressing a support or technical issue",
        "Marketing emails or newsletters", "Informational only – no action required (FYI)",
        "Providing a status update on a project or task", "Email that needs a decision or input",
        "Sending or requesting a quote or proposal", "Negotiating a job or business offer",
        "Reporting a bug or product issue", "Requesting a new feature or improvement",
        "Recruitment or HR-related message", "Scheduling or confirming a job interview",
        "Requesting a referral or recommendation", "Operations or compliance-related matter",
        "Legal, policy, or regulatory updates", "Announcing a new product or feature",
        "Shipping, delivery, or order tracking update", "Invitation to an event or webinar",
        "Thank you note or congratulatory message", "Personal message not related to work"
    ]

    def process_single_email(email):
        """Helper function to process one email."""
        prompt = f"""
        Analyze the following email and return a single, valid JSON object.
        Email Content:
        - From: {email['sender']}
        - Subject: {email['subject']}
        - Body Preview: {email['body'][:1000]}
        Instructions:
        1. Create a concise "summary" of the email.
        2. Categorize the email's "intent" by selecting the best fit from this list: {email_intents}
        JSON Output: {{ "summary": "...", "intent": "..." }}
        """
        response_content = call_llama_groq(prompt)
        response_dict = extract_json(response_content)

        if response_dict:
            email['summary'] = response_dict.get('summary', 'No summary generated.')
            email['intent'] = response_dict.get('intent', 'Unknown')
        else:
            email['summary'] = 'Failed to parse summary from AI response.'
            email['intent'] = 'Unknown'
        return email

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        summarized_results = list(executor.map(process_single_email, emails))

    return summarized_results

def get_thread_history(service, thread_id: str) -> List[Dict]:
    """
    Fetches all messages in a given thread for conversation history.
    """
    try:
        thread = service.users().threads().get(userId='me', id=thread_id, format='full').execute()
        history = []
        for msg in thread.get('messages', []):
            headers = msg.get('payload', {}).get('headers', [])
            history.append({
                "from": next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender'),
                "snippet": msg.get('snippet', '')
            })
        return history
    except Exception as e:
        print(f"Error fetching thread history for {thread_id}: {e}")
        return []
