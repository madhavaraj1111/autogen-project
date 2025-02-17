import os
import json
from dotenv import load_dotenv
from autogen import ConversableAgent,UserProxyAgent,AssistantAgent
from pydantic import BaseModel,create_model
from typing import Annotated,Dict,Any,Optional
from pymongo import MongoClient
from datetime import datetime
import re

# Load environment variables
load_dotenv()

# MongoDB connection
client = MongoClient('mongodb+srv://madhavaraj1111:2004madhav@cluster0.lwkaz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client['testingautogen']
users_collection = db['users']


# MongoDB connection (using environment variables is best practice)
MONGO_URI = os.getenv("MONGO_URI")  # Set this in your .env file
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set.")

try:
    client = MongoClient(MONGO_URI)
    db = client['testingautogen']
    users_collection = db['users']
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

# Function to dynamically create and validate schema (Improved)
def store_user_info(data: Dict[str, Any]) -> str:
    if not data:
        return "⚠️ No data received."

    try:
        fields = {}
        for k, v in data.items():
            field_type = type(v) if v is not None else str  # Handle None values and infer type
            fields[k] = (Optional[field_type], None)

        DynamicUserInfo = create_model("DynamicUserInfo", **fields)
        user_info = DynamicUserInfo(**data)
        user_data = user_info.dict(exclude_none=True)
        user_data["created_at"] = datetime.now()

        users_collection.insert_one(user_data)
        return f"✅ User info stored: {user_data}"

    except ValueError as e:
        return f"❌ Validation Error: {e}"
    except Exception as e:
        return f"❌ An error occurred during database operation: {e}"  # More specific error message

# AutoGen Agents
config_list = [{
    "model": "llama-3.3-70b-versatile",  # Or any other model you have access to
    "api_key": "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",  # Replace with your actual key
    "api_type": "groq",
    "temperature": 0.9,
}]
assistant = ConversableAgent(
    name="assistant",
    llm_config={"config_list": config_list},
    system_message=(
        "You are a helpful assistant. "
        "You have access to a MongoDB database where you can store any user data provided. "
        "Your tasks are:\n"
        "1. **Data Extraction**: Receive user inputs and extract all relevant information, regardless of the fields provided. You should handle dynamic data without relying on any predefined schemas.\n"
        "2. **Avoiding Duplicates**: When storing data, avoid creating duplicate entries. Use a unique identifier (e.g., 'name' or any other appropriate field) to check if a record already exists.\n"
        "3. **Upserting Data**: Use MongoDB's `update_one` operation with `upsert: true` to insert new records or update existing ones based on the unique identifier.\n"
        "4. **Including Timestamps**: Always include a `created_at` timestamp indicating when the data was stored.\n"
        "5. **Response Format**: Return **only** the MongoDB query as a JSON object. Do not include any additional text or explanations.\n"
        "   - For upserting data:\n"
        "     ```json\n"
        "     {\n"
        "       \"update_one\": {\n"
        "         \"filter\": {\"unique_field\": \"value\"},\n"
        "         \"update\": {\"$set\": {\"field1\": \"value1\", \"field2\": \"value2\", \"created_at\": \"timestamp\"}},\n"
        "         \"upsert\": true\n"
        "       }\n"
        "     }\n"
        "     ```\n"
        "   - For finding data:\n"
        "     ```json\n"
        "     {\n"
        "       \"find\": {\"field\": \"value\"}\n"
        "     }\n"
        "     ```\n"
        "6. **Termination**: If the user indicates that the conversation is over, return:\n"
        "   ```json\n"
        "   {\"TERMINATE\": true}\n"
        "   ```\n"
        "7. **Error Handling**: If you cannot extract any relevant information, return an empty JSON object `{}`.\n"
        "\n"
        "Remember, you should **not hardcode** any fields or values. Handle all data dynamically based on the user's input. Ensure the workflow is flexible and can adapt to any information the user provides."
    )
)



user_proxy = UserProxyAgent(  # Corrected is_termination_msg
    name="User",
    llm_config=False,
    is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
    human_input_mode="ALWAYS",
    code_execution_config={"use_docker": False}
)


# Register MongoDB tool (for both LLM and execution)
assistant.register_for_llm(name="store_user_info", description="Stores information in MongoDB.  The data should be a JSON object.")(store_user_info)
assistant.register_for_execution(name="store_user_info")(store_user_info)
user_proxy.register_for_execution(name="store_user_info")(store_user_info)



def process_user_input():
    user_proxy.initiate_chat(assistant, message="Hi, I'm ready to provide user information.")

    while True:
        user_input = input("User: ")
        if user_input.lower() == "exit":
            break
        user_proxy.send(user_input, assistant)
        response = assistant.last_message()
        content = response.get("content")

        if content:
            try:
                query = json.loads(content)
                if query.get("TERMINATE"):
                    print("Assistant: Conversation ended.")
                    break

                if query:
                    # Execute the query based on its type
                    if 'update_one' in query:
                        filter_query = query['update_one']['filter']
                        update_query = query['update_one']['update']
                        upsert = query['update_one'].get('upsert', False)
                        result = users_collection.update_one(filter_query, update_query, upsert=upsert)
                        if result.upserted_id:
                            print(f"Assistant: Data inserted with ID {result.upserted_id}")
                        else:
                            print(f"Assistant: Data updated. Matched count: {result.matched_count}")
                    elif 'find' in query:
                        results = users_collection.find(query['find'])
                        results_list = list(results)
                        print(f"Assistant: Retrieved data: {results_list}")
                    else:
                        print("Assistant: Unrecognized query operation.")
                else:
                    print("Assistant: No valid query generated.")
            except json.JSONDecodeError as e:
                print(f"Assistant: Invalid JSON returned by assistant: {content}. Error: {e}")
            except Exception as e:
                print(f"Assistant: An error occurred: {e}")
        else:
            print("Assistant: No content received from assistant.")

    print("Conversation ended.")

# Start processing user input
process_user_input()
