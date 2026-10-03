import sys
from pathlib import Path
import requests

API="http://localhost:8000"
GREY= "\033[90m"  # switch to grey text
RESET="\033[0m"  # back to the normal color


def choose_dataset(arg):
    """ Upload the file if it exists here, then start a conversation on it. """
    local = Path(arg)
    if local.is_file():
        with open(local, "rb") as f:
            r = requests.post(f"{API}/datasets", files={"file": f})
        r.raise_for_status()
        print(f"Uploaded dataset: {local.name}")
    r = requests.post(f"{API}/sessions", json={"dataset": local.name})
    if r.status_code != 200:
        sys.exit(f"Error starting conversation: {r.json().get('detail', r.text)}")
    return r.json()["session_id"], local.name

def show(data):
    for s in data["steps"]:
        print(f"{GREY}step {s['step']}: tool={s['tool']}, args={s['args']}, result={s['result']}{RESET}")
        print(f"           -> {s['results'][:300]}{RESET}")
    print(f"{GREY} ({data['seconds']} s){RESET}")
    print(f"bot> {data['answer']}\n") 

def main():
    session_id, dataset = choose_dataset(sys.argv[1] if len(sys.argv) > 1 else "data/tx.csv")
    url = f"{API}/sessions/{session_id}"
    
    print(f"Conversation {session_id[:8]} Started on dataset: {dataset}. Type 'quit' to exit the conversation and 'reset' to clear history. \n")
    while True:
        question = input("you> ").strip()
        if question.lower() == "quit":
            break
        if question.lower() == "reset":
            requests.post(f"{url}/reset")
            print("Conversation history cleared\n")   
            continue
        if not question:
            continue
        r = requests.post(f"{url}/ask", json={"question": question}, timeout=900)
        if r.status_code != 200:
            print(f"Error asking question: {r.json().get('detail', r.text)}")
            continue
        show(r.json())

if __name__ == "__main__":
    main()        