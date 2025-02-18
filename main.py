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
    "model": "llama-3.3-70b-specdec",  # Or any other model you have access to
    "api_key": "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",  # Replace with your actual key
    "api_type": "groq",
    "temperature": 0.9,
}]

assistant = ConversableAgent(
    name="assistant",
    llm_config={"config_list": config_list},
    system_message=(
        "You are a helpful assistant with access to a MongoDB database. "
        "You can perform CRUD operations (Create, Read, Update, Delete) on the 'users' collection. "
        "You will receive instructions from the user on what operation to perform and the data involved. "
        "Your job is to generate the correct MongoDB queries (using pymongo syntax) based on the user's request, and then execute those queries. "
        "Return the results of the query execution to the user. "
        "If the user's request is unclear or invalid, return an appropriate error message. "
        "If the user wants to add multiple users, generate and execute the insert_many query. "
        "If the user wants to find users based on criteria, generate and execute the find query with appropriate filters, projections, sorting, and limits. "
        "If the user wants to update users, generate and execute the update_many or update_one query. "
        "If the user wants to delete users, generate and execute the delete_many or delete_one query. "
        "If the user wants to find all users, generate and execute the find query without any filter. "
        "Always handle exceptions gracefully and return informative error messages. "
        "Return a JSON object containing the results of the operation.  For successful operations, include a 'status': 'success' and the 'data' (if any). For errors, include a 'status': 'error' and a 'message' describing the error. "
        "Example: {'status': 'success', 'data': [{'name': 'John', 'age': 30}]} or {'status': 'error', 'message': 'Invalid input'} "
        "Terminate the conversation when the user says 'exit'."
    )
)

user_proxy = UserProxyAgent(
    name="User",
    llm_config=False,
    is_termination_msg=lambda msg: msg.get("content") is not None and "exit" in msg["content"].lower(),
    human_input_mode="ALWAYS",
    code_execution_config={"use_docker": False}
)

# Register MongoDB tool (for both LLM and execution)
assistant.register_for_llm(name="store_user_info", description="Stores information in MongoDB.")(store_user_info)
assistant.register_for_execution(name="store_user_info")(store_user_info)
user_proxy.register_for_execution(name="store_user_info")(store_user_info)

# CRUD operation functions (now directly interacting with MongoDB)

def execute_mongo_query(query_type: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if query_type == "insert_many":
            result = users_collection.insert_many(query_params.get("documents", []))
            return {"status": "success", "data": {"inserted_ids": [str(id) for id in result.inserted_ids]}}

        elif query_type == "find":
            find_params = query_params.get("filter", {})
            projection = query_params.get("projection")
            sort = query_params.get("sort")
            limit = query_params.get("limit")

            cursor = users_collection.find(find_params, projection=projection, sort=sort, limit=limit)
            data = list(cursor)  # Convert cursor to a list of dictionaries
            for doc in data:  # Convert ObjectId to string for JSON serialization
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            return {"status": "success", "data": data}

        elif query_type == "update_one":
            result = users_collection.update_one(query_params.get("filter", {}), query_params.get("update", {}))
            return {"status": "success", "data": {"matched_count": result.matched_count, "modified_count": result.modified_count}}

        elif query_type == "update_many":
            result = users_collection.update_many(query_params.get("filter", {}), query_params.get("update", {}))
            return {"status": "success", "data": {"matched_count": result.matched_count, "modified_count": result.modified_count}}

        elif query_type == "delete_one":
            result = users_collection.delete_one(query_params.get("filter", {}))
            return {"status": "success", "data": {"deleted_count": result.deleted_count}}

        elif query_type == "delete_many":
            result = users_collection.delete_many(query_params.get("filter", {}))
            return {"status": "success", "data": {"deleted_count": result.deleted_count}}

        else:
            return {"status": "error", "message": "Invalid query type."}

    except Exception as e:
        return {"status": "error", "message": str(e)}


assistant.register_for_llm(name="execute_mongo_query", description="Executes MongoDB queries.")(execute_mongo_query)
user_proxy.register_for_execution(name="execute_mongo_query")(execute_mongo_query)


def process_user_input():
    user_proxy.initiate_chat(assistant, message="Hi, I'm ready to help you with MongoDB operations. Tell me what you want to do (e.g., add user, find users, update user, delete user).")

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
                print("Assistant:", query) # Print the query for debugging

                result = execute_mongo_query(query.get("query_type"), query.get("query_params", {}))
                print("Result:", result) # Print the result of query execution

                if result.get("status") == "success":
                    print("Assistant: Operation successful.")
                    if "data" in result and result["data"]:
                        print("Data:", result["data"])
                else:
                    print(f"Assistant: Error: {result.get('message')}")

            except json.JSONDecodeError as e:
                print(f"Assistant: Invalid JSON returned by assistant: {content}. Error: {e}")
            except Exception as e:
                print(f"Assistant: An error occurred: {e}")
        else:
            print("Assistant: No content received from assistant.")

    print("Conversation ended.")


process_user_input()
