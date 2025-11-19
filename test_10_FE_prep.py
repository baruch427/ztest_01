import random
import requests
import sys
import uuid

# --- Configuration ---
URLS = {
    "test": "http://localhost:8000",
    "live": "https://wisdom-pool-serve-02.firebaseapp.com",
}

BASE_URL = ""
API_V1_URL = ""

# Test user ID
TEST_USER_ID = "fe_test_user_001"
CREATOR_ID = "fe_test_creator_001"


def set_environment(env="test"):
    """Sets the global URLs based on the chosen environment."""
    global BASE_URL, API_V1_URL
    BASE_URL = URLS.get(env, URLS["test"])
    API_V1_URL = f"{BASE_URL}/api/v1"
    print(f"--- Setting up test data for {env.upper()} environment ---")
    print(f"Base URL: {BASE_URL}\n")


def create_pool():
    """Creates the FE_TEST pool."""
    print("--- Creating FE_TEST pool ---")
    pool_data = {
        "pool_content": {
            "title": "FE_TEST",
            "description": "Frontend testing pool with sample streams and drops"
        },
        "creator_id": CREATOR_ID,
    }
    response = requests.post(f"{API_V1_URL}/pools", json=pool_data)
    response.raise_for_status()
    pool_id = response.json()["pool_id"]
    print(f"Created pool: {pool_id}\n")
    return pool_id


def create_stream(pool_id, title, description, category="General"):
    """Creates a stream in the pool."""
    stream_data = {
        "stream_content": {
            "title": title,
            "description": description,
            "category": category
        },
        "pool_id": pool_id,
        "creator_id": CREATOR_ID,
    }
    response = requests.post(f"{API_V1_URL}/streams", json=stream_data)
    response.raise_for_status()
    stream_id = response.json()["stream_id"]
    print(f"Created stream: '{title}' ({stream_id})")
    return stream_id


def add_drops_to_stream(stream_id, drops_content):
    """Adds multiple drops to a stream."""
    drops_data = {
        "drops": drops_content,
        "creator_id": CREATOR_ID,
    }
    response = requests.post(
        f"{API_V1_URL}/streams/{stream_id}/drops",
        json=drops_data
    )
    response.raise_for_status()
    result = response.json()
    drop_ids = [d["drop_id"] for d in result.get("drops", [])]
    placement_ids = [d["placement_id"] for d in result.get("drops", [])]
    print(f"  Added {len(drop_ids)} drops")
    return drop_ids, placement_ids


def update_user_progress(pool_id, stream_id, drop_id, placement_id):
    """Updates user progress for a specific drop."""
    progress_data = {
        "pool_id": pool_id,
        "stream_id": stream_id,
        "drop_id": drop_id,
        "placement_id": placement_id
    }
    response = requests.post(
        f"{API_V1_URL}/user/progress",
        json=progress_data,
        headers={"X-User-Id": TEST_USER_ID}
    )
    response.raise_for_status()


def create_test_data():
    """Creates the complete test data structure."""
    
    # Stream definitions with their drops
    streams_data = [
        {
            "title": "Introduction to Mindfulness",
            "description": "A beginner's guide to mindfulness meditation",
            "category": "Wellness",
            "drops": [
                {"title": "What is Mindfulness?", "text": "Mindfulness is the practice of being present in the moment, aware of where we are and what we're doing."},
                {"title": "The Science Behind It", "text": "Research shows mindfulness can reduce stress, improve focus, and enhance emotional regulation."},
                {"title": "Starting Your Practice", "text": "Begin with just 5 minutes a day. Find a quiet space and focus on your breath."},
                {"title": "Common Obstacles", "text": "It's normal for your mind to wander. The practice is in gently bringing your attention back."},
                {"title": "Building Consistency", "text": "Try practicing at the same time each day to build a sustainable habit."},
            ]
        },
        {
            "title": "The Art of Sourdough Baking",
            "description": "Master the craft of making artisan sourdough bread",
            "category": "Cooking",
            "drops": [
                {"title": "Creating Your Starter", "text": "Mix equal parts flour and water, and let nature do the work. Feed it daily for a week."},
                {"title": "Understanding Fermentation", "text": "Wild yeast and bacteria work together to create the complex flavors of sourdough."},
                {"title": "The Perfect Dough", "text": "Hydration level is key. Start with 70% and adjust based on your flour."},
                {"title": "Folding Techniques", "text": "Stretch and fold every 30 minutes during bulk fermentation to develop gluten structure."},
                {"title": "Shaping Your Loaf", "text": "Tension on the surface is crucial for a good rise. Practice makes perfect."},
                {"title": "Scoring and Baking", "text": "A sharp blade and confident cuts will give you beautiful ear formation."},
                {"title": "Troubleshooting Common Issues", "text": "Dense crumb? Could be under-fermentation. Spread too much? Likely over-proofed."},
            ]
        },
        {
            "title": "Climate Action for Individuals",
            "description": "Practical steps to reduce your carbon footprint",
            "category": "Environment",
            "drops": [
                {"title": "Understanding Your Impact", "text": "The average person produces about 4 tons of CO2 per year. Let's break that down."},
                {"title": "Transportation Choices", "text": "Switching to public transit, biking, or electric vehicles can cut emissions by 30-40%."},
                {"title": "Diet and Climate", "text": "Plant-based meals have a fraction of the carbon footprint of meat-heavy diets."},
                {"title": "Energy at Home", "text": "LED bulbs, better insulation, and smart thermostats make a real difference."},
                {"title": "The Power of Collective Action", "text": "Individual choices matter, but systemic change requires community organizing and advocacy."},
                {"title": "Supporting Green Businesses", "text": "Your purchasing decisions send market signals. Choose companies committed to sustainability."},
            ]
        },
        {
            "title": "Introduction to Quantum Computing",
            "description": "Understanding the fundamentals of quantum mechanics in computing",
            "category": "Technology",
            "drops": [
                {"title": "Classical vs Quantum", "text": "Classical bits are 0 or 1. Quantum bits (qubits) can be both simultaneously."},
                {"title": "Superposition Explained", "text": "A qubit exists in all possible states until measured. This enables massive parallelism."},
                {"title": "Entanglement", "text": "When qubits become entangled, measuring one instantly affects the other, regardless of distance."},
                {"title": "Quantum Gates", "text": "Like classical logic gates, but operating on probability amplitudes in Hilbert space."},
                {"title": "Current Limitations", "text": "Decoherence and error rates remain major challenges. We're in the NISQ era."},
                {"title": "Real-World Applications", "text": "Drug discovery, cryptography, optimization problems—quantum computers excel at specific tasks."},
                {"title": "The Race for Quantum Supremacy", "text": "Google, IBM, and others are competing to build practical quantum computers."},
                {"title": "Learning Resources", "text": "IBM's Qiskit and Microsoft's Q# provide accessible ways to start programming quantum algorithms."},
            ]
        },
        {
            "title": "Urban Gardening Basics",
            "description": "Growing food in small spaces",
            "category": "Gardening",
            "drops": [
                {"title": "Assessing Your Space", "text": "Even a balcony or windowsill can support herbs, microgreens, or compact vegetables."},
                {"title": "Container Selection", "text": "Drainage is critical. Self-watering containers can make maintenance easier."},
                {"title": "Soil Matters", "text": "Quality potting mix designed for containers will outperform garden soil every time."},
            ]
        }
    ]
    
    # Create pool
    pool_id = create_pool()
    
    # Create streams and add drops
    all_stream_data = []
    for stream_info in streams_data:
        stream_id = create_stream(
            pool_id,
            stream_info["title"],
            stream_info["description"],
            stream_info["category"]
        )
        
        # Prepare drops
        num_drops = len(stream_info["drops"])
        drops_to_add = stream_info["drops"]
        
        # Add drops
        drop_ids, placement_ids = add_drops_to_stream(stream_id, drops_to_add)
        
        all_stream_data.append({
            "stream_id": stream_id,
            "title": stream_info["title"],
            "drop_ids": drop_ids,
            "placement_ids": placement_ids
        })
    
    print("\n--- Creating user progress data ---")
    
    # Simulate user reading patterns:
    # Stream 0 (Mindfulness): Read all 5 drops (completed)
    stream = all_stream_data[0]
    for i in range(len(stream["drop_ids"])):
        update_user_progress(
            pool_id,
            stream["stream_id"],
            stream["drop_ids"][i],
            stream["placement_ids"][i]
        )
    print(f"User completed: {stream['title']}")
    
    # Stream 1 (Sourdough): Read 4 out of 7 drops (partially read)
    stream = all_stream_data[1]
    for i in range(4):
        update_user_progress(
            pool_id,
            stream["stream_id"],
            stream["drop_ids"][i],
            stream["placement_ids"][i]
        )
    print(f"User partially read: {stream['title']} (4/7 drops)")
    
    # Stream 2 (Climate): Read 2 out of 6 drops (started)
    stream = all_stream_data[2]
    for i in range(2):
        update_user_progress(
            pool_id,
            stream["stream_id"],
            stream["drop_ids"][i],
            stream["placement_ids"][i]
        )
    print(f"User started: {stream['title']} (2/6 drops)")
    
    # Stream 3 (Quantum): Not read at all
    print(f"User hasn't started: {all_stream_data[3]['title']}")
    
    # Stream 4 (Urban Gardening): Read 1 out of 3 drops (just peeked)
    stream = all_stream_data[4]
    update_user_progress(
        pool_id,
        stream["stream_id"],
        stream["drop_ids"][0],
        stream["placement_ids"][0]
    )
    print(f"User peeked at: {stream['title']} (1/3 drops)")
    
    print(f"\n--- Test data creation complete! ---")
    print(f"Pool ID: {pool_id}")
    print(f"Created {len(all_stream_data)} streams with varying numbers of drops")
    print(f"Simulated user reading progress for user: {TEST_USER_ID}")
    
    # Test session-sync and river endpoints
    print(f"\n--- Testing session-sync endpoint ---")
    response = requests.get(
        f"{API_V1_URL}/user/session-sync",
        headers={"X-User-Id": TEST_USER_ID}
    )
    response.raise_for_status()
    session_data = response.json()
    print(f"Session sync successful!")
    print(f"Last active context: {session_data.get('last_active_context')}")
    print(f"Has history: {session_data.get('has_history')}")
    
    print(f"\n--- Testing river feed endpoint ---")
    response = requests.get(
        f"{API_V1_URL}/pools/{pool_id}/river",
        headers={"X-User-Id": TEST_USER_ID},
        params={"limit": 10}
    )
    response.raise_for_status()
    river_data = response.json()
    print(f"River feed successful!")
    print(f"Returned {len(river_data.get('streams', []))} streams")
    for stream in river_data.get('streams', []):
        user_progress = stream.get('user_progress', {})
        print(f"  - {stream['content']['title']}: "
              f"last_read={user_progress.get('last_read_placement_id', 'None')}, "
              f"completed={user_progress.get('is_completed', False)}")
    
    print(f"\n--- All tests passed! ---")


def main():
    """Main function to set up test data."""
    # Determine environment
    if "--live" in sys.argv:
        set_environment("live")
    else:
        set_environment("test")
    
    try:
        create_test_data()
    except requests.exceptions.RequestException as e:
        print(f"\n!!! Error occurred: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            try:
                print(f"Response body: {e.response.json()}")
            except ValueError:
                print(f"Response body: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
