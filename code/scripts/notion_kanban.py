#!/usr/bin/env python3
"""Notion Kanban integration for poker_ai project."""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
DATABASE_ID = "9712ae00-067d-47af-8ba2-e8e73b9e0f6e"
BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def make_request(endpoint: str, method: str = "GET", body: Optional[dict] = None) -> dict:
    """Make a request to the Notion API."""
    url = f"{BASE_URL}/{endpoint}"
    data = json.dumps(body).encode("utf-8") if body else None
    
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {NOTION_TOKEN}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Notion-Version", NOTION_VERSION)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"Notion API error {e.code}: {error_body}", file=sys.stderr)
        return {"error": e.code, "message": error_body}
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return {"error": str(e)}


def query_database(status: Optional[str] = None) -> list:
    """Query all pages in the database, optionally filtered by status."""
    body = {
        "filter": {
            "property": "Status",
            "select": {"equals": status}
        }
    } if status else {}
    
    result = make_request(f"databases/{DATABASE_ID}/query", method="POST", body=body)
    return result.get("results", []) if "results" in result else []


def create_task(title: str, status: str = "Backlog", priority: str = "Medium", notes: str = "") -> dict:
    """Create a new task in the Notion database."""
    body = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "Status": {"select": {"name": status}},
            "Priority": {"select": {"name": priority}},
        }
    }
    if notes:
        body["properties"]["Notes"] = {"rich_text": [{"text": {"content": notes}}]}
    
    return make_request("pages", method="POST", body=body)


def update_task_status(page_id: str, new_status: str) -> dict:
    """Update the status of a task."""
    body = {
        "properties": {
            "Status": {"select": {"name": new_status}}
        }
    }
    return make_request(f"pages/{page_id}", method="PATCH", body=body)


def list_tasks(status: Optional[str] = None) -> list:
    """List all tasks, optionally filtered by status."""
    tasks = query_database(status)
    return tasks


def format_task(task: dict) -> str:
    """Format a task for display."""
    props = task.get("properties", {})
    name = props.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Untitled")
    status = props.get("Status", {}).get("select", {}).get("name", "Unknown")
    priority = props.get("Priority", {}).get("select", {}).get("name", "Unknown")
    created = task.get("created_time", "")[:10]
    return f"  [{status}] {name} (Priority: {priority}) - Created: {created}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python notion_kanban.py <command> [args]")
        print("Commands:")
        print("  list [status]           - List all tasks, optionally filter by status (Backlog/In Progress/Done)")
        print("  add <title> [status] [priority] [notes] - Add a new task")
        print("  move <page_id> <new_status> - Move a task to a new status")
        print("  test                   - Test the Notion connection")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "test":
        print("Testing Notion connection...")
        result = make_request(f"databases/{DATABASE_ID}")
        if "error" in result:
            print(f"❌ Connection failed: {result.get('message', result.get('error'))}")
        else:
            print("✅ Connected successfully!")
            title = result.get("title", [])
            if title:
                db_name = title[0].get("text", {}).get("content", "Unknown")
                print(f"Database: {db_name}")
    
    elif cmd == "list":
        status_filter = sys.argv[2] if len(sys.argv) > 2 else None
        print(f"\n📋 Tasks {f'({status_filter})' if status_filter else '(all)'}:")
        tasks = list_tasks(status_filter)
        if not tasks:
            print("  (no tasks found)")
        else:
            for task in tasks:
                print(format_task(task))
    
    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: notion_kanban.py add <title> [status] [priority] [notes]")
            sys.exit(1)
        title = sys.argv[2]
        status = sys.argv[3] if len(sys.argv) > 3 else "Backlog"
        priority = sys.argv[4] if len(sys.argv) > 4 else "Medium"
        notes = sys.argv[5] if len(sys.argv) > 5 else ""
        result = create_task(title, status, priority, notes)
        if "error" in result:
            print(f"❌ Failed to create task: {result.get('message')}")
        else:
            print(f"✅ Task created: {title}")
    
    elif cmd == "move":
        if len(sys.argv) < 4:
            print("Usage: notion_kanban.py move <page_id> <new_status>")
            sys.exit(1)
        page_id = sys.argv[2]
        new_status = sys.argv[3]
        result = update_task_status(page_id, new_status)
        if "error" in result:
            print(f"❌ Failed to update task: {result.get('message')}")
        else:
            print(f"✅ Task moved to {new_status}")
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
