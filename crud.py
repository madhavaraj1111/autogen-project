import autogen
import tempfile
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create a temporary directory for execution
temp_dir = tempfile.TemporaryDirectory()

# LLM Configuration
config_list = [{
    "model": "llama-3.3-70b-versatile",
    "api_key": os.getenv("GROQ_API_KEY"),  # Secure API key using environment variables
    "api_type": "groq",
    "temperature": 0.0,
    "cache_seed": 42,
    "timeout": 120,
}]

llm_config = {
    "config_list": config_list,
    "temperature": 0,
    "request_timeout": 1200
}

# MongoDB Connection String from .env
mongo_uri = os.getenv("MONGO_URI")

# User Proxy (Admin) - Oversees the process
admin = autogen.UserProxyAgent(
    name="Admin",
    system_message="You oversee the process. If an error occurs in execution, repeat the cycle: generation -> evaluation -> execution.",
    code_execution_config={
        "last_n_messages": 1,
        "work_dir": temp_dir.name,
        "use_docker": False,
    },
    human_input_mode="ALWAYS",
)

# Code Generator - Generates Python code for MongoDB CRUD operations
code_generator = autogen.AssistantAgent(
    name="Code_Generator",
    llm_config=llm_config,
    system_message=f"""
    You generate Python code to perform CRUD operations on a MongoDB database.
    - The MongoDB connection string is stored in the `MONGO_URI` environment variable.
    - Use `pymongo` to connect and execute queries.
    - Ensure proper exception handling in the code.
    """,
)

# Code Evaluator - Checks the code before execution
code_evaluator = autogen.AssistantAgent(
    name="Code_Evaluator",
    llm_config=llm_config,
    system_message="""
    You evaluate the generated Python code before execution.
    - Ensure the code correctly connects to MongoDB using `MONGO_URI`.
    - Check if it follows correct MongoDB query syntax.
    - If errors are found, fix them before execution.
    """,
)

# Code Executor - Runs the MongoDB code
code_executor = autogen.UserProxyAgent(
    name="Code_Executor",
    system_message="You execute the given Python code. If errors occur, report them for correction.",
    code_execution_config={
        "last_n_messages": 1,
        "work_dir": temp_dir.name,
        "use_docker": False,
    },
    human_input_mode="NEVER",
)

# Group Chat
groupchat = autogen.GroupChat(
    agents=[admin, code_generator, code_evaluator, code_executor],
    messages=[],
    max_round=20,
    speaker_selection_method="round_robin"
)

# Group Chat Manager
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# Start Chat
admin.initiate_chat(
    manager,
    message="Generate Python code to delete a database sports , evaluate the code, and execute it. If errors occur, correct them and retry."
)

# Cleanup after chat ends
temp_dir.cleanup()
