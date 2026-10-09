import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.config["DATA_FILE"] = Path(__file__).with_name("courses.json")
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
lock = RLock()
FIELDS = ("name", "description", "target_date", "status")
STATUSES = ("Not Started", "In Progress", "Completed")


class StorageError(Exception):
    pass


def save_courses(courses):
    """Write atomically so failed writes do not damage the existing file."""
    path = Path(app.config["DATA_FILE"])
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = stream.name
            json.dump(courses, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise StorageError("Unable to save course data.") from error
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def validate(data, partial=False):
    """Check required strings, permitted status, and real calendar dates."""
    for field in FIELDS:
        if field not in data:
            if partial:
                continue
            return f"Missing required field: {field}"
        if not isinstance(data[field], str) or not data[field].strip():
            return f"{field} must be a non-empty string"
    if "status" in data and data["status"] not in STATUSES:
        return "Status must be one of: " + ", ".join(STATUSES)
    if "target_date" in data:
        value = data["target_date"]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return "target_date must be a valid date in YYYY-MM-DD format"
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return "target_date must be a valid date in YYYY-MM-DD format"
    return None


def load_courses():
    """Create missing storage and report corrupt data without overwriting it."""
    path = Path(app.config["DATA_FILE"])
    try:
        if not path.exists():
            save_courses([])
        courses = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(courses, list):
            raise ValueError("Expected an array")
        ids = set()
        for course in courses:
            if not isinstance(course, dict):
                raise ValueError("Invalid record")
            course_id = course.get("id")
            if type(course_id) is not int or course_id < 1 or course_id in ids:
                raise ValueError("Invalid ID")
            ids.add(course_id)
            if validate(course) or not isinstance(course.get("created_at"), str):
                raise ValueError("Invalid course fields")
        return courses
    except (OSError, ValueError) as error:
        raise StorageError("Unable to read course data; check courses.json.") from error


def get_next_id(courses):
    return max((course["id"] for course in courses), default=0) + 1


def failure(message, status):
    return jsonify(success=False, error=message), status


def read_body(partial=False):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, "Request body must be a valid JSON object"
    unknown = set(data) - set(FIELDS)
    if unknown:
        return None, "Unknown or read-only fields: " + ", ".join(sorted(unknown))
    if partial and not data:
        return None, "Provide at least one field to update"
    return data, validate(data, partial)


@app.after_request
def cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.errorhandler(StorageError)
def storage_error(error):
    return failure(str(error), 500)


@app.errorhandler(HTTPException)
def http_error(error):
    return failure(error.description, error.code)


@app.get("/api/courses")
def get_all_courses():
    with lock:
        courses = load_courses()
    return jsonify(success=True, count=len(courses), courses=courses), 200


@app.get("/api/courses/<int:course_id>")
def get_course(course_id):
    with lock:
        course = next((c for c in load_courses() if c["id"] == course_id), None)
    if course is None:
        return failure("Course not found", 404)
    return jsonify(success=True, course=course), 200


@app.post("/api/courses")
def add_course():
    data, error = read_body()
    if error:
        return failure(error, 400)
    with lock:
        courses = load_courses()
        course = {
            "id": get_next_id(courses),
            **{field: data[field].strip() for field in FIELDS},
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        }
        courses.append(course)
        save_courses(courses)
    return jsonify(success=True, message="Course added successfully", course=course), 201


@app.put("/api/courses/<int:course_id>")
def update_course(course_id):
    data, error = read_body(partial=True)
    if error:
        return failure(error, 400)
    with lock:
        courses = load_courses()
        course = next((c for c in courses if c["id"] == course_id), None)
        if course is None:
            return failure("Course not found", 404)
        for field, value in data.items():
            course[field] = value.strip()
        save_courses(courses)
    return jsonify(success=True, message="Course updated successfully", course=course), 200


@app.delete("/api/courses/<int:course_id>")
def delete_course(course_id):
    with lock:
        courses = load_courses()
        course = next((c for c in courses if c["id"] == course_id), None)
        if course is None:
            return failure("Course not found", 404)
        courses.remove(course)
        save_courses(courses)
    return jsonify(
        success=True, message="Course deleted successfully", deleted_course=course
    ), 200


@app.get("/api/courses/stats")
def get_stats():
    with lock:
        courses = load_courses()
    return jsonify(
        success=True,
        total=len(courses),
        by_status={s: sum(c["status"] == s for c in courses) for s in STATUSES},
    ), 200


if __name__ == "__main__":
    with lock:
        load_courses()
    port = int(os.environ.get("PORT", "5000"))
    print("CodeCraftHub API is starting...")
    print(f"Data will be stored in: {app.config['DATA_FILE']}")
    print(f"API will be available at: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
