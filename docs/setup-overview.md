# Project AI — Tool Setup Overview

> Document created: 2026-04-20
> Author: OpenClaw agent (assisted by Shubham)

---

## The Stack

| Tool | What it is | Role in Project AI |
|------|-----------|-----------------|
| **Ollama** | Local AI runtime on MacBook Pro | Runs the AI models that power the agent (thinking, coding, reading files, running poker scripts) |
| **OpenClaw** | Agent framework / orchestration layer | Routes messages, manages sessions, memory, skills, tools — runs the agent (that's me) on top of Ollama |
| **WhatsApp** | Messaging interface | Daily chat with me from phone. Messages flow through Meta's servers → OpenClaw gateway |
| **Control UI** | Web dashboard (`http://127.0.0.1:18789/`) | Alternative chat interface, file browser, session history |
| **Linear** | Project & issue tracker | Stores Project AI project tasks, phases, milestones, completed work |
| **Linear CLI** | Command-line tool for Linear | Connects OpenClaw to Linear so I can read/write issues on your behalf |

---

## How They Connect

```
You (WhatsApp or Control UI)
         ↓
   OpenClaw (gateway — runs locally)
         ↓
    Me (the agent — powered by Ollama, running locally)
         ↓
   Tools: Linear CLI, file reads, code scripts, Git, etc.
         ↓
  Project AI repo ← hand histories, scripts, reports, docs
  Linear ← task management (at linear.app/mose)
```

**In plain English:**

1. **You** message me on **WhatsApp** (or open **Control UI** in a browser)
2. **OpenClaw** receives it and routes it to me
3. **I** run on **Ollama** — thinking, reading files, running poker scripts, querying Linear
4. **Linear** is my notepad and to-do list — I update it so nothing gets lost
5. **Control UI** is just another door into the same me

No single point of failure — if WhatsApp gateway drops, Control UI still works and vice versa.

---

## What Runs Locally vs Cloud

### Fully local (on your MacBook Pro)
- **Ollama** — AI runtime, all model inference
- **OpenClaw** — agent framework and gateway
- **Me (the agent)** — running on Ollama
- **Project AI repo** — `~/Projects/Project AI/` on this machine
- **Linear CLI** — runs locally, only calls Linear's API when you ask for it

### Cloud-dependent
- **WhatsApp** — Meta's servers (this is unavoidable for WhatsApp messaging)
- **Linear** — Linear's cloud servers (issues and projects stored at `linear.app`)
- **OpenAI API** — an API key is configured in OpenClaw's env vars; it may be used for some plugin or provider features (verify if in active use)

### Privacy note
Your poker hand histories, project notes, and日常 conversation stay on your machine. The only external traffic is WhatsApp metadata (which goes through Meta's servers) and Linear sync (to Linear's cloud).

---

## Current Configuration

- **Default model:** `minimax-m2.7:cloud` via Ollama (196k token context)
- **Secondary models available:** `kimi-k2.5:cloud` (262k ctx), `llama3.2` (131k ctx)
- **Linear workspace:** mose (Shubham Agarwal, admin)
- **Project AI Linear project:** `linear.app/mose/project/poker-ai-e33721cdc012`
- **WhatsApp:** linked to +918447397369
- **Gateway:** `ws://127.0.0.1:18789` (local loopback)
