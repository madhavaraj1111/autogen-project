import os
import json
from dotenv import load_dotenv
from autogen import ConversableAgent, UserProxyAgent
from datetime import datetime
from pymongo import MongoClient
from typing import Dict, Any

# Load environment variables
load_dotenv()

# MongoDB connection
client = MongoClient(os.getenv("MONGO_URI"))
db = client['testingautogen']
users_collection = db['users']

# Function to store user info with dynamic schema handling
def store_user_info(data: Dict[str, Any]) -> str:
    if not data:
        return "⚠️ No data received."
    
    try:
        # Define fixed fields
        fixed_fields = ['name', 'age', 'gender']
        
        # Extract and cast fields to string, early return for missing fields
        user_data = {field: str(data[field]) for field in fixed_fields if field in data}
        if len(user_data) != len(fixed_fields):
            return f"⚠️ Missing required fields: {', '.join(set(fixed_fields) - user_data.keys())}"
        
        # Add created_at timestamp
        user_data["created_at"] = datetime.now()

        # Upsert data into MongoDB
        result = users_collection.update_one(
            {"name": user_data["name"]},
            {"$set": user_data},
            upsert=True
        )
        return f"✅ User info {'inserted' if result.upserted_id else 'updated'} for {user_data['name']}"

    except Exception as e:
        return f"❌ An error occurred during database operation: {e}"

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
        "You have access to a MongoDB database where you can store user data. "
        "Your tasks are:\n"
        "1. **Data Extraction**: Receive user inputs and extract relevant information for the fields: `name`, `age`, and `gender`. Use the user's input to fill these fields.\n"
        "2. **Data Mapping**: Dynamically map the extracted information to the fixed schema without hardcoding any values.\n"
        "3. **Avoiding Duplicates**: When storing data, avoid creating duplicate entries. Use the `name` field as a unique identifier to check if a record already exists.\n"
        "4. **Upserting Data**: Use MongoDB's `update_one` operation with `upsert: true` to insert new records or update existing ones based on the `name` field.\n"
        "5. **Including Timestamps**: Always include a `created_at` timestamp indicating when the data was stored.\n"
        "6. **Error Handling**: If you cannot extract any relevant information, return an empty JSON object `{}`.\n"
        "7. **Terminate**: Return a termination message if the user indicates the conversation is over."
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
assistant.register_for_llm(name="store_user_info", description="Stores information in MongoDB.")(store_user_info)
assistant.register_for_execution(name="store_user_info")(store_user_info)
user_proxy.register_for_execution(name="store_user_info")(store_user_info)

# CRUD operations functions

def create_user(data: Dict[str, Any]):
    """Create a new user in MongoDB."""
    return store_user_info(data)

def update_user(data: Dict[str, Any]):
    """Update existing user information in MongoDB."""
    return store_user_info(data)

# Function to delete user by name
def delete_user(name: str) -> str:
    try:
        # Check if the user exists
        result = users_collection.delete_one({"name": name})

        if result.deleted_count == 1:
            return f"✅ User '{name}' has been deleted."
        else:
            return f"⚠️ No user found with the name '{name}'."
    except Exception as e:
        return f"❌ An error occurred during deletion: {e}"


def find_user(name: str):
    """Retrieve user data from MongoDB by name."""
    result = users_collection.find_one({"name": name})
    if result:
        return f"✅ User found: {result}"
    else:
        return "⚠️ User not found."

# Register delete function
assistant.register_for_llm(name="delete_user", description="Deletes user from MongoDB based on name.")(delete_user)
user_proxy.register_for_execution(name="delete_user")(delete_user)


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
                    if 'create' in query:  # Handle create operation
                        user_data = query.get("create", {})
                        print(create_user(user_data))
                    elif 'update' in query:  # Handle update operation
                        user_data = query.get("update", {})
                        print(update_user(user_data))
                    elif 'delete' in query:  # Handle delete operation
                        name_to_delete = query.get("delete", "")
                        print(delete_user(name_to_delete))  # Pass the name to delete
                    elif 'find' in query:  # Handle find operation
                        name = query.get("find", "")
                        print(find_user(name))
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
process_user_input()