from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging
from app.schemas.state import BrandProfile, SocialState
from app.graphs.orchestrator import create_aethermark_graph

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("AetherMark")

app = FastAPI(
    title="AetherMark AI Enterprise API", 
    description="Cognitive Marketing Orchestration Engine", 
    version="3.0.0"
)

# Enable CORS for the frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- FAANG Infrastructure Abstraction ---
class PersistentStateManager:
    """Pluggable state storage abstraction (Redis/Postgres ready)"""
    def __init__(self):
        self._brand_db = {}
        self._pending_approvals = {}

    def save_brand(self, client_id: str, profile: BrandProfile):
        self._brand_db[client_id] = profile

    def get_brand(self, client_id: str) -> Optional[BrandProfile]:
        return self._brand_db.get(client_id)

    def stage_approval(self, approval_id: str, state: dict):
        self._pending_approvals[approval_id] = state

    def fetch_approval(self, approval_id: str) -> Optional[dict]:
        return self._pending_approvals.pop(approval_id, None)

    def health(self) -> dict:
        return {
            "brands_loaded": len(self._brand_db),
            "approvals_pending": len(self._pending_approvals)
        }

STATE_STORE = PersistentStateManager()

class CampaignRequest(BaseModel):
    client_id: str
    task_type: str = "campaign"

@app.get("/health")
async def health_check():
    return {"status": "online", "system": "AetherMark AI"}

@app.post("/client/profile")
async def create_profile(profile: BrandProfile, client_id: str):
    STATE_STORE.save_brand(client_id, profile)
    return {"message": "Profile created", "client_id": client_id}

@app.post("/run")
async def run_automation(request: CampaignRequest):
    brand = STATE_STORE.get_brand(request.client_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    # Initialize state as a dictionary for LangGraph compatibility or a controlled BaseModel
    initial_values = {
        "client_id": request.client_id,
        "brand_profile": brand,
        "task_type": request.task_type,
        "messages": [],
        "requires_human_approval": False
    }
    
    # Run the graph
    try:
        graph = create_aethermark_graph()
        result = graph.invoke(initial_values)
        
        # Check if human intervention is needed
        if result.get("requires_human_approval"):
            import uuid
            approval_id = str(uuid.uuid4())
            STATE_STORE.stage_approval(approval_id, result)
            return {
                "status": "awaiting_approval",
                "approval_id": approval_id,
                "reason": result.get("escalation_reason"),
                "content": result.get("generated_content")
            }
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/approve/{approval_id}")
async def approve_content(approval_id: str):
    state = STATE_STORE.fetch_approval(approval_id)
    if not state:
        raise HTTPException(status_code=404, detail="Approval request not found")
    # Resume by calling the scheduler node directly or restarting graph with approved status
    state["requires_human_approval"] = False
    state["task_type"] = "scheduling" # Set task to scheduling to skip previous steps
    
    try:
        graph = create_aethermark_graph()
        result = graph.invoke(state)
        return {"message": "Content approved and scheduled", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reject/{approval_id}")
async def reject_content(approval_id: str, feedback: str = "Rejected by human"):
    state = STATE_STORE.fetch_approval(approval_id)
    if not state:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return {"message": "Content rejected", "feedback": feedback}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
