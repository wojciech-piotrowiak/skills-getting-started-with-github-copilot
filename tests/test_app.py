"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    })


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirects_to_index(self, client):
        """Test that root path redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_success(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data

    def test_get_activities_structure(self, client):
        """Test that activities have correct structure"""
        response = client.get("/activities")
        data = response.json()
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]

    def test_signup_adds_participant(self, client):
        """Test that signup actually adds participant to the activity"""
        client.post("/activities/Chess Club/signup?email=alice@mergington.edu")
        response = client.get("/activities")
        data = response.json()
        assert "alice@mergington.edu" in data["Chess Club"]["participants"]

    def test_signup_duplicate_email(self, client):
        """Test that signing up twice with same email fails"""
        email = "duplicate@mergington.edu"
        client.post(f"/activities/Chess Club/signup?email={email}")
        response = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()

    def test_signup_nonexistent_activity(self, client):
        """Test signup for activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_signup_url_encoding(self, client):
        """Test signup with URL encoded activity name"""
        response = client.post(
            "/activities/Programming%20Class/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/signup endpoint"""

    def test_remove_participant_success(self, client):
        """Test successful removal of a participant"""
        response = client.delete(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "michael@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]

    def test_remove_participant_actually_removes(self, client):
        """Test that deletion actually removes participant from activity"""
        client.delete("/activities/Chess Club/signup?email=michael@mergington.edu")
        response = client.get("/activities")
        data = response.json()
        assert "michael@mergington.edu" not in data["Chess Club"]["participants"]

    def test_remove_participant_not_signed_up(self, client):
        """Test removing participant who isn't signed up"""
        response = client.delete(
            "/activities/Chess Club/signup?email=notsignedup@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"].lower()

    def test_remove_participant_nonexistent_activity(self, client):
        """Test removing participant from activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestActivityCapacity:
    """Tests for activity capacity constraints"""

    def test_activity_has_max_participants(self, client):
        """Test that activities have max_participants field"""
        response = client.get("/activities")
        data = response.json()
        for activity in data.values():
            assert "max_participants" in activity
            assert isinstance(activity["max_participants"], int)
            assert activity["max_participants"] > 0

    def test_can_fill_activity_to_capacity(self, client):
        """Test that we can add participants up to max capacity"""
        # Get current state
        response = client.get("/activities")
        data = response.json()
        chess_club = data["Chess Club"]
        current_count = len(chess_club["participants"])
        max_participants = chess_club["max_participants"]
        spots_available = max_participants - current_count

        # Add participants up to capacity
        for i in range(spots_available):
            response = client.post(
                f"/activities/Chess Club/signup?email=student{i}@mergington.edu"
            )
            assert response.status_code == 200

        # Verify we're at capacity
        response = client.get("/activities")
        data = response.json()
        assert len(data["Chess Club"]["participants"]) == max_participants


class TestEndToEndWorkflow:
    """End-to-end workflow tests"""

    def test_signup_and_remove_workflow(self, client):
        """Test complete workflow: signup then remove"""
        email = "workflow@mergington.edu"
        activity = "Programming Class"

        # Initial count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])

        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200

        # Verify added
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count + 1
        assert email in response.json()[activity]["participants"]

        # Remove
        response = client.delete(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200

        # Verify removed
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count
        assert email not in response.json()[activity]["participants"]

    def test_multiple_activities_independent(self, client):
        """Test that signing up for multiple activities works independently"""
        email = "multisport@mergington.edu"

        # Sign up for multiple activities
        response1 = client.post(f"/activities/Chess Club/signup?email={email}")
        response2 = client.post(f"/activities/Programming Class/signup?email={email}")
        response3 = client.post(f"/activities/Gym Class/signup?email={email}")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200

        # Verify in all activities
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]
        assert email in data["Programming Class"]["participants"]
        assert email in data["Gym Class"]["participants"]
