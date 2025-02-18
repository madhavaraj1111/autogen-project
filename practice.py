import os
from autogen import ConversableAgent,UserProxyAgent
from autogen.coding import LocalCommandLineCodeExecutor
from pymongo import MongoClient
import tempfile
import json

temp_dir=tempfile.TemporaryDirectory()

client = MongoClient(os.getenv("MONGO_URI"))
db = client['testingautogen']
collection = db['users']

config_list = [{
    "model": "llama-3.3-70b-specdec",  
    "api_key": "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",  
    "api_type": "groq",
    "temperature": 0.0,
}]

query_writer_agent=ConversableAgent(
    name="query_writer_agent",
    system_message="You are a query writer agent in the python language. Based on the users need you want to write queries to (insert , update , delete ,find) datas into the mongodb to database 'testingautogen' connection string in the .env file name 'MONGO_URI' and collection 'users' and you have fixed schema of name,age,gender.",
    llm_config={"config_list":config_list},
)


local_executor=LocalCommandLineCodeExecutor(
	timeout=10,
    work_dir=temp_dir.name,
)


local_executor_agent = ConversableAgent(
	"local_executor_agent",
	llm_config=False,
	code_execution_config={"executor": local_executor},
	human_input_mode="ALWAYS",
	is_termination_msg=lambda msg:"TERMINATION" in msg["content"].upper(),
)

user_proxy = UserProxyAgent(
	name="user_proxy",
	code_execution_config={"executor":local_executor},
	
)

messages = ["Update Jegan age to 24"]

# Intialize the chat
chat_result = local_executor_agent.initiate_chat(
	query_writer_agent,
	message=messages[0],
)

temp_dir.cleanup()
