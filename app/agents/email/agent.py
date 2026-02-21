"""
Email agent creation and configuration.
"""

from langchain.agents import create_agent
from .tools import send_email


EMAIL_AGENT_PROMPT = (
    "You are an email assistant. "
    "Compose professional emails based on natural language requests. "
    "Extract recipient information and craft appropriate subject lines and body text. "
    "Use send_email to send the message. "
    "Always confirm what was sent in your final response."
)


def create_email_agent(model):
    """Create and return email agent.
    
    Args:
        model: LLM model instance
    
    Returns:
        Email agent configured with tools
    """
    agent = create_agent(
        model,
        tools=[send_email],
        system_prompt=EMAIL_AGENT_PROMPT,
    )
    
    return agent