import os
import sys
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Annotated, Sequence, Any
from enum import Enum
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import TypedDict
from dotenv import load_dotenv

# --- Corrected Path Setup ---
# Add the project's root directory (three levels up) to the path
# This allows Python to find the 'hushh_mcp' directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.append(project_root)

# Add the 'Backend' directory (one level up) to the path
# This allows Python to find the 'agents' directory
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(backend_root)


# --- RAG Imports ---
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever

# --- Local & Library Imports (Now correctly located) ---
from agents.info_responder_agent import info_responder_agent
from agents.schedular_agent import calendar_agent
from hushh_mcp.consent.token import validate_token
from hushh_mcp.constants import ConsentScope

load_dotenv()


# --- Enums and Dataclasses ---
class AgentType(Enum):
    SCHEDULER = "scheduler"
    INFO_RESPONDER = "info_responder"
    GENERAL_RESPONDER = "general_responder"
    NO_RESPONSE = "no_response"

@dataclass
class EmailContext:
    subject: str
    sender: str
    sender_email: str
    body: str
    summary: str
    intent: str
    snippet: str

@dataclass
class ResponsePlan:
    agent_type: AgentType
    confidence: float
    reasoning: str
    suggested_action: str
    requires_user_input: bool = False

# --- LangGraph State ---
class EmailState(TypedDict):
    """State for the email orchestration workflow"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    email_context: EmailContext
    user_email: str
    user_name: str
    user_suggestion: Optional[str]
    document_content: Optional[bytes]
    document_filename: Optional[str]
    history_retriever: Optional[VectorStoreRetriever]
    response_plan: Optional[ResponsePlan]
    agent_outcome: Optional[str]
    final_response: Optional[str]
    error: Optional[str]

# --- Main Orchestration Agent ---
class OrchestrationAgent:
    def __init__(self, user_name: str, user_email: str):
        self.user_email = user_email
        self.user_name = user_name
        self.llm = ChatOpenAI(
            openai_api_key=os.environ["GROQ_API_KEY"],
            openai_api_base="https://api.groq.com/openai/v1",
            model="qwen/qwen3-32b",
            temperature=0.3,
        )
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.environ.get("GOOGLE_API_KEY")
        )
        self.intent_mapping = {
            "Scheduling or rescheduling a meeting or event": AgentType.SCHEDULER,
            "Requesting information or clarification": AgentType.INFO_RESPONDER,
            "Marketing emails or newsletters": AgentType.NO_RESPONSE,
            "Informational only – no action required (FYI)": AgentType.NO_RESPONSE,
            "Announcing a new product or feature": AgentType.NO_RESPONSE,
            "Shipping, delivery, or order tracking update": AgentType.NO_RESPONSE,
        }
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Builds the LangGraph state machine with a separate composition step."""
        workflow = StateGraph(EmailState)
        workflow.add_node("analyzer", self._analyze_email_node)
        workflow.add_node("scheduler_agent", self._scheduler_agent_node)
        workflow.add_node("info_agent", self._info_agent_node)
        workflow.add_node("general_agent", self._general_agent_node)
        workflow.add_node("no_response", self._no_response_node)
        workflow.add_node("composer", self._compose_final_email_node)

        workflow.add_edge(START, "analyzer")
        workflow.add_conditional_edges(
            "analyzer",
            self._route_to_agent,
            {
                "scheduler": "scheduler_agent",
                "info_responder": "info_agent",
                "general_responder": "general_agent",
                "no_response": "no_response"
            }
        )
        workflow.add_edge("scheduler_agent", "composer")
        workflow.add_edge("info_agent", "composer")
        workflow.add_edge("general_agent", "composer")
        workflow.add_edge("no_response", END)
        workflow.add_edge("composer", END)

        return workflow.compile()

    # --- Node Implementations ---
    def _analyze_email_node(self, state: EmailState) -> EmailState:
        """Analyzes email to determine the correct agent route."""
        email_context = state["email_context"]
        initial_agent = self.intent_mapping.get(email_context.intent, AgentType.GENERAL_RESPONDER)
        
        analysis_prompt = f"""
        Analyze this email and determine the best response strategy.
        Email Details:
        - Subject: {email_context.subject}
        - Sender: {email_context.sender}
        - Intent: {email_context.intent}
        - Summary: {email_context.summary}
        Available Agents: SCHEDULER, INFO_RESPONDER, GENERAL_RESPONDER, NO_RESPONSE.
        Return only valid JSON:
        {{
            "agent_type": "scheduler|info_responder|general_responder|no_response",
            "confidence": 0.0-1.0,
            "reasoning": "Brief explanation of why this agent is chosen",
            "suggested_action": "What specific action should be taken"
        }}
        """
        try:
            response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
            analysis = self._extract_json(response.content)
            response_plan = ResponsePlan(
                agent_type=AgentType(analysis["agent_type"]),
                confidence=analysis["confidence"],
                reasoning=analysis["reasoning"],
                suggested_action=analysis["suggested_action"]
            )
        except Exception as e:
            print(f"LLM analysis failed: {e}, falling back to intent mapping.")
            response_plan = ResponsePlan(
                agent_type=initial_agent,
                confidence=0.7,
                reasoning=f"Fallback based on intent: {email_context.intent}",
                suggested_action="Handle using the mapped agent"
            )
        
        analysis_msg = AIMessage(content=f"Analyzed email. Route to: {response_plan.agent_type.value}")
        return {**state, "messages": state["messages"] + [analysis_msg], "response_plan": response_plan}

    def _route_to_agent(self, state: EmailState) -> str:
        """Routes to the appropriate agent based on analysis."""
        return state["response_plan"].agent_type.value if state["response_plan"] else "general_responder"

    def _scheduler_agent_node(self, state: EmailState) -> EmailState:
        """Node for handling scheduling. Just gets the raw output from the calendar agent."""
        email_context = state["email_context"]
        user_suggestion = state.get("user_suggestion")
        try:
            sender_email = self._extract_email_from_sender(email_context.sender)
            message_content = f"Email from {email_context.sender}:\n{email_context.body}\n{f'User suggestion: {user_suggestion}' if user_suggestion else ''}"
            initial_state = {'messages': [HumanMessage(content=message_content)], 'senders_email_address': sender_email, 'users_email_address': state["user_email"]}
            result = calendar_agent.invoke(initial_state)
            agent_outcome = result['messages'][-1].content
        except Exception as e:
            agent_outcome = f"Error in scheduler: {str(e)}"
        
        return {**state, "agent_outcome": agent_outcome}

    def _info_agent_node(self, state: EmailState) -> EmailState:
        """Node for handling information requests. Just gets the raw output from the info agent."""
        email_context = state["email_context"]
        user_suggestion = state.get("user_suggestion")
        document_content = state.get("document_content")
        document_filename = state.get("document_filename")
        
        query = f"{email_context.summary}\n\n{f'User guidance: {user_suggestion}' if user_suggestion else ''}"
        
        try:
            agent_outcome = info_responder_agent(
                query=query,
                doc_content=document_content,
                doc_filename=document_filename
            )
        except Exception as e:
            agent_outcome = f"Error processing info request: {str(e)}"
        
        return {**state, "agent_outcome": agent_outcome}

    def _general_agent_node(self, state: EmailState) -> EmailState:
        """Node for general communication. Generates a draft response to be used by the composer."""
        email_context = state["email_context"]
        user_suggestion = state.get("user_suggestion")
        
        recipient_name = email_context.sender.split('<')[0].strip()
        if '@' in recipient_name:
            recipient_name = "there"

        response_prompt = f"""
You are an AI assistant writing an email on behalf of {self.user_name}.
Write a professional response to the email below.

**Instructions:**
1. Address the email to '{recipient_name}'. Start with a polite greeting.
2. Sign the email with the name '{self.user_name}'.

**Original Email:**
- From: {email_context.sender}
- Body: {email_context.body[:500]}

**User guidance:** {user_suggestion if user_suggestion else "N/A"}

Write the email response now.
"""
        try:
            response = self.llm.invoke([HumanMessage(content=response_prompt)])
            agent_outcome = self._strip_think_block(response.content)
        except Exception as e:
            agent_outcome = f"Error generating response: {str(e)}"
        
        return {**state, "agent_outcome": agent_outcome}

    def _no_response_node(self, state: EmailState) -> EmailState:
        """Node for emails that don't require a response."""
        return {**state, "final_response": "This email doesn't require a response."}

    def _compose_final_email_node(self, state: EmailState) -> EmailState:
        """Takes the output from a specialist agent and composes the final email."""
        agent_outcome = state.get("agent_outcome", "No information was generated.")
        email_context = state["email_context"]

        # --- FIX: Extract recipient's name for a personalized greeting ---
        recipient_name = email_context.sender.split('<')[0].strip()
        # Fallback for cases where the name is just an email address
        if '@' in recipient_name:
            recipient_name = "there"

        response_prompt = f"""
You are an AI assistant writing a professional email on behalf of {self.user_name}.

Your task is to compose a final email response.
Use the "Contextual Information" below, which was generated by a specialist agent, to formulate your answer.
Integrate this information naturally into a polite and helpful email.

**Contextual Information to Use for the Reply:**
---
{agent_outcome}
---

**Original Email Details:**
- From: {email_context.sender}
- Subject: {email_context.subject}

**Instructions:**
1. **Address the email to '{recipient_name}'.** Start with a polite greeting like "Dear {recipient_name}," or "Hi {recipient_name},".
2. Write a complete and professional email response based on the contextual information.
3. **Sign the email with the name '{self.user_name}'.**

Write the final email response now.
GIVE YOUR RESPONSE ONLY THE BODY OF THE EMAIL AND NOTHING ELSE
"""
        response = self.llm.invoke([HumanMessage(content=response_prompt)])
        final_response = self._strip_think_block(response.content)
        
        return {**state, "final_response": final_response}

    # --- Helper and Public Methods ---
    def _strip_think_block(self, text: str) -> str:
        """Removes a <think>...</think> block from the beginning of a string."""
        return re.sub(r"^<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    def _create_history_retriever(self, history: Optional[List[str]]) -> Optional[VectorStoreRetriever]:
        if not history: return None
        documents = [Document(page_content=msg) for msg in history]
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        splits = text_splitter.split_documents(documents)
        vector = FAISS.from_documents(splits, self.embeddings)
        return vector.as_retriever()

    def generate_response(self, email_context: EmailContext, consent_token: str, user_suggestion: Optional[str] = None, document_content: Optional[bytes] = None, document_filename: Optional[str] = None, conversation_history: Optional[List[str]] = None) -> Dict:
        # 1. Validate the token and scope
        is_valid, reason, parsed_token = validate_token(consent_token, expected_scope=ConsentScope.VAULT_READ_EMAIL)
        if not is_valid:
            raise PermissionError(f"Consent validation failed: {reason}")
        if parsed_token.user_id != self.user_email:
            raise PermissionError("User ID in token does not match")

        # 2. If valid, proceed with the existing logic
        history_retriever = self._create_history_retriever(conversation_history)
        initial_state = {
            "messages": [HumanMessage(content=f"Processing email: {email_context.subject}")],
            "email_context": email_context,
            "user_email": self.user_email,
            "user_name": self.user_name,
            "user_suggestion": user_suggestion,
            "document_content": document_content,
            "document_filename": document_filename,
            "history_retriever": history_retriever,
        }
        try:
            final_state = self.workflow.invoke(initial_state)
            response_plan = final_state.get("response_plan")
            final_response = final_state.get("final_response", "No response generated")
            
            agent_type = response_plan.agent_type.value if response_plan else "general_responder"
            if agent_type == "no_response":
                return {"response_type": "no_response", "message": final_response, "reasoning": "N/A", "confidence": 1.0}

            return {
                "response_type": agent_type,
                "message": final_response,
                "reasoning": response_plan.reasoning if response_plan else "Default processing",
                "confidence": response_plan.confidence if response_plan else 0.7,
            }
        except Exception as e:
            return {"response_type": "error", "message": f"Error: {str(e)}", "reasoning": "System error", "confidence": 0.0}

    def _extract_email_from_sender(self, sender: str) -> str:
        email_match = re.search(r'<([^>]+)>', sender)
        return email_match.group(1) if email_match else sender.strip()

    def _extract_json(self, response_text: str) -> Optional[Dict]:
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            try: return json.loads(match.group())
            except json.JSONDecodeError: return None
        return None

# --- Main Entrypoint Function ---
def process_email_with_orchestration(email_data: Dict, user_email: str, user_name: str, consent_token: str, user_suggestion: Optional[str] = None, document_content: Optional[bytes] = None, document_filename: Optional[str] = None, conversation_history: Optional[List[str]] = None) -> Dict:
    email_context = EmailContext(
        subject=email_data.get('subject', ''),
        sender=email_data.get('sender', ''),
        sender_email=email_data.get('sender', ''),
        body=email_data.get('body', ''),
        summary=email_data.get('summary', ''),
        intent=email_data.get('intent', ''),
        snippet=email_data.get('snippet', '')
    )
    orchestrator = OrchestrationAgent(user_name, user_email)
    return orchestrator.generate_response(email_context, consent_token, user_suggestion, document_content, document_filename, conversation_history)