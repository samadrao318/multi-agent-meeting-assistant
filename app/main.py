# """
# Main entry point for the multi-agent system.
# Run the supervisor agent with sub-agents.
# Production-ready with clean, non-duplicate output.
# """

# import os
# import logging
# from dotenv import load_dotenv
# from langgraph.types import Command

# from app.core.llm_factory import create_llm
# from app.supervisor.supervisor_agent import create_supervisor_agent


# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)


# def main():
#     """Main function to run the multi-agent system with error handling."""
    
#     try:
#         # Load environment variables
#         load_dotenv()
#         logger.info("Environment variables loaded")
        
#         print("="*70)
#         print("🤖 MULTI-AGENT SYSTEM WITH SUB-AGENTS")
#         print("="*70)
#         print("\nCapabilities:")
#         print("  📅 Calendar Agent - Google Calendar booking")
#         print("  📧 Email Agent - Gmail sending")
#         print("  💾 Data Agent - CSV contact management")
#         print("  🤝 Human-in-the-Loop - Approval for critical actions")
#         print("="*70)
        
#         # Check environment variables
#         if not os.getenv("AZURE_OPENAI_ENDPOINT") or not os.getenv("AZURE_OPENAI_API_KEY"):
#             logger.error("Missing Azure OpenAI credentials")
#             print("\n❌ ERROR: Missing Azure OpenAI credentials!")
#             print("\nPlease create a .env file with:")
#             print("  AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/")
#             print("  AZURE_OPENAI_API_KEY=your-api-key")
#             print("  AZURE_OPENAI_DEPLOYMENT=gpt-4")
#             return
        
#         try:
#             # Initialize LLM
#             print("\n⚙️  Initializing Azure OpenAI model...")
#             logger.info("Initializing LLM...")
#             model = create_llm()
            
#             if model is None:
#                 raise ValueError("LLM initialization returned None")
            
#             print("✅ Model initialized")
#             logger.info("LLM initialized successfully")
            
#         except Exception as e:
#             logger.error(f"Failed to initialize LLM: {str(e)}", exc_info=True)
#             print(f"\n❌ Failed to initialize model: {str(e)}")
#             print("\nTroubleshooting:")
#             print("  1. Check AZURE_OPENAI_ENDPOINT is correct")
#             print("  2. Verify AZURE_OPENAI_API_KEY is valid")
#             print("  3. Ensure AZURE_OPENAI_DEPLOYMENT exists")
#             return
        
#         try:
#             # Create supervisor agent
#             print("⚙️  Creating supervisor agent with sub-agents...")
#             logger.info("Creating supervisor agent...")
#             supervisor = create_supervisor_agent(model, enable_hitl=True)
            
#             if supervisor is None:
#                 raise ValueError("Supervisor agent creation returned None")
            
#             print("✅ Supervisor agent ready")
#             logger.info("Supervisor agent created successfully")
            
#         except Exception as e:
#             logger.error(f"Failed to create supervisor: {str(e)}", exc_info=True)
#             print(f"\n❌ Failed to create supervisor agent: {str(e)}")
#             print("\nTroubleshooting:")
#             print("  1. Check all agent files exist")
#             print("  2. Verify tool imports are correct")
#             print("  3. Ensure LangChain dependencies are installed")
#             return
        
#         # Configuration for conversation
#         config = {"configurable": {"thread_id": "1"}}
        
#         print("\n" + "="*70)
#         print("💬 INTERACTIVE MODE")
#         print("="*70)
#         print("\nExample requests:")
#         print("  • 'Show me all contacts'")
#         print("  • 'Search for engineers'")
#         print("  • 'Add new contact: alice@example.com, Alice Smith, Designer'")
#         print("  • 'Schedule a meeting tomorrow at 2pm'")
#         print("  • 'Send an email to the team about the meeting'")
#         print("\nType 'quit' to exit")
#         print("="*70)
        
#         # Interactive loop
#         while True:
#             try:
#                 user_input = input("\n🗣️  You: ").strip()
                
#                 if not user_input:
#                     continue
                
#                 if user_input.lower() in ['quit', 'exit', 'q']:
#                     logger.info("User exited application")
#                     print("\n👋 Goodbye!")
#                     break
                
#                 logger.info(f"Processing user input: {user_input[:50]}...")
                
#                 print(f"\n{'='*70}")
#                 print("🤖 Processing request...")
#                 print(f"{'='*70}\n")
                
#                 # Run supervisor agent with error handling
#                 try:
#                     interrupts = []
                    
#                     for step in supervisor.stream(
#                         {"messages": [{"role": "user", "content": user_input}]},
#                         config,
#                     ):
#                         # Validate step
#                         if not step or not hasattr(step, 'values'):
#                             logger.warning("Invalid step received, skipping")
#                             continue
                        
#                         for update in step.values():
#                             # Handle regular messages
#                             if isinstance(update, dict):
#                                 messages = update.get("messages", [])
#                                 for message in messages:
#                                     if hasattr(message, 'content') and hasattr(message, 'type'):
#                                         if message.type == "ai":
#                                             print(f"🤖 Assistant: {message.content}\n")
#                                             logger.info("Assistant response sent")
                            
#                             # Handle interrupts (HITL) - CLEAN VERSION
#                             elif isinstance(update, (list, tuple)) and len(update) > 0:
#                                 try:
#                                     interrupt = update[0]
                                    
#                                     # Validate interrupt structure
#                                     if not hasattr(interrupt, 'value'):
#                                         logger.warning("Invalid interrupt structure")
#                                         continue
                                    
#                                     if not isinstance(interrupt.value, dict):
#                                         logger.warning("Interrupt value is not a dict")
#                                         continue
                                    
#                                     if 'action_requests' not in interrupt.value:
#                                         logger.warning("No action_requests in interrupt")
#                                         continue
                                    
#                                     interrupts.append(interrupt)
#                                     logger.info("Human approval requested")
                                    
#                                     # CLEAN DISPLAY - NO DUPLICATION
#                                     print(f"\n{'='*70}")
#                                     print("⚠️  HUMAN APPROVAL REQUIRED")
#                                     print(f"{'='*70}")
                                    
#                                     # Collect decisions for each action
#                                     decisions = []
#                                     action_requests = interrupt.value["action_requests"]
                                    
#                                     # Display all actions first
#                                     for idx, request in enumerate(action_requests, 1):
#                                         print(f"\n📋 Action {idx}:")
#                                         print(f"   Tool: {request.get('tool_name', 'Unknown')}")
                                        
#                                         # Display arguments in clean format
#                                         args = request.get('args', {})
#                                         if args:
#                                             print(f"   Arguments:")
#                                             for key, value in args.items():
#                                                 # Format value nicely
#                                                 if isinstance(value, list):
#                                                     value_str = ', '.join(str(v) for v in value)
#                                                     print(f"     • {key}: {value_str}")
#                                                 elif isinstance(value, str) and len(value) > 50:
#                                                     print(f"     • {key}: {value[:50]}...")
#                                                 else:
#                                                     print(f"     • {key}: {value}")
                                    
#                                     print(f"\n{'='*70}")
                                    
#                                     # Ask for decision for EACH action
#                                     for idx, request in enumerate(action_requests, 1):
#                                         tool_name = request.get('tool_name', 'Unknown')
                                        
#                                         print(f"\nAction {idx} ({tool_name}):")
#                                         print("  [a] Approve")
#                                         print("  [r] Reject")
                                        
#                                         decision = input(f"Your choice for Action {idx} (a/r): ").strip().lower()
                                        
#                                         if decision == 'a':
#                                             decisions.append({"type": "approve"})
#                                             print(f"  ✅ Action {idx} approved")
#                                         else:
#                                             decisions.append({"type": "reject"})
#                                             print(f"  ❌ Action {idx} rejected")
                                    
#                                     print(f"\n{'='*70}")
#                                     logger.info(f"User provided {len(decisions)} decisions")
                                    
#                                     # Create resume with ALL decisions
#                                     resume = {
#                                         interrupt.id: {
#                                             "decisions": decisions
#                                         }
#                                     }
                                    
#                                     # Continue with decision
#                                     try:
#                                         for step2 in supervisor.stream(
#                                             Command(resume=resume),
#                                             config,
#                                         ):
#                                             if not step2 or not hasattr(step2, 'values'):
#                                                 continue
                                            
#                                             for update2 in step2.values():
#                                                 if isinstance(update2, dict):
#                                                     messages = update2.get("messages", [])
#                                                     for message in messages:
#                                                         if hasattr(message, 'content') and hasattr(message, 'type'):
#                                                             if message.type == "ai":
#                                                                 print(f"\n🤖 Assistant: {message.content}\n")
#                                                                 logger.info("Post-approval response sent")
                                    
#                                     except Exception as e:
#                                         logger.error(f"Error resuming after decision: {str(e)}")
#                                         print(f"\n⚠️  Warning: Error processing decision - {str(e)}")
#                                         continue
                                
#                                 except (AttributeError, KeyError, IndexError, TypeError) as e:
#                                     logger.warning(f"Error processing interrupt: {str(e)}")
#                                     print(f"\n⚠️  Warning: Could not process approval request")
#                                     continue
                    
#                     print(f"{'='*70}\n")
                
#                 except Exception as e:
#                     logger.error(f"Error during agent execution: {str(e)}", exc_info=True)
#                     print(f"\n❌ Error processing request: {str(e)}")
#                     print("\nPossible causes:")
#                     print("  • Missing Google API credentials (for Calendar/Email)")
#                     print("  • Network connectivity issues")
#                     print("  • Invalid input format")
#                     print("\nTry:")
#                     print("  • Use Data Agent commands (don't need Google APIs)")
#                     print("  • Check credentials.json exists")
#                     print("  • Verify .env configuration")
#                     print(f"\n{'='*70}\n")
            
#             except KeyboardInterrupt:
#                 logger.info("User interrupted with Ctrl+C")
#                 print("\n\n👋 Interrupted. Goodbye!")
#                 break
            
#             except Exception as e:
#                 logger.error(f"Unexpected error in loop: {str(e)}", exc_info=True)
#                 print(f"\n❌ Unexpected error: {str(e)}")
#                 print("Please try again.\n")
    
#     except Exception as e:
#         logger.critical(f"Critical error in main: {str(e)}", exc_info=True)
#         print(f"\n❌ Critical error: {str(e)}")
#         print("\nTroubleshooting:")
#         print("  1. Check .env file exists and is properly formatted")
#         print("  2. Verify all required packages are installed")
#         print("  3. Ensure Python version is 3.8+")
#         print("  4. Check file permissions")


# if __name__ == "__main__":
#     main()