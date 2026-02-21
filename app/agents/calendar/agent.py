"""
Calendar agent creation and configuration.
"""

from langchain.agents import create_agent
from .tools import create_calendar_event, get_available_time_slots


CALENDAR_AGENT_PROMPT = (
    "You are a calendar scheduling assistant. "
    "Parse natural language scheduling requests (e.g., 'next Tuesday at 2pm') "
    "into proper ISO datetime formats (YYYY-MM-DDTHH:MM:SS). "
    "Use get_available_time_slots to check availability when needed. "
    "Use create_calendar_event to schedule events. "
    "Always confirm what was scheduled in your final response."
)


def create_calendar_agent(model):
    """Create and return calendar agent.
    
    Args:
        model: LLM model instance
    
    Returns:
        Calendar agent configured with tools
    """
    agent = create_agent(
        model,
        tools=[create_calendar_event, get_available_time_slots],
        system_prompt=CALENDAR_AGENT_PROMPT,
    )
    
    return agent