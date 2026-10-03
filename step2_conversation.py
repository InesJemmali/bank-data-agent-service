import sys
from step_chat import chat

KEEP_HISTORY = "--nohistory" not in sys.argv

SYSTEM = {"role": "system", "content": "You are a concise assistant."}

messages = [SYSTEM]

print(f"History: {'ON' if KEEP_HISTORY else 'OFF'}")


while True:
    user_text = input("you> ").strip()
    if user_text.lower() == "quit":
        break
    if not user_text:
        continue

    if KEEP_HISTORY:
        messages.append({"role": "user", "content": user_text})
        payload = messages
    else:
        payload = [SYSTEM, {"role": "user", "content": user_text}]

    reply = chat(payload)["message"]["content"]
    print(f"bot> {reply}\n")

    if KEEP_HISTORY:
        messages.append({"role": "assistant", "content": reply})


print(f"\nFinal message list had {len(messages)} entries.")
           