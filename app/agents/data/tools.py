"""
Data tools for CSV file operations.
"""

import os
import pandas as pd
from typing import List, Dict, Optional
from langchain.tools import tool


CSV_FILE_PATH = "data/contacts.csv"


def ensure_csv_exists():
    """Ensure CSV file and directory exist."""
    os.makedirs(os.path.dirname(CSV_FILE_PATH), exist_ok=True)
    
    if not os.path.exists(CSV_FILE_PATH):
        # Create with sample data
        df = pd.DataFrame({
            'email': ['john.doe@example.com', 'jane.smith@example.com'],
            'name': ['John Doe', 'Jane Smith'],
            'designation': ['Software Engineer', 'Product Manager']
        })
        df.to_csv(CSV_FILE_PATH, index=False)


@tool
def read_contacts(
    filter_designation: Optional[str] = None
) -> str:
    """Read contacts from CSV file, optionally filtered by designation.
    
    Args:
        filter_designation: Optional designation to filter by (e.g., 'Engineer', 'Manager')
    
    Returns:
        String representation of contacts
    """
    try:
        ensure_csv_exists()
        df = pd.read_csv(CSV_FILE_PATH)
        
        if filter_designation:
            df = df[df['designation'].str.contains(filter_designation, case=False, na=False)]
        
        if df.empty:
            return "No contacts found matching criteria."
        
        result = f"Found {len(df)} contact(s):\n\n"
        for _, row in df.iterrows():
            result += f"- {row['name']} ({row['email']}) - {row['designation']}\n"
        
        return result
    
    except Exception as e:
        return f"❌ Error reading contacts: {str(e)}"


@tool
def add_contact(
    email: str,
    name: str,
    designation: str
) -> str:
    """Add a new contact to the CSV file.
    
    Args:
        email: Contact email address
        name: Contact full name
        designation: Contact job title/designation
    
    Returns:
        Confirmation message
    """
    try:
        ensure_csv_exists()
        df = pd.read_csv(CSV_FILE_PATH)
        
        # Check if email already exists
        if email in df['email'].values:
            return f"❌ Contact with email {email} already exists."
        
        # Add new contact
        new_row = pd.DataFrame([{
            'email': email,
            'name': name,
            'designation': designation
        }])
        
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(CSV_FILE_PATH, index=False)
        
        return f"✅ Contact added: {name} ({email}) - {designation}"
    
    except Exception as e:
        return f"❌ Error adding contact: {str(e)}"


@tool
def search_contacts(
    query: str
) -> str:
    """Search contacts by name, email, or designation.
    
    Args:
        query: Search term to look for across all fields
    
    Returns:
        String representation of matching contacts
    """
    try:
        ensure_csv_exists()
        df = pd.read_csv(CSV_FILE_PATH)
        
        # Search across all columns
        mask = (
            df['name'].str.contains(query, case=False, na=False) |
            df['email'].str.contains(query, case=False, na=False) |
            df['designation'].str.contains(query, case=False, na=False)
        )
        
        df = df[mask]
        
        if df.empty:
            return f"No contacts found matching '{query}'."
        
        result = f"Found {len(df)} contact(s) matching '{query}':\n\n"
        for _, row in df.iterrows():
            result += f"- {row['name']} ({row['email']}) - {row['designation']}\n"
        
        return result
    
    except Exception as e:
        return f"❌ Error searching contacts: {str(e)}"


@tool
def get_all_emails() -> List[str]:
    """Get all email addresses from the CSV file.
    
    Returns:
        List of email addresses
    """
    try:
        ensure_csv_exists()
        df = pd.read_csv(CSV_FILE_PATH)
        return df['email'].tolist()
    
    except Exception as e:
        return []