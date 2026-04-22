# Antigravity — Agentic AI Coding Assistant

*Document created to demonstrate local file-writing capabilities.*

Antigravity is a tool developed by Google DeepMind. It functions as a powerful, semi-autonomous coding agent deeply integrated with the local machine space. Below is an overview of its fundamental technical stack and workflow.

---

## The Antigravity Stack & Architecture

### 1. The "Brain" (The Core Model)
At its core, Antigravity is typically powered by a large language model from the Google Gemini family (e.g., **Gemini 3.1 Pro**).
- **Capabilities**: Beyond just reasoning and conversation, the model is fine-tuned for "Agentic Coding." It is trained to iteratively plan, use tools, read outputs, self-correct, and maintain context over long, complex coding sessions instead of just writing single snippets of code.

### 2. The App Data & Context Layer (The Memory)
The agent maintains context about the workspace by saving and reading states from a specific hidden data directory (`~/.gemini/antigravity`).
- **Conversation State**: Stores a "brain" folder containing unique session logs.
- **Artifacts**: Dedicated space for structural reports like `implementation_plan.md` or `task.md`.
- **System Information Wrapper**: Along with every user message, the local client silently injects highly relevant metadata. The agent always knows:
  - Which file the user has actively open in their IDE.
  - Exactly what line the cursor is resting on.
  - The local timestamp.
  - Which browser tabs are currently active in the user's workspace.

### 3. The Tool Layer (The Hands)
Antigravity is an *Agent*, meaning it executes functions against the local environment using a defined API.
- **File System Tools**: Tools like `list_dir`, `view_file`, `replace_file_content`, and `write_to_file` allow it to read and directly manipulate the local codebase securely.
- **Terminal Execution**: Access to a secure shell to run compilers, git commands, and python scripts, including background task monitoring and interactive REPL inputs.
- **Browser Sub-Agent**: Can spin up a headless "sub-agent" to test interactive web apps by clicking buttons, typing in forms, taking DOM snapshots, and recording WebP videos to report back.
- **Search Capabilities**: Built-in access to web searching and local AST-aware file grep searching.

### 4. The Orchestrator (The Planner)
To prevent destructive actions, the framework enforces a "Planning Mode" state machine for complex requests.
- **Phase 1**: Exhaustive codebase research (Read-only).
- **Phase 2**: Generation of an `implementation_plan.md` artifact.
- **Phase 3**: Hard-stop execution until the user explicitly approves the design document.
- **Phase 4**: Execution and local file modification.

---

## Example Request Lifecycle
1. The user sends a standard chat message (e.g., asking for a git status).
2. The local client bundles the text with active metadata (like what file is open) and pings the Google Gemini infrastructure.
3. The language model evaluates the prompt and generates a strict API `tool_call` instead of conversational text.
4. The local client receives the payload and securely executes the function (e.g., spawning a bash terminal to run `git status`).
5. Standard output is captured and sent back to the model.
6. The model synthesizes the raw terminal output into a friendly response, which is finally sent to the chat UI.
