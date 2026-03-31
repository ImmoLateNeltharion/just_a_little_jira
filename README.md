# Simple Jira

Minimal task tracker with comments and Q&A.

## Quick Start (Docker)

```bash
cd simple-jira
docker compose up -d --build
```

Open http://localhost:5050

## Stop

```bash
docker compose down
```

Data persists in a Docker volume (`jira-data`). To wipe it:

```bash
docker compose down -v
```

## Run without Docker

```bash
cd simple-jira
pip install -r requirements.txt
python app.py
```

Open http://localhost:5050

## Features

- Create / edit / delete tasks
- Change status: Open → In Progress → Done
- Filter tasks by status
- Add progress comments
- Ask questions with answer section
