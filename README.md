flowchart TD
    User[User Input: "Update Jegan age to 24"] --> UserProxy[User Proxy Agent]
    UserProxy --> QueryWriter[Query Writer Agent]
    QueryWriter -->|Generates MongoDB Query| LocalExecutor[Local Executor Agent]
    LocalExecutor -->|Executes with pymongo| MongoDB[(MongoDB Database)]
    MongoDB -->|Response| LocalExecutor
    LocalExecutor --> UserProxy
    UserProxy -->|Displays Result| User

style User fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px
style UserProxy fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
style QueryWriter fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
style LocalExecutor fill:#fff3e0,stroke:#f57c00,stroke-width:2px
style MongoDB fill:#e0f7fa,stroke:#00838f,stroke-width:2px
```

### Explanation:
- **User Proxy Agent:** Receives user input and initiates the conversation.
- **Query Writer Agent:** Uses the LLM to generate MongoDB queries.
- **Local Executor Agent:** Executes the queries using `pymongo`.
- **MongoDB:** Stores, updates, deletes, or retrieves data.
- **Response:** Flows back from MongoDB to the user via the agents.

You can paste this Mermaid code into platforms like **Markdown Live Preview**, **Mermaid Live Editor**, or **GitHub README** to render the flowchart.
