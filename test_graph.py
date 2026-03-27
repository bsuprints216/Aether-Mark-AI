import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.graphs.orchestrator import create_aethermark_graph
from app.schemas.state import SocialState, BrandProfile

def test_graph_compilation():
    print("Testing AetherMark AI Graph Compilation...")
    try:
        graph = create_aethermark_graph()
        print("✅ Graph compiled successfully!")
        
        # Test state initialization
        brand = BrandProfile(
            brand_name="Test Brand",
            target_audience="Developers",
            content_pillars=["AI", "Python"],
            active_platforms=["twitter", "linkedin"]
        )
        state = SocialState(
            client_id="client_001",
            brand_profile=brand,
            task_type="campaign"
        )
        print(f"✅ State initialized for task: {state.task_type}")
        
    except Exception as e:
        print(f"❌ Error during graph setup: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_graph_compilation()
