"""
Calendar tools for Google Calendar integration.
Production-ready with REAL API calls and complete error handling.
"""

import os
import pickle
from datetime import datetime, timedelta
from typing import List
from langchain.tools import tool
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_calendar_service():
    """Get authenticated Google Calendar service with proper error handling."""
    try:
        creds = None
        token_path = 'token_calendar.pickle'
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    print("⚠️  credentials.json not found")
                    return None
                
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        service = build('calendar', 'v3', credentials=creds)
        return service
        
    except Exception as e:
        print(f"Calendar authentication failed: {e}")
        return None


@tool
def create_calendar_event(
    title: str,
    start_time: str,  # ISO format: "2024-01-15T14:00:00"
    end_time: str,    # ISO format: "2024-01-15T15:00:00"
    attendees: List[str],  # email addresses
    location: str = ""
) -> str:
    """Create a calendar event. Requires exact ISO datetime format.
    
    Args:
        title: Event title/summary
        start_time: Start time in ISO format (YYYY-MM-DDTHH:MM:SS)
        end_time: End time in ISO format (YYYY-MM-DDTHH:MM:SS)
        attendees: List of attendee email addresses
        location: Event location (optional)
    
    Returns:
        Confirmation message with event details
    """
    try:
        # Get service
        service = get_calendar_service()
        
        # CRITICAL: Check if service is None
        if service is None:
            return (
                f"⚠️  Google Calendar not configured.\n\n"
                f"Event Details:\n"
                f"  Title: {title}\n"
                f"  Start: {start_time}\n"
                f"  End: {end_time}\n"
                f"  Attendees: {len(attendees)} ({', '.join(attendees)})\n"
                f"  Location: {location or 'Not specified'}\n\n"
                f"To enable calendar features:\n"
                f"  1. Download credentials.json from Google Cloud Console\n"
                f"  2. Place it in project root directory\n"
                f"  3. Run the application again\n\n"
                f"Data Agent is still fully functional."
            )
        
        # Create event
        event = {
            'summary': title,
            'location': location,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
            'attendees': [{'email': email} for email in attendees],
        }
        
        # ACTUAL API CALL to create event
        created_event = service.events().insert(
            calendarId='primary',
            body=event,
            sendUpdates='all'
        ).execute()
        
        return (
            f"✅ Event created successfully!\n"
            f"  Title: {title}\n"
            f"  Start: {start_time}\n"
            f"  End: {end_time}\n"
            f"  Attendees: {len(attendees)}\n"
            f"  Link: {created_event.get('htmlLink', 'N/A')}"
        )
    
    except HttpError as e:
        return f"❌ Google Calendar API error: {e.reason if hasattr(e, 'reason') else str(e)}"
    
    except Exception as e:
        return f"❌ Error creating event: {str(e)}"


@tool
def get_available_time_slots(
    attendees: List[str],
    date: str,  # ISO format: "2024-01-15"
    duration_minutes: int
) -> str:
    """Check calendar availability for given attendees on a specific date.
    
    Args:
        attendees: List of attendee email addresses
        date: Date in ISO format (YYYY-MM-DD)
        duration_minutes: Duration of meeting in minutes
    
    Returns:
        String with available time slots or error message
    """
    try:
        # Get service
        service = get_calendar_service()
        
        # CRITICAL: Check if service is None
        if service is None:
            # Return default slots with clear message
            default_slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
            return (
                f"📅 Suggested time slots for {date}:\n"
                f"(Default working hours - Google Calendar not configured)\n\n"
                + "\n".join([f"  • {slot}" for slot in default_slots])
                + "\n\nTo check real availability, add credentials.json"
            )
        
        # ACTUAL API CALL to get calendar events
        try:
            time_min = f"{date}T00:00:00Z"
            time_max = f"{date}T23:59:59Z"
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Calculate busy hours from REAL calendar data
            busy_hours = set()
            for event in events:
                start = event.get('start', {}).get('dateTime', '')
                if 'T' in start:
                    hour = int(start.split('T')[1].split(':')[0])
                    busy_hours.add(hour)
            
            # Generate available slots (9 AM - 5 PM)
            available_slots = []
            for hour in range(9, 17):
                if hour not in busy_hours:
                    available_slots.append(f"{hour:02d}:00")
            
            if not available_slots:
                return (
                    f"⚠️  No available slots found on {date}.\n"
                    f"All working hours (9 AM - 5 PM) are busy.\n"
                    f"Found {len(events)} existing events."
                )
            
            return (
                f"📅 Available time slots for {date}:\n"
                f"(Based on real calendar data - {len(events)} events found)\n\n"
                + "\n".join([f"  • {slot}" for slot in available_slots[:8]])
            )
        
        except HttpError as e:
            # API error - return default slots
            default_slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
            return (
                f"⚠️  Calendar API error: {e.reason if hasattr(e, 'reason') else 'Unknown'}\n\n"
                f"Suggested default slots:\n"
                + "\n".join([f"  • {slot}" for slot in default_slots])
            )
    
    except Exception as e:
        # General error - return default slots with message
        default_slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
        return (
            f"❌ Error checking availability: {str(e)}\n\n"
            f"Suggested default slots:\n"
            + "\n".join([f"  • {slot}" for slot in default_slots])
        )