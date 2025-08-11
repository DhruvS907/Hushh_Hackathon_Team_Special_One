# scheduler_agent_tools_oauth2.py

from datetime import datetime, timedelta
import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain.agents import tool
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Sequence
from langgraph.graph.message import add_messages
import pytz

load_dotenv()

# 🔐 Google Calendar API OAuth2 setup
SCOPES = ['https://www.googleapis.com/auth/calendar']

def setup_oauth2_credentials():
    """Set up OAuth2 credentials for Google Calendar API"""
    creds = None
    
    # The file token.pickle stores the user's access and refresh tokens.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials_calendar.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def get_calendar_service():
    """Get Google Calendar service using OAuth2 credentials"""
    creds = setup_oauth2_credentials()
    return build('calendar', 'v3', credentials=creds)

def get_tomorrow_date():
    """Get tomorrow's date in YYYY-MM-DD format"""
    tomorrow = datetime.now() + timedelta(days=1)
    return tomorrow.strftime('%Y-%m-%d')

# ✅ TOOL 1: Get user availability
@tool
def check_user_availability(start_time: str, end_time: str, email: str) -> list:
    """
    Fetches the user's busy time slots from their Google Calendar between start_time and end_time.

    Args:
        start_time (str): RFC3339 format, e.g., "2025-07-30T17:00:00+05:30"
        end_time (str): RFC3339 format, e.g., "2025-07-30T18:00:00+05:30"
        email (str): Email ID of the user (e.g., dhruv@example.com)

    Returns:
        list: A list of busy time slots in the form:
              [{"start": "<ISO time>", "end": "<ISO time>"}]
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
        return busy_slots  # Empty list → fully available
    except Exception as e:
        return [{"error": f"Error while checking availability: {str(e)}"}]

# ✅ TOOL 2: Propose time slots
@tool
def propose_time_slots_tool(busy_times: list, working_hours: tuple = (9, 18)) -> list:
    """
    Suggests up to 3 available 1-hour time slots within working hours over the next 7 days, avoiding conflicts
    with already scheduled busy times.

    Args:
        busy_times (list): A list of dictionaries representing the user's busy time ranges.
                           Example: [{"start": "2025-07-29T10:00:00+05:30", "end": "2025-07-29T11:00:00+05:30"}]
        working_hours (tuple, optional): Tuple of integers representing working hours (24-hr format).
                                         Defaults to (9, 18), meaning from 9 AM to 6 PM.

    Returns:
        list: A list of up to 3 available time slots (tuples of ISO 8601 start and end time).
              Example: [("2025-07-30T09:00:00+05:30", "2025-07-30T10:00:00+05:30")]

    Use this tool when you want to propose free slots for scheduling a new meeting.
    """
    available_slots = []
    current_time = datetime.now()
    days_checked = 0
    ist = pytz.timezone('Asia/Kolkata')

    while len(available_slots) < 3 and days_checked < 7:
        date = current_time.date() + timedelta(days=days_checked)
        for hour in range(working_hours[0], working_hours[1]):
            # Create timezone-aware datetime
            slot_start = ist.localize(datetime(date.year, date.month, date.day, hour))
            slot_end = slot_start + timedelta(hours=1)

            is_busy = any(
                slot_start.isoformat() < busy['end'] and slot_end.isoformat() > busy['start']
                for busy in busy_times
            )

            if not is_busy:
                available_slots.append((slot_start.isoformat(), slot_end.isoformat()))
            if len(available_slots) == 3:
                break
        days_checked += 1

    return available_slots

# ✅ TOOL 3: Schedule meeting
@tool
def schedule_meeting_on_calendar_tool(summary: str, start_time: str, end_time: str, attendees: list, description: str = "") -> str:
    """
    Schedules a meeting in the user's Google Calendar and sends invites to the listed attendees.

    Args:
        summary (str): The title or subject of the meeting.
        start_time (str): Start time of the meeting in ISO 8601 format.
        end_time (str): End time of the meeting in ISO 8601 format.
        attendees (list): List of email addresses to be invited to the meeting.
                          Example: ["john@example.com", "jane@example.com"]
        description (str, optional): Additional description or agenda for the meeting.

    Returns:
        str: A URL to the scheduled meeting (Google Calendar event link).

    Use this tool to confirm a finalized time and send invitations to attendees.
    """
    try:
        service = get_calendar_service()
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Asia/Kolkata',
            },
            'attendees': [{'email': email} for email in attendees],
            'reminders': {
                'useDefault': True,
            },
        }
        event = service.events().insert(calendarId='primary', body=event, sendUpdates='all').execute()
        return event.get('htmlLink')
    except Exception as e:
        return f"Error scheduling meeting: {str(e)}"

# ✅ TOOL 4: Listing the upcoming events
@tool
def list_upcoming_events_tool(max_results: int = 10) -> list:
    """
    Lists the user's upcoming scheduled events from Google Calendar.

    Args:
        max_results (int, optional): Maximum number of events to return. Defaults to 10.

    Returns:
        list: A list of upcoming events, where each event is a dictionary containing:
              - "id": Unique event ID.
              - "summary": Title of the event.
              - "start": Start time of the event in ISO 8601 format.
              - "end": End time of the event in ISO 8601 format.

    Use this tool to review upcoming meetings or pick one to reschedule or cancel.
    """
    try:
        service = get_calendar_service()
        now = datetime.now().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime').execute()
        
        return [
            {
                "id": event['id'],
                "summary": event.get('summary', ''),
                "start": event['start'].get('dateTime', ''),
                "end": event['end'].get('dateTime', '')
            }
            for event in events_result.get('items', [])
        ]
    except Exception as e:
        return [{"error": f"Error listing events: {str(e)}"}]

# ✅ TOOL 5: Reschedule event
@tool
def reschedule_event_tool(event_id: str, new_start_time: str, new_end_time: str) -> str:
    """
    Reschedules an existing event on the user's Google Calendar to a new time slot.

    Args:
        event_id (str): The unique identifier of the event to be updated.
        new_start_time (str): New start time in ISO 8601 format.
        new_end_time (str): New end time in ISO 8601 format.

    Returns:
        str: Updated meeting URL (Google Calendar link).

    Use this tool when the user wants to move an existing meeting to a different time.
    """
    try:
        service = get_calendar_service()
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        event['start']['dateTime'] = new_start_time
        event['end']['dateTime'] = new_end_time
        updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        return updated_event.get('htmlLink')
    except Exception as e:
        return f"Error rescheduling event: {str(e)}"

# ✅ TOOL 6: Cancel event
@tool
def cancel_event_tool(event_id: str) -> str:
    """
    Cancels a scheduled meeting on the user's Google Calendar using its event ID.

    Args:
        event_id (str): The unique identifier of the event to be deleted.

    Returns:
        str: A confirmation message indicating successful cancellation.

    Use this tool when the user no longer wishes to attend or host a scheduled event.
    """
    try:
        service = get_calendar_service()
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return "Event canceled successfully."
    except Exception as e:
        return f"Error canceling event: {str(e)}"

# Tool list to register in LangChain agent
tool_list = [
    check_user_availability,
    propose_time_slots_tool,
    schedule_meeting_on_calendar_tool,
    list_upcoming_events_tool,
    reschedule_event_tool,
    cancel_event_tool
]

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    senders_email_address: str
    users_email_address: str

def agent(state: AgentState) -> AgentState:
    tomorrow_date = get_tomorrow_date()
    
    # CHANGE: Added instructions for handling user suggestions to reschedule.
    system_message = f"""You are a scheduling assistant. Your job is to help the signed-in user manage their meeting requests based on their calendar availability.

Current date: {datetime.now().strftime('%Y-%m-%d')}
Tomorrow's date: {tomorrow_date}

Sender's email address: {state['senders_email_address']}
User's email address: {state['users_email_address']}

You are only concerned with the availability of the signed-in user, whose Gmail ID is {state['users_email_address']}. Do not attempt to check or reason about the sender's availability — assume they are free at the time they suggest.

When someone mentions "tomorrow", use the date {tomorrow_date}.
When checking availability, use the proper date format: {tomorrow_date}T17:00:00+05:30 for 5 PM IST.

If the user provides a suggestion to change the meeting time, you must first find the existing event and cancel it before scheduling the new one.
If the sender proposes a time slot:
1. Check if the signed-in user is available during that time using check_user_availability
2. If available → proceed to create a calendar event using schedule_meeting_on_calendar_tool
3. If not available → use propose_time_slots_tool to suggest alternate times

Always use the user's email ({state['users_email_address']}) for all calendar operations.
"""
    
    llm = ChatOpenAI(
        openai_api_key=os.environ["GROQ_API_KEY"],
        openai_api_base="https://api.groq.com/openai/v1",
        model="qwen/qwen3-32b",
        temperature=0.2,
    ).bind_tools(tool_list)

    recent_messages = state["messages"][-5:] if len(state["messages"]) > 5 else state["messages"]
    response = llm.invoke([SystemMessage(content=system_message)] + recent_messages)
    updated_history = state["messages"] + [response]
    
    return {**state, "messages": updated_history}

def should_continue(state: AgentState) -> str:
    """Determine whether to continue or end based on the last message"""
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return "end"

# Custom tool node to handle empty responses
def custom_tool_node(state: AgentState) -> AgentState:
    """Custom tool node that ensures tool messages have proper content"""
    last_message = state["messages"][-1]
    tool_messages = []
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            try:
                # Find the tool and execute it
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_id = tool_call['id']
                
                # Execute the appropriate tool
                result = None
                for tool in tool_list:
                    if tool.name == tool_name:
                        result = tool.invoke(tool_args)
                        break
                
                # Ensure result is a string
                if result is None:
                    result_str = f"Tool {tool_name} executed but returned no result"
                elif isinstance(result, list):
                    if len(result) == 0:
                        result_str = f"No conflicts found - user is available during requested time"
                    else:
                        result_str = str(result)
                else:
                    result_str = str(result)
                
                tool_message = ToolMessage(
                    content=result_str,
                    tool_call_id=tool_id,
                    name=tool_name
                )
                tool_messages.append(tool_message)
                
            except Exception as e:
                error_message = ToolMessage(
                    content=f"Error executing {tool_call['name']}: {str(e)}",
                    tool_call_id=tool_call['id'],
                    name=tool_call['name']
                )
                tool_messages.append(error_message)
    
    return {**state, "messages": state["messages"] + tool_messages}

# Create the graph with proper flow
graph = StateGraph(AgentState)
graph.add_node("agent", agent)
graph.add_node("tools", custom_tool_node)

# Set up the flow
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
graph.add_edge("tools", "agent")  # Return to agent after tool execution

calendar_agent = graph.compile()

# if __name__ == "__main__":
#     # Use current date for testing
#     tomorrow_date = get_tomorrow_date()
    
#     initial_state = {
#         'messages': [
#             HumanMessage(content="Hi there John this side, Want you to schedule a meet tomorrow at 5pm to 6pm. If you are busy then propose some other times if possible else we can schedule the meet at the required time")
#         ], 
#         'senders_email_address': 'dhruvsaraswat642@gmail.com', 
#         'users_email_address': 'dhruvsaraswat907@gmail.com'
#     }

#     print("Starting calendar agent...")
#     try:
#         result = calendar_agent.invoke(initial_state)
        
#         # Print the final response
#         final_message = result['messages'][-1]
#         if hasattr(final_message, 'content'):
#             print("\nFinal Response:")
#             print(final_message.content)
#     except Exception as e:
#         print(f"Error: {e}")
#         print("\nMake sure you have:")
#         print("1. Downloaded credentials.json from Google Cloud Console")
#         print("2. Enabled Google Calendar API")
#         print("3. Run the OAuth2 setup first")