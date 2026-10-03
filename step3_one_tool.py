import json
import pandas as pd
from step_chat import chat


# ------ 1. the tool: ordinary Python -------
def row_count(path: str) -> str:
    df = pd.read_csv(path)
    return json.dumps({"row_count": int(df.shape[0]), "columns": int(df.shape[1])})

TOOLS = { "row_count": row_count }

# ------ 2. the schema: what the model is told exists --------
SCHEMAS = [
    {
       "type": "function",
       "function": {
          "name": "row_count",
          "description": "Returns the number of rows in a CSV file.",
          "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the CSV file."
                    },
            },
            "required": ["path"],
          },
        },
    },
]

# ----- 3 . one round trip, written out by hand -----

messages = [
  {"role":"system","content":"You are a data analyst. Use tools for"},
  {"role": "user", "content": "How many rows are in data/tx.csv?"},  
] 


first = chat(messages,tools=SCHEMAS)
print("---- First Reply ------")
print(json.dumps(first["message"],indent=2))

calls = first["message"].get("tool_calls", [])
if not calls:
  print("NO TOOL CALL. Model answered directly:", first["message"]["content"])
  raise SystemExit

messages.append(first["message"])

for c in calls:
  name = c["function"]["name"]
  args = c["function"]["arguments"]
  print(f"--- EXECUTING {name}({args}) ---")
  result = TOOLS[name](**args)
  print("RESULT: ", result)
  messages.append({"role":"tool","content":result,"name":name})  

second = chat(messages,tools=SCHEMAS)
print("---- Second Reply ------")
print(second["message"]["content"])
