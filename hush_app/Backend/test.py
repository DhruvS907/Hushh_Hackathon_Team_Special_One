# scheduler_agent_tools.py

from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from langchain.agents import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Sequence
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages


load_dotenv()


# 🔐 Google Calendar API credentials file
SERVICE_ACCOUNT_FILE = 'credentials_calendar.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=creds)

# print(get_calendar_service())

@tool
# ✅ TOOL 1: Get user availability
def check_user_availability(start_time: str, end_time: str, email: str) -> list:
    """
    Fetches the user's busy time slots from their Google Calendar between start_time and end_time.

    Args:
        start_time (str): RFC3339 format, e.g., "2025-07-29T11:00:00+05:30"
        end_time (str): RFC3339 format, e.g., "2025-07-29T14:00:00+05:30"
        email (str): Email ID of the user (e.g., dhruv@example.com)

    Returns:
        list: A list of busy time slots in the form:
              [{"start": "<ISO time>", "end": "<ISO time>"}, ...]
              Returns an empty list if the user is free.
    """
    try:
        service = get_calendar_service()

        body = {
            "timeMin": start_time,
            "timeMax": end_time,
            "timeZone": "Asia/Kolkata",
            "items": [{"id": email}]
        }

        response = service.freebusy().query(body=body).execute()
        busy_slots = response['calendars'][email]['busy']
        return busy_slots 

    except Exception as e:
        return [{"error": f"Error while checking availability: {str(e)}"}]
    
print(check_user_availability(start_time="2025-07-29T11:00:00+05:30", end_time="2025-07-29T14:00:00+05:30", email = "dhruvsaraswat907@gmail.com"))