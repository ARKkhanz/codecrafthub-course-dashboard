# CodeCraftHub

A Python/Flask REST API for tracking developer learning courses.
Course data is stored in courses.json; no database or authentication is needed.

## Features
CRUD operations, automatic IDs, UTC timestamps, input validation,
consistent JSON responses, CORS, atomic file writes, and course statistics.

## Files
- app.py: API, validation, storage, and CORS.
- courses.json: automatically created course data.
- requirements.txt: dependencies.
- test_api.py: automated tests.
- submission_evidence/: curl commands, responses, and test results.

## Install and run
Requires Python 3.10 or newer.
Run these commands from the project folder:

    python3 -m pip install --user virtualenv
    python3 -m virtualenv .venv
    .venv/bin/python -m pip install -r requirements.txt
    .venv/bin/python app.py

On Windows, use .venv\Scripts\python.exe instead of .venv/bin/python.
The API runs at http://localhost:5000.
Keep the server terminal open and test in another terminal.

## Endpoints
- POST /api/courses: create, returns 201.
- GET /api/courses: list, returns 200.
- GET /api/courses/<id>: retrieve, returns 200.
- PUT /api/courses/<id>: update, returns 200.
- DELETE /api/courses/<id>: delete, returns 200.
- GET /api/courses/stats: statistics, returns 200.

POST requires non-empty name, description, target_date, and status strings.
Dates use YYYY-MM-DD and must be real calendar dates.
Statuses: Not Started, In Progress, Completed.
PUT accepts a non-empty subset of editable fields.
ID and created_at are generated automatically and cannot be changed.

## Examples
Create:

    curl -i -X POST http://localhost:5000/api/courses -H 'Content-Type: application/json' -d '{"name":"Python Basics","description":"Learn Python","target_date":"2026-12-31","status":"Not Started"}'

Read:

    curl -i http://localhost:5000/api/courses
    curl -i http://localhost:5000/api/courses/1

Update:

    curl -i -X PUT http://localhost:5000/api/courses/1 -H 'Content-Type: application/json' -d '{"status":"In Progress"}'

Delete:

    curl -i -X DELETE http://localhost:5000/api/courses/1

Use the actual ID returned by POST.
Invalid input returns 400; missing courses return 404; storage errors return 500.
Errors use {"success":false,"error":"..."}.

## Tests
Run:

    .venv/bin/python -m unittest -v test_api.py

Tests cover CRUD, persistence, validation, malformed JSON, missing courses,
CORS, corrupt storage, failed writes, and statistics.
Temporary test storage preserves your real course data.

## Troubleshooting
- Missing Flask: install requirements using the virtual environment.
- Missing ensurepip: use the virtualenv installation commands above.
- Port occupied: run PORT=5002 .venv/bin/python app.py and update client URLs.
- Storage error: check JSON and permissions; back up before editing.
- Browser connection: verify the server and reachable API URL.

In Cloud IDE, launch port 5000 to obtain a browser-accessible URL.
Use that URL for a remote Bolt dashboard instead of localhost.

## Scope
This learning server has no authentication.
File locking supports threads in one process, not multiple server processes.
Part 2 adds a dashboard generated using Bolt.new or Bolt.diy.
