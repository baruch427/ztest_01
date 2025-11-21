import json
import os
import sys
import uuid
from datetime import datetime

import requests

# --- Configuration ---
URLS = {
    "test": "http://localhost:8000",
    "live": "https://wisdom-pool-server-3473lz5ika-nw.a.run.app",
}
STATE_FILE = "test_state.json"

# These will be set based on the environment
BASE_URL = ""
API_V1_URL = ""


def set_environment(env="test"):
    """Sets the global URLs based on the chosen environment."""
    global BASE_URL, API_V1_URL
    BASE_URL = URLS.get(env, URLS["test"])
    API_V1_URL = f"{BASE_URL}/api/v1"
    print(f"--- Running tests against {env.upper()} environment: {BASE_URL} ---\n")


def save_state(data):
    """Saves the current test state to a file."""
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Progress saved. Last successful step: {data.get('last_step')}")


def load_state():
    """Loads the test state from a file if it exists."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}  # Return empty state if file is corrupted
    return {}


def generate_creator_id():
    """Generates a unique creator ID."""
    return f"user_{uuid.uuid4()}"


def clear_server_logs():
    """Clears the in-memory logs on the server."""
    print("--- Clearing server logs for a fresh run ---")
    try:
        response = requests.delete(f"{BASE_URL}/logs/clear")
        response.raise_for_status()
        print("Server logs cleared successfully.\n")
    except requests.exceptions.RequestException as e:
        print(f"Could not clear server logs: {e}\n")


def dump_server_logs():
    """Fetches and prints the in-memory logs from the server."""
    print("\n" + "="*20 + " FETCHING SERVER LOGS " + "="*20)
    try:
        log_response = requests.get(f"{BASE_URL}/logs")
        log_response.raise_for_status()
        print(log_response.text)
        print("="*62 + "\n")
    except requests.exceptions.RequestException as log_e:
        print(f"Failed to fetch server logs: {log_e}")


def test_full_workflow():
    """Runs the full API workflow, resuming from the last saved state."""
    # Load previous state or initialize a new one
    state = load_state()
    pool_id = state.get("pool_id")
    stream_id = state.get("stream_id")
    drop_records = state.get("drop_records")
    drop_ids = state.get("drop_ids", [])
    if not drop_records and drop_ids:
        # Backwards compatibility for older state files
        drop_records = [
            {"drop_id": d_id, "placement_id": None}
            for d_id in drop_ids
        ]
    elif not drop_records:
        drop_records = []
    last_step = state.get("last_step", "")
    creator_id = state.get("creator_id", generate_creator_id())
    user_id = state.get("user_id", generate_creator_id())

    # If starting a fresh run, clear the logs on the server
    if not state:
        clear_server_logs()

    # Always save the creator_id and user_id
    if "creator_id" not in state:
        state["creator_id"] = creator_id
    if "user_id" not in state:
        state["user_id"] = user_id
        save_state(state)

    def refresh_drop_records_from_server():
        """Fetch drop records (with placement IDs) and persist them."""
        nonlocal drop_records
        if not stream_id:
            return
        response = requests.get(
            f"{API_V1_URL}/streams/{stream_id}/drops",
            params={"limit": 50}
        )
        response.raise_for_status()
        drops_payload = response.json().get("drops", [])
        if not drops_payload:
            return
        drop_records = [
            {
                "drop_id": d["drop_id"],
                "placement_id": d.get("placement_id"),
            }
            for d in drops_payload
        ]
        state["drop_records"] = drop_records
        state["drop_ids"] = [d["drop_id"] for d in drop_records]
        save_state(state)

    def get_placement_for_drop(target_drop_id):
        """Ensures we have a placement ID for the given drop."""
        for record in drop_records:
            if (
                record["drop_id"] == target_drop_id
                and record.get("placement_id")
            ):
                return record["placement_id"]
        refresh_drop_records_from_server()
        for record in drop_records:
            if (
                record["drop_id"] == target_drop_id
                and record.get("placement_id")
            ):
                return record["placement_id"]
        return None

    try:
        # Step 0: Root Endpoint (always run)
        print("--- 0. Checking root endpoint ---")
        response = requests.get(f"{BASE_URL}/")
        response.raise_for_status()
        root_message = response.json().get("message", "No message returned")
        print(f"Root endpoint healthy: {root_message}\n")

        # Step 1: Health Check (always run)
        print("--- 1. Checking server health ---")
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        health_data = response.json()
        start_ts = health_data["start_time_utc"].replace("Z", "+00:00")
        server_ts = health_data["server_time_utc"].replace("Z", "+00:00")
        start_time = datetime.fromisoformat(start_ts)
        server_time = datetime.fromisoformat(server_ts)
        uptime_minutes = (server_time - start_time).total_seconds() / 60
        print(f"Server is OK. Uptime: {uptime_minutes:.2f} minutes.\n")

        # Step 2: Create and Validate Pool
        if not pool_id:
            print("--- 1. Creating a new pool ---")
            pool_data = {
                "pool_content": {
                    "title": "Test Pool",
                    "description": "A test pool.",
                },
                "creator_id": creator_id,
            }
            response = requests.post(f"{API_V1_URL}/pools", json=pool_data)
            response.raise_for_status()
            pool_id = response.json()["pool_id"]
            state.update({"pool_id": pool_id, "last_step": "create_pool"})
            save_state(state)
            print(f"Pool created with ID: {pool_id}\n")
        else:
            print("--- 1. Pool already exists (skipping creation) ---")
            print(f"Using Pool ID: {pool_id}\n")

        if last_step in ["", "create_pool"]:
            print(f"--- 2. Validating pool {pool_id} ---")
            response = requests.get(f"{API_V1_URL}/pools/{pool_id}")
            response.raise_for_status()
            state.update({"last_step": "validate_pool"})
            save_state(state)
            print(f"Pool {pool_id} validated successfully.\n")

        # Step 3: Create and Validate Stream
        if not stream_id:
            print("--- 3. Creating a new stream ---")
            stream_data = {
                "stream_content": {
                    "title": "Test Stream",
                    "description": "A test stream.",
                },
                "pool_id": pool_id,
                "creator_id": creator_id,
            }
            response = requests.post(f"{API_V1_URL}/streams", json=stream_data)
            response.raise_for_status()
            stream_id = response.json()["stream_id"]
            state.update({
                "stream_id": stream_id,
                "last_step": "create_stream",
            })
            save_state(state)
            print(f"Stream created with ID: {stream_id}\n")
        else:
            print("--- 3. Stream already exists (skipping creation) ---")
            print(f"Using Stream ID: {stream_id}\n")

        if last_step in ["create_pool", "validate_pool", "create_stream"]:
            print(f"--- 4. Validating stream {stream_id} ---")
            response = requests.get(f"{API_V1_URL}/streams/{stream_id}")
            response.raise_for_status()
            state.update({"last_step": "validate_stream"})
            save_state(state)
            print(f"Stream {stream_id} validated successfully.\n")

        # Step 4: Add and Validate Drops
        if len(drop_records) < 3:
            print(f"--- 5. Adding 3 drops to stream {stream_id} ---")
            drops_data = {
                "drops": [
                    {"title": "Drop 1", "text": "This is the first drop."},
                    {"title": "Drop 2", "text": "This is the second drop."},
                    {"title": "Drop 3", "text": "This is the third drop."}
                ],
                "creator_id": creator_id,
            }
            response = requests.post(
                f"{API_V1_URL}/streams/{stream_id}/drops",
                json=drops_data,
            )
            response.raise_for_status()
            new_drops = response.json().get("drops", [])
            drop_records = [
                {
                    "drop_id": d["drop_id"],
                    "placement_id": d.get("placement_id"),
                }
                for d in new_drops
            ]
            drop_ids = [record["drop_id"] for record in drop_records]
            state.update({
                "drop_records": drop_records,
                "drop_ids": drop_ids,
                "last_step": "add_drops"
            })
            save_state(state)
            print(f"3 drops added with IDs: {drop_ids}\n")
        else:
            print("--- 5. Drops already exist (skipping creation) ---")
            print(f"Using Drop IDs: {drop_ids}\n")

        if last_step != "validate_drops":
            print("--- 6. Validating individual drops ---")
            for drop_record in drop_records:
                response = requests.get(
                    f"{API_V1_URL}/drops/{drop_record['drop_id']}"
                )
                response.raise_for_status()
                print(f"Drop {drop_record['drop_id']} validated successfully.")
            state.update({"last_step": "validate_drops"})
            save_state(state)
            print("All drops validated.\n")

        # Step 5: Test User Progress Endpoints
        if last_step != "test_user_progress":
            print("--- 7. Testing user progress endpoints ---")
            
            # First, get user river (should have limited history initially)
            print("Getting initial user river...")
            response = requests.get(
                f"{API_V1_URL}/user/river",
                params={"limit": 30},
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            river_data = response.json()
            initial_records = len(river_data.get("records", []))
            print(f"Initial river records: {initial_records}")
            
            # Update user progress
            print("Updating user progress...")
            target_drop_id = drop_ids[1] if len(drop_ids) > 1 else drop_ids[0]
            placement_id = get_placement_for_drop(target_drop_id)
            if not placement_id:
                raise RuntimeError(
                    "Could not determine placement_id for progress update."
                )
            progress_data = {
                "pool_id": pool_id,
                "stream_id": stream_id,
                "drop_id": target_drop_id,
                "placement_id": placement_id
            }
            response = requests.post(
                f"{API_V1_URL}/user/progress",
                json=progress_data,
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            print("User progress updated successfully.")
            
            # Get user river again (should now reflect the activity)
            print("Getting updated user river...")
            response = requests.get(
                f"{API_V1_URL}/user/river",
                params={"limit": 30},
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            updated_river = response.json()
            touched_streams = [
                r.get("stream_id") for r in updated_river.get("records", [])
            ]
            if stream_id not in touched_streams:
                warning_msg = (
                    "Warning: Updated river does not include the stream we just touched."
                )
                print(warning_msg)
            else:
                print("User river reflects the recent activity.")
            
            state.update({"last_step": "test_user_progress"})
            save_state(state)
            print("User progress tests completed.\n")

        # Step 5: Test Get Drops in Stream
        if last_step != "test_get_drops":
            print("--- 8. Testing get drops in stream endpoint ---")
            response = requests.get(
                f"{API_V1_URL}/streams/{stream_id}/drops",
                params={"limit": 10}
            )
            response.raise_for_status()
            drops_response = response.json()
            drop_count = len(drops_response.get("drops", []))
            print(f"Retrieved {drop_count} drops from stream")
            print(f"Has more: {drops_response.get('has_more')}")
            print(f"Total count: {drops_response.get('total_count')}")
            
            state.update({"last_step": "test_get_drops"})
            save_state(state)
            print("Get drops test completed.\n")

        print("--- Full workflow test completed successfully! ---")

    except requests.exceptions.RequestException as e:
        last_step_name = state.get("last_step", "initial")
        print(f"\n!!! An error occurred during step: '{last_step_name}' !!!")
        print(f"Error: {e}")
        if e.response:
            print(f"Response status code: {e.response.status_code}")
            try:
                print(f"Response body: {e.response.json()}")
            except ValueError:
                print(f"Response body: {e.response.text}")
        
        dump_server_logs()
        sys.exit(1)


if __name__ == "__main__":
    # Determine environment
    if "--live" in sys.argv:
        set_environment("live")
    else:
        set_environment("test")

    # Handle command-line flags
    if "--logs" in sys.argv:
        dump_server_logs()
        sys.exit(0)

    if "--reset" in sys.argv and os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print("Test state has been reset. Starting from the beginning.")

    test_full_workflow()


