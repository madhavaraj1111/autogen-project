import autogen
import os
# import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create a temporary directory for execution
# temp_dir = tempfile.TemporaryDirectory()

# LLM Configuration
config_list = [{
    "model": "llama-3.3-70b-versatile",
    "api_key":"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",
    "api_type": "groq",
    "temperature": 0.0,
    "cache_seed": 42,
    "timeout": 120,
}]

llm_config = {"config_list": config_list, "temperature": 0, "request_timeout": 1200}
mongo_uri = os.getenv("MONGO_URI")  # MongoDB Connection String

# **Admin Agent - Oversees the process**
admin = autogen.UserProxyAgent(
    name="Admin",
    system_message="""
    You classify the user's query into MONGODB and connection string MONGO_URI is in .env file import os to get that:
    1. Database-level operations (Create, List, Delete, Rename).
    2. Collection-level operations (Create, List, Delete, Rename).
    3. Record-level operations (Insert, Retrieve, Update, Delete).

    Rules:
    - Always list databases before creating a new one.
    - If the database exists, do not create a new one. Instead, proceed with collection or record operations.
    - If the user wants to delete a database, ensure it exists before dropping it.
    - If the user wants to rename a database, check if renaming is possible and perform the update.
    """,
    code_execution_config={
        "last_n_messages": 1,
        "work_dir": "coding",
        "use_docker": False,
    },
    human_input_mode="ALWAYS",
)

# **Database Agent - Handles DB-level CRUD operations**
database_agent = autogen.AssistantAgent(
    name="Database_Agent",
    llm_config=llm_config,
    system_message="""
    You handle database-level operations in MONGODB connection string MONGO_URI is in .env file import os to get that:
    
    - **List Databases**: Retrieve and show all available databases.
    - **Create Database**: Before creating a new database, first list existing databases. If it already exists, do not create a duplicate.
    - **Delete Database**: Before deletion, check if the database exists. If it exists, delete it.
    - **Rename Database**: If the user requests a rename, check if renaming is possible and execute the update.

    Always ensure proper validation before performing any operation.
    """,
)

# **Collection Agent - Handles Collection-level CRUD operations**
collection_agent = autogen.AssistantAgent(
    name="Collection_Agent",
    llm_config=llm_config,
    system_message="""
    You handle collection-level operations inside a MONGODB database connection string MONGO_URI is in .env file import os to get that.

    - **List Collections**: Retrieve and show all collections inside the specified database.
    - **Create Collection**: Check if the collection exists before creating it. If it exists, do nothing.
    - **Delete Collection**: Verify the collection exists before deletion.
    - **Rename Collection**: If renaming is requested, check if it is possible and perform the update.

    Always ensure that the database exists before performing any collection-related operations.
    """,
)

# **Record Agent - Handles Record-level CRUD operations**
record_agent = autogen.AssistantAgent(
    name="Record_Agent",
    llm_config=llm_config,
    system_message="""
    You handle CRUD operations at the record level inside a MongoDB collection connection string MONGO_URI is in .env file import os to get that.

    - **Insert Record**: Ensure the collection exists before inserting the record. Validate data against the predefined schema.
    - **Retrieve Records**: Fetch all or specific records based on user input.
    - **Update Record**: Modify only the specified fields without affecting other data.
    - **Delete Record**: Remove a document only if it exists.

    Always check if the collection exists before performing any record operation.
    """,
)

# **Schema Validator - Ensures Schema Compliance**
schema_validator = autogen.AssistantAgent(
    name="Schema_Validator",
    llm_config=llm_config,
    system_message="""
    You validate MongoDB documents before insertion or updates connection string MONGO_URI is in .env file import os to get that.

    - Ensure the record follows a predefined schema.
    - Prevent missing or incorrect fields.
    - If the schema is invalid, reject the request and ask the user for corrections.
    """,
)

# **Code Evaluator - Checks Code Before Execution**
code_evaluator = autogen.AssistantAgent(
    name="Code_Evaluator",
    llm_config=llm_config,
    system_message="""
    You verify if the generated Python code:

    - Connects correctly to MongoDB (using MONGO_URI from .env).
    - Uses valid MongoDB query syntax.
    - Includes exception handling to prevent crashes.
    
    If an issue is found, suggest corrections before execution.
    """,
)

# **Code Executor - Runs the Code**
code_executor = autogen.UserProxyAgent(
    name="Code_Executor",
    system_message="You execute MongoDB CRUD Python code. If errors occur, report them.",
    code_execution_config={
        "last_n_messages": 1,
        "work_dir": "coding",
        "use_docker": False,  # Ensure Docker is disabled
    },
    human_input_mode="ALWAYS",
)

allowed_transitions = {
    admin: [database_agent, collection_agent, record_agent],
    database_agent: [code_evaluator],  # Validate before execution
    collection_agent: [code_evaluator],
    record_agent: [schema_validator],  # Validate schema first
    schema_validator: [code_evaluator],  # Then check the query
    code_evaluator: [code_executor],  # Ensure it's correct
    code_executor: [admin],  # Send final execution result
}

# **Group Chat Setup**
groupchat = autogen.GroupChat(
    agents=[admin, database_agent, collection_agent, record_agent, schema_validator, code_evaluator, code_executor],
    allowed_or_disallowed_speaker_transitions=allowed_transitions,
    speaker_transitions_type="allowed",  # Enforce allowed transitions only
    messages=[],
    max_round=20,
    send_introductions=True,  # Agents introduce themselves before first response
)

# **Group Chat Manager**
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# **Admin initiates the request**
admin.initiate_chat(manager, message="Update the rule for 'Tennis' in the tennis collection in 'sports_db'. The new rule should be 'Use a racket to hit the ball'.")

# **Cleanup temporary files**
# temp_dir.cleanup()
