Bronze Tier – Personal AI Employee (Digital FTE)

This project implements the Bronze Tier of the Personal AI Employee Hackathon 2026.
The goal is to build a minimum viable Digital FTE (Full-Time Equivalent) using a local-first architecture powered by:

Claude Code as the reasoning engine

Obsidian as the knowledge base and dashboard

Python Watcher as the perception layer

🧠 Concept

The AI Employee works using a simple but powerful flow:

Perception → Reasoning → Action

A Watcher script monitors inputs (e.g., Gmail or local files).

When a new item appears, it creates a markdown file in /Needs_Action.

Claude Code reads the file using Agent Skills.

The task is processed.

The Dashboard is updated.

The file is moved to /Done.

This transforms Claude from a chatbot into a task-processing agent.

📂 Implemented Features (Bronze Scope)

✔ Obsidian Vault structure

✔ /Needs_Action, /Done, /Inbox, /Logs folders

✔ Working Watcher (Gmail or File System)

✔ Dashboard.md auto-updates

✔ Agent Skills-based task processing

✔ Ralph Loop compatibility

🎯 Objective

The objective of this Bronze Tier implementation is to prove that:

A local AI agent can autonomously process structured tasks using markdown files as a control interface.

This is the foundation for higher tiers (Silver/Gold), where external integrations and MCP servers will be added.

💡 Key Learning