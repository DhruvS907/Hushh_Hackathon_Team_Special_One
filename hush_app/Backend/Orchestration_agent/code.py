import os
import json
import re
from enum import Enum
from typing import TypedDict, Optional, Union

from dotenv import load_dotenv
from dataclasses import dataclass
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents import info_responder_agent
from agents.schedular_agent import calendar_agent

load_dotenv()

# ──────────────────────────────────────────────────────────────
# ENUMS AND DATACLASSES
# ──────────────────────────────────────────────────────────────
class AgentType(str, Enum):
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

class GraphState(TypedDict):
    email_context: EmailContext
    response: Optional[str]
    agent_type: Optional[AgentType]
    confidence: Optional[float]
    reasoning: Optional[str]
    suggested_action: Optional[str]
    requires_user_input: Optional[bool]
    user_suggestion: Optional[str]

# ──────────────────────────────────────────────────────────────
# SHARED LLM
# ──────────────────────────────────────────────────────────────

llm = ChatOpenAI(
    openai_api_key=os.environ["GROQ_API_KEY"],
    openai_api_base="https://api.groq.com/openai/v1",
    model="qwen/qwen3-32b",
    temperature=0.3,
)

# ──────────────────────────────────────────────────────────────
# ROUTER NODE
# ──────────────────────────────────────────────────────────────

def route_agent(state: GraphState) -> Union[AgentType, str]:
    email = state["email_context"]
    agent_mapping = {
        "Scheduling or rescheduling a meeting or event": AgentType.SCHEDULER,
        "Following up on a previous conversation or task": AgentType.INFO_RESPONDER,
        "Requesting information or clarification": AgentType.INFO_RESPONDER,
        "Providing requested information or sharing details": AgentType.GENERAL_RESPONDER,
        "Requesting approval for a task or document": AgentType.GENERAL_RESPONDER,
        "Declining or cancelling a meeting or request": AgentType.SCHEDULER,
        "Invoices, payments, or billing-related matters": AgentType.GENERAL_RESPONDER,
        "Raising or addressing a support or technical issue": AgentType.INFO_RESPONDER,
        "Marketing emails or newsletters": AgentType.NO_RESPONSE,
        "Informational only – no action required (FYI)": AgentType.NO_RESPONSE,
        "Providing a status update on a project or task": AgentType.GENERAL_RESPONDER,
        "Email that needs a decision or input": AgentType.GENERAL_RESPONDER,
        "Sending or requesting a quote or proposal": AgentType.INFO_RESPONDER,
        "Negotiating a job or business offer": AgentType.GENERAL_RESPONDER,
        "Reporting a bug or product issue": AgentType.INFO_RESPONDER,
        "Requesting a new feature or improvement": AgentType.INFO_RESPONDER,
        "Recruitment or HR-related message": AgentType.GENERAL_RESPONDER,
        "Scheduling or confirming a job interview": AgentType.SCHEDULER,
        "Requesting a referral or recommendation": AgentType.GENERAL_RESPONDER,
        "Operations or compliance-related matter": AgentType.GENERAL_RESPONDER,
        "Legal, policy, or regulatory updates": AgentType.GENERAL_RESPONDER,
        "Announcing a new product or feature": AgentType.NO_RESPONSE,
        "Shipping, delivery, or order tracking update": AgentType.NO_RESPONSE,
        "Invitation to an event or webinar": AgentType.SCHEDULER,
        "Thank you note or congratulatory message": AgentType.GENERAL_RESPONDER,
        "Personal message not related to work": AgentType.GENERAL_RESPONDER
    }

    prompt = f"""
    Analyze this email and determine the best response strategy:
    
    Email Details:
    - Subject: {email.subject}
    - Sender: {email.sender}
    - Intent: {email.intent}
    - Summary: {email.summary}
    - Body Preview: {email.body[:300]}...

    Return JSON in this format:
    {{
        "agent_type": "scheduler|info_responder|general_responder|no_response",
        "confidence": 0.0-1.0,
        "reasoning": "Brief reason",
        "suggested_action": "Action",
        "requires_user_input": true/false
    }}
    """

    result = llm.invoke(prompt)
    try:
        match = re.search(r"{.*}", result.content, re.DOTALL)
        if match:
            analysis = json.loads(match.group())
            state["agent_type"] = AgentType(analysis["agent_type"])
            state["confidence"] = analysis["confidence"]
            state["reasoning"] = analysis["reasoning"]
            state["suggested_action"] = analysis["suggested_action"]
            state["requires_user_input"] = analysis.get("requires_user_input", False)
            return analysis["agent_type"]
    except Exception:
        return agent_mapping.get(email.intent, AgentType.GENERAL_RESPONDER)

    return AgentType.GENERAL_RESPONDER

# ──────────────────────────────────────────────────────────────
# AGENT HANDLERS
# ──────────────────────────────────────────────────────────────
def scheduler_node(state: GraphState) -> GraphState:
    msg = f"""
    Email from {state['email_context'].sender}:
    Subject: {state['email_context'].subject}
    Summary: {state['email_context'].summary}
    Content: {state['email_context'].body}
    
    {f"User suggestion: {state.get('user_suggestion')}" if state.get("user_suggestion") else ""}
    """

    result = calendar_agent.invoke({
        "messages": [HumanMessage(content=msg)],
        "senders_email_address": extract_email(state["email_context"].sender),
        "users_email_address": os.environ["USER_EMAIL"]
    })

    final_message = result['messages'][-1]
    state["response"] = final_message.content if hasattr(final_message, 'content') else "Calendar action done"
    return state

def info_node(state: GraphState) -> GraphState:
    query = f"""{state['email_context'].summary}\n\nOriginal email: {state['email_context'].body}"""
    if state.get("user_suggestion"):
        query += f"\n\nUser guidance: {state['user_suggestion']}"

    result = info_responder_agent(query)
    state["response"] = f"""Dear {state['email_context'].sender.split('<')[0].strip()},

Thank you for your email regarding "{state['email_context'].subject}".

{result}

Best regards,
[Your Name]"""
    return state

def general_node(state: GraphState) -> GraphState:
    prompt = f"""
    Respond to the following email professionally:

    From: {state['email_context'].sender}
    Subject: {state['email_context'].subject}
    Summary: {state['email_context'].summary}
    Intent: {state['email_context'].intent}
    Context: {state['email_context'].body[:500]}

    {f"User guidance: {state['user_suggestion']}" if state.get("user_suggestion") else ""}
    """
    result = llm.invoke(prompt)
    state["response"] = result.content.strip()
    return state

def no_response_node(state: GraphState) -> GraphState:
    state["response"] = "This email doesn't require a response."
    return state

# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────
def extract_email(sender: str) -> str:
    match = re.search(r'<([^>]+)>', sender)
    return match.group(1) if match else sender.strip()

# ──────────────────────────────────────────────────────────────
# GRAPH CONSTRUCTION
# ──────────────────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("router", route_agent)
    graph.add_node("scheduler", scheduler_node)
    graph.add_node("info", info_node)
    graph.add_node("general", general_node)
    graph.add_node("no_response", no_response_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        lambda state: state["agent_type"],
        {
            AgentType.SCHEDULER: "scheduler",
            AgentType.INFO_RESPONDER: "info",
            AgentType.GENERAL_RESPONDER: "general",
            AgentType.NO_RESPONSE: "no_response",
        },
    )

    graph.add_edge("scheduler", END)
    graph.add_edge("info", END)
    graph.add_edge("general", END)
    graph.add_edge("no_response", END)

    return graph.compile()

# ──────────────────────────────────────────────────────────────
# ENTRY FUNCTION
# ──────────────────────────────────────────────────────────────
def process_email(email_data: dict, user_suggestion: Optional[str] = None) -> dict:
    email_context = EmailContext(
        subject=email_data.get('subject', ''),
        sender=email_data.get('sender', ''),
        sender_email=email_data.get('sender', ''),
        body=email_data.get('body', ''),
        summary=email_data.get('summary', ''),
        intent=email_data.get('intent', ''),
        snippet=email_data.get('snippet', '')
    )
    graph = build_graph()
    result = graph.invoke({
        "email_context": email_context,
        "user_suggestion": user_suggestion
    })
    return {
        "response": result["response"],
        "agent_type": result["agent_type"],
        "confidence": result["confidence"],
        "reasoning": result["reasoning"],
        "suggested_action": result["suggested_action"]
    }


sample_email = {
    'subject': 'Meeting Request for Tomorrow',
    'sender': 'John Doe <john.doe@example.com>',
    'body': 'Hi, I would like to schedule a meeting with you tomorrow at 2 PM to discuss the project.',
    'summary': 'John wants to schedule a meeting tomorrow at 2 PM to discuss a project.',
    'intent': 'Scheduling or rescheduling a meeting or event',
    'snippet': 'Meeting request for project discussion'
}

result = process_email(sample_email)
print(result)
