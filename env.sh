module load python/3.11
source /lustre07/scratch/ines12/financial-agent/.venv/bin/activate
export OLLAMA_ROOT="/lustre07/scratch/ines12/llms/ollama"
export PATH="$OLLAMA_ROOT/bin:$PATH"
export LD_LIBRARY_PATH="$OLLAMA_ROOT/lib/ollama:$LD_LIBRARY_PATH"
export OLLAMA_MODELS="/lustre07/scratch/ines12/llms/ollama_models"
export OLLAMA_HOST="127.0.0.1:21434"
export MODEL="qwen3:14b"
export OLLAMA_KEEP_ALIVE=2h
export WEB_MODE="open"
