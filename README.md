
### Explanation:
- **User Proxy Agent:** Receives user input and initiates the conversation.
- **Query Writer Agent:** Uses the LLM to generate MongoDB queries.
- **Local Executor Agent:** Executes the queries using `pymongo`.
- **MongoDB:** Stores, updates, deletes, or retrieves data.
- **Response:** Flows back from MongoDB to the user via the agents.

