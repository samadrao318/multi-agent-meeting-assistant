"""
Data agent creation and configuration.
"""

from langchain.agents import create_agent
from .tools import read_contacts, add_contact, search_contacts, get_all_emails


DATA_AGENT_PROMPT = (
    "You are a data management assistant. "
    "You can read, search, and add contacts from a CSV database. "
    "The CSV contains: email, name, and designation fields. "
    "Use read_contacts to view all contacts or filter by designation. "
    "Use search_contacts to find specific contacts. "
    "Use add_contact to add new contacts. "
    "Use get_all_emails to retrieve all email addresses. "
    "Always provide clear responses about what data was found or modified."
)


def create_data_agent(model):
    """Create and return data agent.
    
    Args:
        model: LLM model instance
    
    Returns:
        Data agent configured with tools
    """
    agent = create_agent(
        model,
        tools=[read_contacts, add_contact, search_contacts, get_all_emails],
        system_prompt=DATA_AGENT_PROMPT,
    )
    
    return agent