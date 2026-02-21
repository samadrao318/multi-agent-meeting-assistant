"""
Email tools for Gmail integration.
Production-ready with REAL API calls and complete error handling.
"""

import os
import pickle
import base64
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from langchain.tools import tool
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]


def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email.strip()) is not None


def get_gmail_service():
    """Get authenticated Gmail service with proper error handling."""
    try:
        creds = None
        token_path = 'token_gmail.pickle'
        
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
        
        service = build('gmail', 'v1', credentials=creds)
        return service
        
    except Exception as e:
        print(f"Gmail authentication failed: {e}")
        return None


@tool
def send_email(
    to: List[str],  # email addresses
    subject: str,
    body: str,
    cc: List[str] = []
) -> str:
    """Send an email via Gmail API. Requires properly formatted addresses.
    
    Args:
        to: List of recipient email addresses
        subject: Email subject line
        body: Email body content
        cc: List of CC email addresses (optional)
    
    Returns:
        Confirmation message with email details
    """
    try:
        # Input validation
        if not to or len(to) == 0:
            return "❌ Error: At least one recipient is required"
        
        if not subject or not subject.strip():
            return "❌ Error: Email subject is required"
        
        if not body or not body.strip():
            return "❌ Error: Email body is required"
        
        # Validate email addresses
        invalid_emails = []
        for email in to + cc:
            if not validate_email(email):
                invalid_emails.append(email)
        
        if invalid_emails:
            return f"❌ Error: Invalid email addresses: {', '.join(invalid_emails)}"
        
        # Get service
        service = get_gmail_service()
        
        # CRITICAL: Check if service is None
        if service is None:
            return (
                f"⚠️  Gmail not configured.\n\n"
                f"Email Details:\n"
                f"  To: {', '.join(to)}\n"
                f"  CC: {', '.join(cc) if cc else 'None'}\n"
                f"  Subject: {subject}\n"
                f"  Body: {body[:100]}{'...' if len(body) > 100 else ''}\n\n"
                f"To enable email features:\n"
                f"  1. Download credentials.json from Google Cloud Console\n"
                f"  2. Enable Gmail API in your project\n"
                f"  3. Place credentials.json in project root\n"
                f"  4. Run the application again\n\n"
                f"Data Agent is still fully functional."
            )
        
        # Create message
        message = MIMEMultipart()
        message['to'] = ', '.join([email.strip() for email in to])
        message['subject'] = subject.strip()
        
        if cc:
            message['cc'] = ', '.join([email.strip() for email in cc])
        
        # Add body
        message.attach(MIMEText(body, 'plain'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # ACTUAL API CALL to send email
        try:
            sent_message = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            message_id = sent_message.get('id', 'N/A')
            thread_id = sent_message.get('threadId', 'N/A')
            
            return (
                f"✅ Email sent successfully!\n"
                f"  To: {', '.join(to)}\n"
                f"  CC: {', '.join(cc) if cc else 'None'}\n"
                f"  Subject: {subject}\n"
                f"  Message ID: {message_id}\n"
                f"  Thread ID: {thread_id}\n"
                f"  Body length: {len(body)} characters\n\n"
                f"Recipients will receive the email shortly."
            )
        
        except HttpError as e:
            error_details = e.reason if hasattr(e, 'reason') else str(e)
            return f"❌ Gmail API error: {error_details}"
    
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"


@tool
def read_emails(
    max_results: int = 10,
    query: str = "is:unread"
) -> str:
    """Read emails from Gmail inbox with optional filtering.
    
    Args:
        max_results: Maximum number of emails to retrieve (default: 10)
        query: Gmail search query (default: "is:unread")
               Examples: "from:sender@example.com", "subject:meeting", "is:starred"
    
    Returns:
        String with email list or error message
    """
    try:
        # Get service
        service = get_gmail_service()
        
        # CRITICAL: Check if service is None
        if service is None:
            return (
                "⚠️  Gmail not configured.\n\n"
                "To read emails:\n"
                "  1. Download credentials.json from Google Cloud Console\n"
                "  2. Enable Gmail API\n"
                "  3. Place credentials.json in project root\n\n"
                "Data Agent is still fully functional."
            )
        
        # ACTUAL API CALL to list messages
        try:
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return f"📧 No emails found matching query: '{query}'"
            
            email_list = []
            
            # ACTUAL API CALLS to get message details
            for msg in messages[:max_results]:
                try:
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata',
                        metadataHeaders=['From', 'Subject', 'Date']
                    ).execute()
                    
                    headers = message.get('payload', {}).get('headers', [])
                    
                    from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
                    
                    snippet = message.get('snippet', 'No preview available')
                    
                    email_list.append(
                        f"From: {from_email}\n"
                        f"Subject: {subject}\n"
                        f"Date: {date}\n"
                        f"Preview: {snippet[:100]}...\n"
                    )
                
                except Exception as e:
                    email_list.append(f"Error reading message: {str(e)}\n")
            
            return (
                f"📧 Found {len(messages)} email(s) matching '{query}':\n\n"
                + "\n---\n\n".join(email_list)
            )
        
        except HttpError as e:
            error_details = e.reason if hasattr(e, 'reason') else str(e)
            return f"❌ Gmail API error: {error_details}"
    
    except Exception as e:
        return f"❌ Error reading emails: {str(e)}"