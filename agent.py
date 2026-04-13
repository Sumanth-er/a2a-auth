import os
import httpx
import logging
import json
import base64
from collections.abc import AsyncIterable
from typing import Any, Literal, Optional

from pydantic import BaseModel

from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, ToolMessage
from langchain.agents.structured_output import ToolStrategy
from langchain.agents.structured_output import ProviderStrategy

from llm_models import llm
from agent_tools import addition, division, multiplication, power, root, subtraction

# Langfuse integration
try:
    from langfuse.decorators import observe
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    observe = lambda f: f  # Dummy decorator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

memory = MemorySaver()

# Initialize Langfuse if credentials provided
langfuse_client = None
if LANGFUSE_AVAILABLE:
    if os.getenv('LANGFUSE_PUBLIC_KEY') and os.getenv('LANGFUSE_SECRET_KEY'):
        try:
            langfuse_client = Langfuse(
                public_key=os.getenv('LANGFUSE_PUBLIC_KEY'),
                secret_key=os.getenv('LANGFUSE_SECRET_KEY'),
                host=os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com'),
            )
            logger.info("Langfuse initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse: {e}")


class ResponseFormat(BaseModel):
    """Respond to the user in this format."""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


class CalculatorAgent:
    """Calculator Agent with Langfuse observability"""

    SYSTEM_INSTRUCTION = (
        'You are a helpful and precise mathematical assistant. '
        'Your primary function is to solve arithmetic and mathematical problems accurately '
        'Use available tools to resolved the users mathematical questions '
    )

    FORMAT_INSTRUCTION = (
        'Set response status to input_required if the user needs to provide more information to complete the request.'
        'Set response status to error if there is an error while processing the request.'
        'Set response status to completed if the request is complete.'
    )

    def __init__(self, enable_advanced_tools: bool = False):
        self.model = llm

        self.tools = [addition, subtraction, multiplication, division]
        if enable_advanced_tools:
            self.tools.extend([power, root])

        self.graph = create_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            system_prompt=self.SYSTEM_INSTRUCTION,
            # Use below if model provider doesn't supports native structured output
            response_format=ToolStrategy(ResponseFormat),

            # Use below if model provider supports native structured output
            # response_format=ProviderStrategy(ContactInfo)
        )

    @observe(name="agent_stream")
    async def stream(
        self,
        query: str,
        context_id: str,
        keycloak_token: Optional[str] = None
    ) -> AsyncIterable[dict[str, Any]]:
        """
        Stream agent responses with Langfuse observability
        
        Args:
            query: User's question
            context_id: Conversation thread ID
            keycloak_token: JWT token from Keycloak (for user context)
        """
        # Extract user context from JWT
        user_context = self._decode_keycloak_token(keycloak_token) if keycloak_token else None
        
        # Log with Langfuse
        user_email = user_context.get('email', 'unknown') if user_context else 'unknown'
        user_id = user_context.get('user_id', 'unknown') if user_context else 'unknown'
        user_name = user_context.get('name', 'unknown') if user_context else 'unknown'
        user_username = user_context.get('username', 'unknown') if user_context else 'unknown'
        user_roles = user_context.get('roles', []) if user_context else []
        
        # Role-based access control
        required_role = 'agent-user'
        if required_role not in user_roles:
            error_msg = f"User {user_email} lacks required '{required_role}' role. Current roles: {user_roles}"
            logger.warning(f"Access denied: {error_msg}")
            yield {
                'status': 'error',
                'is_task_complete': False,
                'require_user_input': False,
                'content': f"Access denied. You must have '{required_role}' role to use this agent.",
            }
            return
        
        logger.info(f"Agent invoked by {user_email} ({user_id}) - Thread: {context_id}")
        
        if langfuse_client:
            langfuse_client.trace(
                name="calculator_query",
                user_id=user_id,
                input={"query": query, "context_id": context_id},
                metadata={
                    "user_email": user_email,
                    "user_name": user_name,
                    "user_username": user_username,
                    "roles": user_roles,
                    "context_id": context_id
                }
            )
        
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id}}
        logger.info(f"Agent invoked with thread_id: {context_id}")

        for chunk in self.graph.stream(inputs, config, stream_mode='updates'):
            logger.info("Agent response:")
            logger.info(f"chunk: {chunk}")

            for step, data in chunk.items():
                if structured_response := data.get('structured_response'):
                    yield self.get_agent_response(structured_response)
                    continue

                message = data['messages'][-1]

                if isinstance(message, AIMessage):
                    if message.tool_calls and len(message.tool_calls) > 0:
                        for tool in message.tool_calls:
                            tool_name = tool["name"]
                            tool_args = str(tool["args"])
                            
                            # Log tool call with Langfuse
                            if langfuse_client:
                                langfuse_client.event(
                                    name=f"tool_call_{tool_name}",
                                    input={"args": tool_args},
                                    metadata={
                                        "user_email": user_email,
                                        "user_id": user_id,
                                        "tool_name": tool_name,
                                        "context_id": context_id
                                    }
                                )
                            
                            yield {
                                'status': 'working',
                                'is_task_complete': False,
                                'require_user_input': False,
                                'content': f'Invoking {tool_name} tool with arguments {tool_args}',
                            }
                    else:
                        # No structured terminal payload from the model; treat as
                        # regular completion if content exists, else ask for input.
                        has_content = bool(str(message.content).strip())
                        yield {
                            'status': 'completed' if has_content else 'input_required',
                            'is_task_complete': has_content,
                            'require_user_input': not has_content,
                            'content': message.content or 'Please provide more details.',
                        }
                elif isinstance(message, ToolMessage):
                    tool_name = message.name
                    tool_response = message.content
                    
                    # Log tool response with Langfuse
                    if langfuse_client:
                        langfuse_client.event(
                            name=f"tool_result_{tool_name}",
                            output={"result": tool_response},
                            metadata={
                                "user_email": user_email,
                                "user_id": user_id,
                                "tool_name": tool_name,
                                "context_id": context_id
                            }
                        )
                    
                    yield {
                        'status': 'working',
                        'is_task_complete': False,
                        'require_user_input': False,
                        'content': f'Response from {tool_name} tool is {tool_response}',
                    }

    def get_agent_response(self, structured_response):
        logging.info(f'Final agent response: {structured_response}')
        logging.info(f'Final response type: {type(structured_response)}')
        if structured_response and isinstance(
            structured_response, ResponseFormat
        ):
            if structured_response.status == 'input_required':
                return {
                    'status': 'input_required',
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'error':
                return {
                    'status': 'error',
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': structured_response.message,
                }
            if structured_response.status == 'completed':
                return {
                    'status': 'completed',
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': structured_response.message,
                }

        return {
            'status': 'error',
            'is_task_complete': False,
            'require_user_input': False,
            'content': (
                'We are unable to process your request at the moment. '
                'Please try again.'
            ),
        }

    @staticmethod
    def _decode_keycloak_token(keycloak_token: Optional[str]) -> Optional[dict]:
        """Decode JWT without signature verification (backend already verified)"""
        if not keycloak_token:
            return None

        try:
            # JWT format: header.payload.signature
            parts = keycloak_token.split('.')
            if len(parts) != 3:
                return None

            # Decode payload (add padding if needed)
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding

            decoded_bytes = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded_bytes)

            # Extract user info
            return {
                'user_id': claims.get('sub'),
                'email': claims.get('email'),
                'name': claims.get('name'),
                'username': claims.get('preferred_username'),
                'roles': claims.get('realm_access', {}).get('roles', []),
                'full_claims': claims,  # Store all claims if needed
            }

        except Exception as e:
            logger.error(f"Error decoding Keycloak token: {e}")
            return None

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
