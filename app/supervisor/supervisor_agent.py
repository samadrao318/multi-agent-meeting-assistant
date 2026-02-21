"""
Supervisor agent that coordinates calendar, email, and data sub-agents.
Includes Human-in-the-Loop for critical actions.
Production-ready with error handling and clean imports.
"""

import logging
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

# Import actual tools (these are used directly)
from app.agents.calendar.tools import create_calendar_event, get_available_time_slots
from app.agents.email.tools import send_email
from app.agents.data.tools import read_contacts, add_contact, search_contacts, get_all_emails


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_supervisor_agent(model, enable_hitl: bool = True):
    """Create supervisor agent with all sub-agents and error handling.
    
    Args:
        model: LLM model instance
        enable_hitl: Enable Human-in-the-Loop for critical actions
    
    Returns:
        Supervisor agent with checkpointer
        
    Raises:
        ValueError: If required tools are not available
        Exception: If agent creation fails
    """
    
    try:
        logger.info("Starting supervisor agent creation...")
        
        # Validate model
        if model is None:
            raise ValueError("Model cannot be None")
        
        # Wrap calendar tools with HITL
        if enable_hitl:
            calendar_tools = [create_calendar_event, get_available_time_slots]
            email_tools = [send_email]
        else:
            calendar_tools = [create_calendar_event, get_available_time_slots]
            email_tools = [send_email]
        
        # Data tools don't need HITL for read operations
        data_tools = [read_contacts, add_contact, search_contacts, get_all_emails]
        
        # Validate all tools are available
        all_tools = calendar_tools + email_tools + data_tools
        
        if not all_tools or len(all_tools) == 0:
            raise ValueError("No tools available for supervisor agent")
        
        logger.info(f"Loaded {len(all_tools)} tools successfully")
        
        # Supervisor prompt
        SUPERVISOR_PROMPT = (
            "You are a personal assistant with direct tool access. "
            "CRITICAL: USE tools to execute tasks, don't just describe them.\n\n"
            
            "Tools available:\n"
            "• create_calendar_event, get_available_time_slots\n"
            "• send_email\n"
            "• read_contacts, add_contact, search_contacts, get_all_emails\n\n"
            
            "Rules:\n"
            "1. Email request → USE send_email tool\n"
            "2. Calendar request → USE create_calendar_event tool\n"
            "3. Data request → USE read_contacts or search_contacts\n"
            "4. Multi-step task → Execute each tool sequentially\n"
            "5. Datetime format: ISO (YYYY-MM-DDTHH:MM:SS)\n\n"
            
            "IMPORTANT:\n"
            "- If calendar/email tools show 'not configured', explain setup to user\n"
            "- Data tools always work (CSV-based)\n"
            "- Human approval required for: send_email, create_calendar_event\n"
            "- Always provide clear, actionable responses"
        )
        
        # Create supervisor agent
        try:
            if enable_hitl:
                logger.info("Creating supervisor with Human-in-the-Loop enabled")
                supervisor = create_agent(
                    model,
                    tools=all_tools,
                    system_prompt=SUPERVISOR_PROMPT,
                    middleware=[
                        HumanInTheLoopMiddleware(
                            interrupt_on={
                                "create_calendar_event": True,
                                "send_email": True,
                            },
                            description_prefix="⚠️  Action requires approval",
                        ),
                    ],
                    checkpointer=InMemorySaver(),
                )
            else:
                logger.info("Creating supervisor without Human-in-the-Loop")
                supervisor = create_agent(
                    model,
                    tools=all_tools,
                    system_prompt=SUPERVISOR_PROMPT,
                    checkpointer=InMemorySaver(),
                )
            
            logger.info("Supervisor agent created successfully")
            return supervisor
            
        except Exception as e:
            logger.error(f"Failed to create agent: {str(e)}")
            raise Exception(f"Agent creation failed: {str(e)}")
    
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise
    
    except ImportError as ie:
        logger.error(f"Import error - missing dependencies: {str(ie)}")
        raise Exception(f"Failed to import required modules: {str(ie)}")
    
    except Exception as e:
        logger.error(f"Unexpected error creating supervisor: {str(e)}", exc_info=True)
        raise Exception(f"Failed to create supervisor agent: {str(e)}")