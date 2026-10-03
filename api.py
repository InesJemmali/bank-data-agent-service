from fastapi import FastAPI, File, HTTPException, UploadFile
import requests
import time 
from pathlib import Path
from pydantic import BaseModel
from agent_conversation import SYSTEM_PROMPT,  TURN_INSTRUCTION, agent_turn
from step_chat import OLLAMA_HOST, MODEL
import threading
import uuid

DATA_DIR = Path("data")
ALLOWED = {".csv", ".xlsx", ".xls"}
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB 
MAX_SESSION = 50  # conversation kept in RAM




app = FastAPI(title="Local Financial Analysist Agent", description="An advanced financial agent application built with FastAPI.")


def new_message(dataset_path):
    """ The first three messages of a conversation, exactly like reply() builds them. """
    return [
        {"role":"system","content":SYSTEM_PROMPT},
        {"role": "user", "content": f"Dataset path: {dataset_path}. Use this exact path for every tool call."},
        {"role":"assistant", "content":"Hello! I am your financial data analyst assistant. Please ask your question about the dataset, and I will help you analyze it step by step."}   
    ]

def get_session(session_id):
    """ Get or create a session for a given session_id. """
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found. Please start a new conversation.")
    return session    

class StartRequest(BaseModel):
    dataset: str

class Question(BaseModel):
    question: str

class Session:
    """ One conversation: its dataset, its history, and a lock """
    def __init__(self, dataset_path):
        self.dataset = dataset_path.name
        self.messages = new_message(dataset_path)
        self.lock = threading.Lock()
        self.dataset_path = dataset_path.resolve()
        self.last_used = time.time()  # Timestamp of the last activity in this session

sessions : dict[str, Session] = {}

@app.get("/")
def root():
    return {"message": "Welcome to the Financial Agent Advanced App!"}

@app.get("/health")
def health_check():
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags",timeout=5)
        r.raise_for_status()
        pulled = [m["name"] for m in r.json().get("models",[])]
        return {"ollama": "reachable", "chat_model": MODEL, "available_models": pulled}
    except requests.RequestException as e:
        return {"ollama": f"unreachable ({type(e).__name__})","ollama_host":OLLAMA_HOST,"error": str(e), "chat_model": MODEL}

@app.post("/sessions")
def create_session(body: StartRequest):
    """ Create a new session with the specified dataset. """
    path = DATA_DIR / Path(body.dataset).name
    if path.suffix.lower() not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Invalid type. Allowed types: {ALLOWED}")
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Dataset not found: {path}")   
    if len(sessions) >= MAX_SESSION:
        oldest = min(sessions,key=lambda sid: sessions[sid].last_used)    
        del sessions[oldest]
    session_id = uuid.uuid4().hex
    sessions[session_id] = Session(path)
    return {"session_id": session_id, "dataset": path.name}

@app.post("/sessions/{session_id}/ask")
def ask(session_id: str, body: Question):
    """ Ask a question to the agent in a specific session. """
    session = get_session(session_id)
    if not session.lock.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Session is busy. Please try again later.")
    try:
        session.last_used = time.time()
        t0 = time.time()  
        steps = []
        history_length = len(session.messages)
        session.messages.append({"role": "user", "content": f"{body.question}\n{TURN_INSTRUCTION}"})
        try:    
             answer = agent_turn(session.messages, verbose=False, trace=steps, dataset_path=session.dataset_path)
        except requests.RequestException as e:
            del session.messages[history_length:]  # Rollback to previous state
            raise HTTPException(status_code=503, detail=f"Cannot reach the LLM service: {type(e).__name__}: {e}")
        except RuntimeError as e:
            del session.messages[history_length:]  # Rollback to previous state
            raise HTTPException(status_code=502, detail=f"The LLM service encountered a runtime error: {type(e).__name__}: {e}")      
        return {"session_id": session_id, "dataset": session.dataset, "answer": answer, "steps": steps, "seconds": round(time.time() - t0,1)}
    finally:
        session.lock.release()


@app.post("/sessions/{session_id}/reset")
def reset(session_id: str):
    """ Reset the current conversation in a specific session. """
    session = get_session(session_id)
    del session.messages[3:]
    return {"session_id": session_id, "reset": True}

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """ Delete a specific session. """
    get_session(session_id)   
    del sessions[session_id]
    return {"session_id": session_id, "deleted": True}

@app.get("/datasets")
def list_datasets():
    """ List all datasets in the data directory. """
    return {"datasets": sorted(p.name for p in DATA_DIR.iterdir() if p.suffix in ALLOWED)}   

@app.post("/datasets")
def upload_dataset(file: UploadFile = File(...)):
    """ Upload a new dataset to the data directory. """
    name = Path(file.filename).name
    if Path(name).suffix.lower() not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed types: {ALLOWED}")
    content = file.file.read(MAX_UPLOAD_SIZE + 1)
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds the maximum allowed size of {MAX_UPLOAD_SIZE} bytes.")
    (DATA_DIR / name).write_bytes(content)
    return {"saved":name}

@app.post("/start")
def start(body: StartRequest):
    """ Start a new conversation with the specified dataset. """
    path = DATA_DIR / Path(body.dataset).name
    if not path.exists() or path.suffix.lower() not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Dataset not found or invalid type. Allowed types: {ALLOWED}")
    
    conversation["dataset"] = path.name
    conversation["messages"] = new_message(path)
    return {"started": True, "dataset": path.name}    


"""
@app.post("/ask")
def ask(body: Question):
    
    if not conversation["messages"]:
        raise HTTPException(status_code=400, detail="No active conversation. Please start a conversation first.")
    t0 = time.time()
    steps = []
    conversation["messages"].append({"role": "user", "content": f"{body.question}\n{TURN_INSTRUCTION}"})    
    answer = agent_turn(conversation["messages"], verbose=False, trace=steps)
    return {"dataset": conversation["dataset"], "answer": answer, "steps": steps, "seconds": round(time.time() - t0,1)}


@app.post("/reset")
def reset():
    
    del conversation["messages"][3:]
    return {"reset": True}

"""