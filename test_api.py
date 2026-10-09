import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import app, StorageError


class CourseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original = app.config["DATA_FILE"]
        app.config["DATA_FILE"] = Path(self.temp.name) / "courses.json"
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.data = {
            "name": "Python Basics",
            "description": "Learn Python fundamentals",
            "target_date": "2026-12-31",
            "status": "Not Started",
        }

    def tearDown(self):
        app.config["DATA_FILE"] = self.original
        self.temp.cleanup()

    def test_crud_and_persistence(self):
        response = self.client.post("/api/courses", json=self.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["course"]["id"], 1)
        self.assertIn("created_at", response.json["course"])

        self.assertEqual(self.client.get("/api/courses").json["count"], 1)
        self.assertEqual(
            self.client.get("/api/courses/1").json["course"]["name"],
            "Python Basics",
        )

        response = self.client.put(
            "/api/courses/1", json={"status": "In Progress"}
        )
        self.assertEqual(response.status_code, 200)
        saved = json.loads(Path(app.config["DATA_FILE"]).read_text())
        self.assertEqual(saved[0]["status"], "In Progress")

        self.assertEqual(self.client.delete("/api/courses/1").status_code, 200)
        self.assertEqual(self.client.get("/api/courses").json["count"], 0)
        self.assertEqual(self.client.get("/api/courses/1").status_code, 404)

    def test_invalid_fields(self):
        self.assertEqual(
            self.client.post("/api/courses", json={"name": "Incomplete"}).status_code,
            400,
        )
        for changes in (
            {"status": "Invalid"},
            {"target_date": "2026-02-30"},
            {"target_date": "2026-1-01"},
            {"name": " "},
            {"description": 123},
        ):
            response = self.client.post(
                "/api/courses", json={**self.data, **changes}
            )
            self.assertEqual(response.status_code, 400)

        self.client.post("/api/courses", json=self.data)
        for update in ({"status": "Invalid"}, {"id": 99}, {}):
            self.assertEqual(
                self.client.put("/api/courses/1", json=update).status_code, 400
            )

    def test_bad_json_and_missing_course(self):
        response = self.client.post(
            "/api/courses", data="{", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/api/courses/999").status_code, 404)
        self.assertEqual(self.client.delete("/api/courses/999").status_code, 404)
        self.assertEqual(
            self.client.put(
                "/api/courses/999", json={"status": "Completed"}
            ).status_code,
            404,
        )

    def test_cors(self):
        response = self.client.options(
            "/api/courses",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "*")
        self.assertIn("PUT", response.headers["Access-Control-Allow-Methods"])

    def test_corrupt_file_is_preserved(self):
        path = Path(app.config["DATA_FILE"])
        path.write_text("{broken")
        self.assertEqual(self.client.get("/api/courses").status_code, 500)
        self.assertEqual(path.read_text(), "{broken")

    def test_failed_write(self):
        self.client.get("/api/courses")
        with patch("app.save_courses", side_effect=StorageError("Save failed")):
            response = self.client.post("/api/courses", json=self.data)
        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.json["success"])
        self.assertEqual(self.client.get("/api/courses").json["count"], 0)

    def test_statistics(self):
        self.client.post("/api/courses", json=self.data)
        response = self.client.get("/api/courses/stats")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["total"], 1)
        self.assertEqual(response.json["by_status"]["Not Started"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
