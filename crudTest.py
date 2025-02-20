import autogen
import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

temp_dir = tempfile.TemporaryDirectory()

config_list = [{
    "model": "llama-3.3-70b-specdec",
    "api_key": "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",
    "api_type": "groq",
    "temperature": 0.0,
    "cache_seed": 42,
    "timeout": 120,
}]

llm_config = {"config_list": config_list, "temperature": 0, "request_timeout": 1200}
mongo_uri = os.getenv("MONGO_URI") 

admin = autogen.UserProxyAgent(
    name="Admin",
    system_message="""
    You classify the user's query and direct it to the appropriate agent.
    You manage the overall workflow and ensure tasks are completed correctly.
    """,
    code_execution_config={
        "last_n_messages": 1,
        "work_dir": "coding",
        "use_docker": False,
    },
    human_input_mode="ALWAYS",
)

database_agent = autogen.AssistantAgent(
    name="Database_Agent",
    llm_config=llm_config,
    system_message="""
    You handle all MongoDB operations (database, collection, records).
    If the user request is to create multiple databases or collections, create code to do so.
    Generate Python code to perform the requested operation.
    Ensure code includes error handling and validation.
    Use MONGO_URI from the environment variables.
    When creating collections, include example documents.
    """,
)

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

code_executor = autogen.UserProxyAgent(
    name="Code_Executor",
    system_message="You execute MongoDB CRUD Python code. If errors occur, report them.",
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,  
    },
    human_input_mode="ALWAYS",
)

allowed_transitions = {
    admin: [database_agent],
    database_agent: [code_evaluator],  
    code_evaluator: [code_executor],  
    code_executor: [admin], 
}


groupchat = autogen.GroupChat(
    agents=[admin, database_agent, code_evaluator, code_executor],
    allowed_or_disallowed_speaker_transitions=allowed_transitions,
    speaker_transitions_type="allowed",  
    messages=[],
    max_round=20, 
    send_introductions=True,  
)


manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)


admin.initiate_chat(manager, message="""
create a sport rules database and inside that having collections as basket ball ,
football, cricket and some example record for each collections and also create a top5news database and 
the respective collections as international, national,politics and have some example records
and create education database and with collections school,college,University and some example records""")
temp_dir.cleanup()
