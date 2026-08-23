# 📁 05. Workspace Files — Step-by-Step UI Guide

> **Author**: Vijay Donthireddy  
> **Route**: `http://localhost:8000/workspace`  
> **Component Source**: [`webui/src/views/WorkspaceView.jsx`](file:///Users/donthireddy/code/github/agentic-ai/webui/src/views/WorkspaceView.jsx)

---

## 🌟 1. What It Does (Plain English & Analogy)

The **Workspace Files** view is a secure, sandboxed file manager and interactive code editor for the AI agent's dedicated workspace directory (`./workspace`). Both you and the AI agent can read, write, edit, and delete files here safely without granting unrestricted access to your root operating system.

> 💡 **The Real-World Analogy**:  
> Think of this as a shared digital whiteboard and project folder on your office desk. The AI agent can create scratch files, write markdown reports, and save structured code scripts where you can inspect, edit, or delete them in real time.

---

## 🎯 2. Why & How It Helps (Value Proposition)

### "The Challenge Before" vs. "How This Solves It"

| The Challenge Before | How This Solves It |
|---|---|
| **Dangerous OS Access**: Allowing an agent to write anywhere on your computer risks overwriting critical system files. | **Strict Sandboxed Directory Isolation**: Enforces a secure boundary within `./workspace`, rejecting path traversal attacks (`../`). |
| **Ephemeral Agent Outputs**: Agent-generated tables and reports get lost when the chat window is closed. | **Persistent Local Storage**: Files are saved to disk and can be downloaded or previewed at any time. |
| **No Live Visual Feedback**: Users have to switch to terminal or VS Code to see what file the agent created. | **Instant In-Browser Viewer & Editor**: Syntax-highlighted code editor with live Markdown preview rendering. |

---

## 🚀 3. Real-World Step-by-Step Scenario

### Scenario: Creating and Editing a Project Report

```mermaid
flowchart LR
    User["👤 User / Agent"] --> Create["Create file: 'tokyo_itinerary.md'"]
    Create --> View["Inspect in Workspace Explorer"]
    View --> Edit["Edit contents & save"]
    Edit --> Down["Download or use in Agent Chat"]

    classDef cIndigo fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#fff;
    classDef cCyan fill:#082f49,stroke:#0ea5e9,stroke-width:2px,color:#fff;
    classDef cAmber fill:#78350f,stroke:#f59e0b,stroke-width:2px,color:#fff;
    classDef cEmerald fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef cFuchsia fill:#701a75,stroke:#d946ef,stroke-width:2px,color:#fff;

    class User cIndigo;
    class Create cCyan;
    class View cAmber;
    class Edit cEmerald;
    class Down cFuchsia;
```

### Step-by-Step UI Actions:

1. **View Workspace Contents**: In the left file tree, browse existing files (`sample.txt`, `notes.md`, `generated_code.py`).
2. **Create New File**:
   - Click the **`[+ New File]`** button.
   - Enter filename: `trip_plan.md`.
   - Type initial text: `# ✈️ Tokyo Trip Plan\n- Day 1: Shibuya & Shinjuku`.
   - Click **`Save File`**.
3. **Inspect & Edit**:
   - Click any file from the list to view its contents in the editor.
   - Modify the text and click **`💾 Save Changes`**.
4. **Delete or Download**:
   - Click the **`🗑️ Delete`** icon to remove obsolete scratch files.
   - Or click **`⬇️ Download`** to save the file to your computer.

---

## 😄 4. Witty & Relatable Commentary

> *"Giving an autonomous AI access to your computer without a sandbox is like letting a robot vacuum roam your house with a laser chainsaw attached. Our Workspace sandbox keeps the agent happily vacuuming in its own room!"*

---

## 💻 5. Under-the-Hood Code & API Endpoints

- **List Files Endpoint**: `GET /api/workspace/files`
- **Read File Endpoint**: `GET /api/workspace/files/{filename}`
- **Write File Endpoint**: `POST /api/workspace/files`
- **Delete File Endpoint**: `DELETE /api/workspace/files/{filename}`
- **Tool Implementation**: [`mcp_server/tools/file_tools.py`](file:///Users/donthireddy/code/github/agentic-ai/mcp_server/tools/file_tools.py)
