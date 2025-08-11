from fastapi import FastAPI, HTTPException, Depends, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests
from google.oauth2.credentials import Credentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from sqlalchemy import Column, Integer, String, Text, DateTime, LargeBinary, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from typing import Optional, List, Dict
import json
import base64
import os
import sys
import logging
import traceback
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Load environment variables from the project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Add project root to path to find other modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import your existing modules
import Email_Summarizer
from Orchestration_agent.agent import process_email_with_orchestration

# Import HushhMCP components
from hushh_mcp.consent.token import issue_token
from hushh_mcp.constants import ConsentScope

# === CONFIG ===
CLIENT_ID = "387653948430-kmg1urmijluvtrbkin3736ffcvbduv9b.apps.googleusercontent.com"
DATABASE_URL = "sqlite:///./users.db"

# Configure logging
logging.basicConfig(level=logging.INFO)

# === APP SETUP ===
app = FastAPI()

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# === DB SETUP ===
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    linkedin = Column(String, nullable=True)
    github = Column(String, nullable=True)
    gmail = Column(String, nullable=False, unique=True)
    hashed_password = Column(String, nullable=True)

class EmailResponse(Base):
    __tablename__ = "email_responses"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, nullable=False)
    sender_email = Column(String, nullable=False)
    email_subject = Column(String, nullable=False)
    email_summary = Column(Text, nullable=False)
    email_intent = Column(String, nullable=False)
    generated_response = Column(Text, nullable=False)
    agent_type = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.now)
    user_suggestion = Column(Text, nullable=True)
    email_id = Column(String, nullable=True)
    gmail_message_id = Column(String, nullable=True)
    gmail_thread_id = Column(String, nullable=True)
    consent_token = Column(String, nullable=True)
    attachment_filename = Column(String, nullable=True)
    attachment_content = Column(LargeBinary, nullable=True)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === MODELS ===
class TokenRequest(BaseModel):
    token: str
    # NEW: Add token expiry setting to token requests
    token_expiry_hours: Optional[int] = 24

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str
    # NEW: Add token expiry setting to login requests
    token_expiry_hours: Optional[int] = 24

class UserProfileDetails(BaseModel):
    name: str
    linkedin: Optional[str] = None
    github: Optional[str] = None
    gmail: str

class EmailProcessRequest(BaseModel):
    email_id: str
    consent_token: str
    user_suggestion: Optional[str] = None
    user_email: Optional[str] = None
    gmail_message_id: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    knowledge_base_consent_token: Optional[str] = None

class KbTokenRequest(BaseModel):
    user_email: str

# === HELPER FUNCTIONS ===
def get_user_access_token() -> Optional[str]:
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), 'token.json')
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, Email_Summarizer.SCOPES)
        if creds and creds.token:
            return creds.token
    return None

def send_email(service, to: str, subject: str, message_text: str, attachment: Optional[Dict] = None):
    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject
    message.attach(MIMEText(message_text, 'plain'))

    if attachment and attachment.get('filename') and attachment.get('content'):
        part = MIMEApplication(attachment['content'], Name=attachment['filename'])
        part['Content-Disposition'] = f'attachment; filename="{attachment["filename"]}"'
        message.attach(part)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {'raw': raw_message}
    try:
        message = (service.users().messages().send(userId='me', body=body).execute())
        return message
    except Exception as e:
        print(f"An error occurred while sending email: {e}")
        return None

def mark_email_as_read(service, message_id):
    try:
        return service.users().messages().modify(
            userId='me', id=message_id, body={'removeLabelIds': ['UNREAD']}
        ).execute()
    except Exception as e:
        print(f"An error occurred while marking email as read: {e}")
        return None

def generate_email_id(subject: str, sender: str) -> str:
    content = subject + sender
    hash_value = 0
    for char in content:
        hash_value = ((hash_value << 5) - hash_value) + ord(char)
        hash_value &= 0xFFFFFFFF
    return str(abs(hash_value))

def find_email_by_id(email_id: str, emails: List[Dict]) -> Optional[Dict]:
    for email in emails:
        if generate_email_id(email.get('subject', ''), email.get('sender', '')) == email_id:
            return email
    return None

def get_user_kb_path(user_email: str) -> str:
    base_path = os.path.join(os.path.dirname(__file__), "user_knowledge_bases")
    sanitized_email = user_email.replace("@", "_at_").replace(".", "_dot_")
    user_path = os.path.join(base_path, sanitized_email)
    os.makedirs(user_path, exist_ok=True)
    return user_path

# === AUTHENTICATION ROUTES ===

@app.post("/auth/signup")
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.gmail == user_data.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = generate_password_hash(user_data.password)
    new_user = User(name=user_data.name, gmail=user_data.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully", "user": {"name": new_user.name, "email": new_user.gmail}}

@app.post("/auth/login")
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.gmail == user_data.email).first()
    if not user or not check_password_hash(user.hashed_password, user_data.password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # MODIFIED: Use the expiry from the request
    expires_in_ms = (user_data.token_expiry_hours or 24) * 3600 * 1000
    
    consent_token_obj = issue_token(
        user_id=user.gmail,
        agent_id="default_agent",
        scope=ConsentScope.VAULT_READ_EMAIL,
        expires_in_ms=expires_in_ms
    )
    
    return {
        "message": "Login successful",
        "user": {"id": user.id, "name": user.name, "email": user.gmail},
        "consent_token": consent_token_obj.token
    }

@app.post("/auth/google")
async def auth_google(request: TokenRequest, db: Session = Depends(get_db)):
    try:
        logging.info(f"Received Google token for authentication.")
        if not CLIENT_ID:
            logging.error("GOOGLE_CLIENT_ID is not set in the environment variables.")
            raise HTTPException(status_code=500, detail="Server configuration error: Missing Google Client ID.")

        idinfo = id_token.verify_oauth2_token(request.token, requests.Request(), CLIENT_ID)
        email = idinfo['email']
        name = idinfo.get('name', 'Google User')
        logging.info(f"Token verified for email: {email}")

        user = db.query(User).filter(User.gmail == email).first()

        if not user:
            logging.info(f"User with email {email} not found. Creating new user.")
            new_user = User(name=name, gmail=email)
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user = new_user
        
        # MODIFIED: Use the expiry from the request
        expires_in_ms = (request.token_expiry_hours or 24) * 3600 * 1000

        consent_token_obj = issue_token(
            user_id=user.gmail,
            agent_id="default_agent",
            scope=ConsentScope.VAULT_READ_EMAIL,
            expires_in_ms=expires_in_ms
        )
        
        logging.info(f"Successfully authenticated user: {email}")
        return {
            "message": "Authentication successful",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.gmail,
                "github": user.github,
                "linkedin": user.linkedin,
            },
            "consent_token": consent_token_obj.token
        }
    except ValueError as e:
        logging.error(f"Google token verification failed: {e}. This may be due to an invalid token or incorrect CLIENT_ID.")
        raise HTTPException(status_code=401, detail="Invalid Google token. Verification failed.")
    except Exception as e:
        logging.error(f"An unexpected error occurred during Google authentication: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred during Google authentication.")

# === API ROUTES ===

@app.post("/api/summarize")
async def summarize_emails_api():
    try:
        service = Email_Summarizer.get_gmail_service()
        emails = Email_Summarizer.get_unread_emails(service)
        return {"emails": Email_Summarizer.summarize_emails(emails)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error summarizing emails: {str(e)}")

@app.post("/api/process-email")
async def process_email(request: EmailProcessRequest, db: Session = Depends(get_db)):
    try:
        service = Email_Summarizer.get_gmail_service()
        emails = Email_Summarizer.get_unread_emails(service)
        summarized_emails = Email_Summarizer.summarize_emails(emails)
        
        target_email = find_email_by_id(request.email_id, summarized_emails)
        if not target_email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        user_email = request.user_email
        if not user_email:
             raise HTTPException(status_code=400, detail="User email is required.")

        user = db.query(User).filter(User.gmail == user_email).first()
        user_name = user.name if user else "Support Team"
        
        conversation_history = []
        if target_email.get('threadId'):
            history_messages = Email_Summarizer.get_thread_history(service, target_email['threadId'])
            conversation_history = [f"From: {msg['from']}\nSnippet: {msg['snippet']}" for msg in history_messages]

        access_token = get_user_access_token()
        if not access_token:
            raise HTTPException(status_code=401, detail="User access token not found. Please re-authenticate.")

        result = process_email_with_orchestration(
            email_data=target_email, 
            user_email=user_email, 
            user_name=user_name, 
            consent_token=request.consent_token,
            access_token=access_token,
            user_suggestion=request.user_suggestion,
            conversation_history=conversation_history,
            knowledge_base_consent_token=request.knowledge_base_consent_token
        )
        
        attachment = result.get('attachment')
        
        email_response = EmailResponse(
            user_email=user_email,
            sender_email=target_email['sender'],
            email_subject=target_email['subject'],
            email_summary=target_email['summary'],
            email_intent=target_email['intent'],
            generated_response=result.get('message', 'No response generated'),
            agent_type=result.get('response_type', 'unknown'),
            user_suggestion=request.user_suggestion,
            email_id=request.email_id,
            gmail_message_id=target_email.get('id'),
            gmail_thread_id=target_email.get('threadId'),
            consent_token=request.consent_token,
            attachment_filename=attachment['filename'] if attachment else None,
            attachment_content=attachment['content'] if attachment else None
        )
        db.add(email_response)
        db.commit()
        db.refresh(email_response)
        
        json_safe_result = result.copy()
        if json_safe_result.get('attachment') and json_safe_result['attachment'].get('content'):
            content_bytes = json_safe_result['attachment']['content']
            json_safe_result['attachment']['content_b64'] = base64.b64encode(content_bytes).decode('ascii')
            del json_safe_result['attachment']['content']

        return {
            "response_id": email_response.id,
            "email_data": target_email,
            "generated_response": json_safe_result,
            "status": "pending"
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logging.error(f"Error processing email: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing email: {str(e)}")

@app.post("/api/generate-kb-token")
def generate_kb_token(req: KbTokenRequest):
    if not req.user_email:
        raise HTTPException(status_code=400, detail="User email is required")
    try:
        scope = ConsentScope.KNOWLEDGE_BASE_READ
        expiry_seconds = 300
        
        consent_token_obj = issue_token(
            user_id=req.user_email,
            agent_id="default_agent",
            scope=scope,
            expires_in_ms=expiry_seconds * 1000
        )
        
        token_string = consent_token_obj.token
        
        return {"kb_consent_token": token_string}
    except Exception as e:
        logging.error(f"Could not generate KB consent token: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Could not generate consent token: {str(e)}")

@app.post("/api/response-action")
async def handle_response_action(
    response_id: int = Form(...),
    action: str = Form(...),
    user_suggestion: Optional[str] = Form(None),
    send_attachment: bool = Form(True),
    file: Optional[UploadFile] = File(None),
    knowledge_base_consent_token: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        original_response = db.query(EmailResponse).filter(EmailResponse.id == response_id).first()
        if not original_response:
            raise HTTPException(status_code=404, detail="Original response not found")

        service = Email_Summarizer.get_gmail_service()

        if action == "approve":
            attachment_data = None
            if send_attachment and original_response.attachment_filename and original_response.attachment_content:
                attachment_data = {
                    "filename": original_response.attachment_filename,
                    "content": original_response.attachment_content
                }
            
            send_email(
                service, 
                original_response.sender_email, 
                original_response.email_subject, 
                original_response.generated_response,
                attachment=attachment_data
            )
            
            if original_response.gmail_message_id:
                mark_email_as_read(service, original_response.gmail_message_id)
            original_response.status = "approved"
            db.commit()

            if attachment_data and send_attachment:
                return {"message": "Email approved and sent successfully with attachment."}
            elif not send_attachment and original_response.attachment_filename:
                return {"message": "Email approved and sent successfully without the attachment."}
            else:
                return {"message": "Email approved and sent successfully."}

        elif action == "reject":
            original_response.status = "rejected"
            db.commit()
            return {"message": "Response rejected"}

        elif action == "regenerate":
            document_content = await file.read() if file else None
            document_filename = file.filename if file else None
            user = db.query(User).filter(User.gmail == original_response.user_email).first()
            user_name = user.name if user else "Support Team"
            
            conversation_history = []
            if original_response.gmail_thread_id:
                history_messages = Email_Summarizer.get_thread_history(service, original_response.gmail_thread_id)
                conversation_history = [f"From: {msg['from']}\nSnippet: {msg['snippet']}" for msg in history_messages]

            access_token = get_user_access_token()
            if not access_token:
                raise HTTPException(status_code=401, detail="User access token not found.")

            result = process_email_with_orchestration(
                email_data={"subject": original_response.email_subject, "sender": original_response.sender_email, "summary": original_response.email_summary, "intent": original_response.email_intent, "body": "", "snippet": ""},
                user_email=original_response.user_email,
                user_name=user_name,
                user_suggestion=user_suggestion,
                consent_token=original_response.consent_token,
                access_token=access_token,
                document_content=document_content,
                document_filename=document_filename,
                conversation_history=conversation_history,
                knowledge_base_consent_token=knowledge_base_consent_token
            )
            
            attachment = result.get('attachment')
            
            original_response.generated_response = result.get('message', 'No response generated')
            original_response.agent_type = result.get('response_type', 'unknown')
            original_response.user_suggestion = user_suggestion
            original_response.created_at = datetime.now()
            original_response.attachment_filename = attachment['filename'] if attachment else None
            original_response.attachment_content = attachment['content'] if attachment else None
            
            db.commit()
            db.refresh(original_response)
            
            json_safe_result = result.copy()
            if json_safe_result.get('attachment') and json_safe_result['attachment'].get('content'):
                content_bytes = json_safe_result['attachment']['content']
                json_safe_result['attachment']['content_b64'] = base64.b64encode(content_bytes).decode('ascii')
                del json_safe_result['attachment']['content']
            
            return {"message": "Response regenerated successfully", "generated_response": json_safe_result, "status": "pending", "response_id": original_response.id}
        else:
            raise HTTPException(status_code=400, detail="Invalid action specified")
            
    except Exception as e:
        logging.error(f"Error in response action: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# === KNOWLEDGE BASE MANAGEMENT ROUTES ===

@app.get("/api/knowledge-base/files")
async def list_kb_files(user_email: str):
    if not user_email:
        raise HTTPException(status_code=400, detail="User email is required.")
    
    user_kb_path = get_user_kb_path(user_email)
    try:
        files = [f for f in os.listdir(user_kb_path) if os.path.isfile(os.path.join(user_kb_path, f))]
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not list files: {str(e)}")

@app.post("/api/knowledge-base/upload")
async def upload_kb_file(user_email: str = Form(...), file: UploadFile = File(...)):
    if not user_email:
        raise HTTPException(status_code=400, detail="User email is required.")

    user_kb_path = get_user_kb_path(user_email)
    filename = secure_filename(file.filename)
    file_path = os.path.join(user_kb_path, filename)

    if os.path.exists(file_path):
        raise HTTPException(status_code=409, detail=f"File '{filename}' already exists.")

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        return {"message": f"File '{filename}' uploaded successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not upload file: {str(e)}")

@app.delete("/api/knowledge-base/files/{filename}")
async def delete_kb_file(user_email: str, filename: str):
    if not user_email:
        raise HTTPException(status_code=400, detail="User email is required.")

    user_kb_path = get_user_kb_path(user_email)
    secure_name = secure_filename(filename)
    file_path = os.path.join(user_kb_path, secure_name)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")

    try:
        os.remove(file_path)
        return {"message": f"File '{filename}' deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not delete file: {str(e)}")

# === NEW: SETTINGS ENDPOINTS ===

@app.get("/api/user-details")
async def get_user_details(user_email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.gmail == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"name": user.name, "linkedin": user.linkedin, "github": user.github}

@app.post("/api/update-settings")
async def update_settings(details: UserProfileDetails, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.gmail == details.gmail).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.name = details.name
    user.linkedin = details.linkedin
    user.github = details.github
    
    db.commit()
    return {"message": "User details updated successfully."}


# === HISTORY & PENDING ENDPOINTS ===

def serialize_response(response_obj: EmailResponse) -> Dict:
    """Safely serializes an EmailResponse object, handling binary data."""
    response_dict = {c.name: getattr(response_obj, c.name) for c in response_obj.__table__.columns}
    if isinstance(response_dict.get('attachment_content'), bytes):
        response_dict['attachment_content'] = base64.b64encode(response_dict['attachment_content']).decode('ascii')
    return response_dict

@app.get("/api/pending-responses")
async def get_pending_responses(user_email: str, db: Session = Depends(get_db)):
    responses = db.query(EmailResponse).filter(EmailResponse.user_email == user_email, EmailResponse.status == "pending").order_by(EmailResponse.created_at.desc()).all()
    
    serialized_responses = [serialize_response(r) for r in responses]
    return {"pending_responses": serialized_responses}

@app.get("/api/response-history")
async def get_response_history(user_email: str, db: Session = Depends(get_db)):
    from sqlalchemy import or_
    responses = db.query(EmailResponse).filter(
        EmailResponse.user_email == user_email,
        or_(EmailResponse.status == "approved", EmailResponse.status == "rejected")
    ).order_by(EmailResponse.created_at.desc()).limit(50).all()
    
    serialized_responses = [serialize_response(r) for r in responses]
    return {"response_history": serialized_responses}
