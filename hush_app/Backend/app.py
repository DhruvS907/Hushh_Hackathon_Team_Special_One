from fastapi import FastAPI, HTTPException, Depends, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import hashlib
import base64
from email.mime.text import MIMEText
import os
import sys
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

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
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
DATABASE_URL = "sqlite:///./users.db"

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
    # Store the consent token to allow for regeneration actions
    consent_token = Column(String, nullable=True)


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

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserDetails(BaseModel):
    name: str
    linkedin: str
    github: str
    gmail: str

class EmailProcessRequest(BaseModel):
    email_id: str
    consent_token: str
    user_suggestion: Optional[str] = None
    user_email: Optional[str] = None
    gmail_message_id: Optional[str] = None
    gmail_thread_id: Optional[str] = None

# === HELPER FUNCTIONS ===
def send_email(service, to, subject, message_text):
    message = MIMEText(message_text)
    message['to'] = to
    message['subject'] = subject
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
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
    except Exception as e:
        print(f"An error occurred while marking email as read: {e}")
        return None

def generate_email_id(subject: str, sender: str) -> str:
    content = subject + sender
    hash_value = 0
    for char in content:
        hash_value = ((hash_value << 5) - hash_value) + ord(char)
        hash_value = hash_value & 0xFFFFFFFF
        if hash_value >= 0x80000000:
            hash_value -= 0x100000000
    return str(abs(hash_value))

def find_email_by_id(email_id: str, emails: List[Dict]) -> Optional[Dict]:
    for email in emails:
        if generate_email_id(email.get('subject', ''), email.get('sender', '')) == email_id:
            return email
    return None

# === ROUTES ===
@app.post("/auth/google")
def authenticate_user(req: TokenRequest, db: Session = Depends(get_db)):
    try:
        idinfo = id_token.verify_oauth2_token(req.token, requests.Request(), CLIENT_ID)
        user_email = idinfo.get("email")
        user = db.query(User).filter(User.gmail == user_email).first()
        token_obj = issue_token(user_id=user_email, agent_id="OrchestrationAgent", scope=ConsentScope.VAULT_READ_EMAIL)
        if user:
            return {"exists": True, "idinfo": idinfo, "consent_token": token_obj.token, "user_data": {"name": user.name, "email": user.gmail, "linkedin": user.linkedin, "github": user.github}}
        else:
            return {"exists": False, "idinfo": idinfo, "consent_token": token_obj.token}
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/signup-email")
def signup_email(user_create: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.gmail == user_create.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = generate_password_hash(user_create.password)
    new_user = User(name=user_create.name, gmail=user_create.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

@app.post("/api/signin-email")
def signin_email(user_login: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.gmail == user_login.email).first()
    if not user or not user.hashed_password or not check_password_hash(user.hashed_password, user_login.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token_obj = issue_token(user_id=user.gmail, agent_id="OrchestrationAgent", scope=ConsentScope.VAULT_READ_EMAIL)
    return {"message": "Login successful", "consent_token": token_obj.token, "user_data": {"name": user.name, "email": user.gmail}}

@app.post("/api/signup-details")
def signup_details(user_details: UserDetails, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.gmail == user_details.gmail).first()
    if user:
        user.name = user_details.name
        user.linkedin = user_details.linkedin
        user.github = user_details.github
    else:
        new_user = User(name=user_details.name, linkedin=user_details.linkedin, github=user_details.github, gmail=user_details.gmail)
        db.add(new_user)
    db.commit()
    return {"message": "User details saved successfully"}

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
        
        user_email = request.user_email or "user@example.com"
        user = db.query(User).filter(User.gmail == user_email).first()
        user_name = user.name if user else "Support Team"
        
        conversation_history = []
        if target_email.get('threadId'):
            history_messages = Email_Summarizer.get_thread_history(service, target_email['threadId'])
            conversation_history = [f"From: {msg['from']}\nSnippet: {msg['snippet']}" for msg in history_messages]

        result = process_email_with_orchestration(
            email_data=target_email, 
            user_email=user_email, 
            user_name=user_name, 
            consent_token=request.consent_token,
            user_suggestion=request.user_suggestion,
            conversation_history=conversation_history
        )
        
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
            consent_token=request.consent_token
        )
        db.add(email_response)
        db.commit()
        db.refresh(email_response)
        
        return {
            "response_id": email_response.id,
            "email_data": target_email,
            "generated_response": result,
            "status": "pending"
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing email: {str(e)}")

@app.post("/api/response-action")
async def handle_response_action(
    response_id: int = Form(...),
    action: str = Form(...),
    user_suggestion: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    try:
        original_response = db.query(EmailResponse).filter(EmailResponse.id == response_id).first()
        if not original_response:
            raise HTTPException(status_code=404, detail="Original response not found")

        if action == "approve" or action == "reject":
            response_to_action = db.query(EmailResponse).filter(
                EmailResponse.gmail_thread_id == original_response.gmail_thread_id,
                EmailResponse.status == "pending"
            ).order_by(EmailResponse.created_at.desc()).first()

            if not response_to_action:
                raise HTTPException(status_code=404, detail="No pending response found to action.")

            if action == "approve":
                service = Email_Summarizer.get_gmail_service()
                recipient_email = response_to_action.sender_email.split('<')[-1].strip('>')
                send_email(service, recipient_email, f"Re: {response_to_action.email_subject}", response_to_action.generated_response)
                if response_to_action.gmail_message_id:
                    mark_email_as_read(service, response_to_action.gmail_message_id)
                response_to_action.status = "approved"
                db.commit()
                db.refresh(response_to_action)
                return {"message": "Response approved and sent successfully", "status": "approved"}
            
            elif action == "reject":
                response_to_action.status = "rejected"
                db.commit()
                db.refresh(response_to_action)
                return {"message": "Response rejected successfully", "status": "rejected"}

        elif action == "regenerate":
            document_content = await file.read() if file else None
            document_filename = file.filename if file else None
            user = db.query(User).filter(User.gmail == original_response.user_email).first()
            user_name = user.name if user else "Support Team"
            service = Email_Summarizer.get_gmail_service()
            conversation_history = []
            if original_response.gmail_thread_id:
                history_messages = Email_Summarizer.get_thread_history(service, original_response.gmail_thread_id)
                conversation_history = [f"From: {msg['from']}\nSnippet: {msg['snippet']}" for msg in history_messages]

            result = process_email_with_orchestration(
                email_data={"subject": original_response.email_subject, "sender": original_response.sender_email, "summary": original_response.email_summary, "intent": original_response.email_intent, "body": "", "snippet": ""},
                user_email=original_response.user_email,
                user_name=user_name,
                user_suggestion=user_suggestion,
                consent_token=original_response.consent_token,
                document_content=document_content,
                document_filename=document_filename,
                conversation_history=conversation_history
            )
            
            new_email_response = EmailResponse(
                user_email=original_response.user_email,
                sender_email=original_response.sender_email,
                email_subject=original_response.email_subject,
                email_summary=original_response.email_summary,
                email_intent=original_response.email_intent,
                generated_response=result.get('message', 'Failed to regenerate.'),
                agent_type=result.get('response_type', 'unknown'),
                status="pending",
                user_suggestion=user_suggestion,
                email_id=original_response.email_id,
                gmail_message_id=original_response.gmail_message_id,
                gmail_thread_id=original_response.gmail_thread_id,
                consent_token=original_response.consent_token
            )
            db.add(new_email_response)
            db.commit()
            db.refresh(new_email_response)
            
            return {"message": "Response regenerated successfully", "generated_response": result, "status": "pending", "response_id": new_email_response.id}
        else:
            raise HTTPException(status_code=400, detail="Invalid action specified")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred while handling the response action: {str(e)}")

@app.get("/api/pending-responses")
async def get_pending_responses(user_email: str, db: Session = Depends(get_db)):
    responses = db.query(EmailResponse).filter(EmailResponse.user_email == user_email, EmailResponse.status == "pending").order_by(EmailResponse.created_at.desc()).all()
    return {"pending_responses": [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in responses]}

@app.get("/api/response-history")
async def get_response_history(user_email: str, db: Session = Depends(get_db)):
    responses = db.query(EmailResponse).filter(EmailResponse.user_email == user_email).order_by(EmailResponse.created_at.desc()).limit(50).all()
    return {"response_history": [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in responses]}
