## Llama Stack Setup


```bash
ollama run llama3.1:8b-instruct-fp16 --keepalive 60m
```

```bash
export INFERENCE_MODEL="meta-llama/Llama-3.1-8B-Instruct"
export LLAMA_STACK_PORT=8321
```

podman or docker

```bash
podman pull docker.io/llamastack/distribution-ollama
```

```bash
mkdir -p ~/.llama_stack
```

### Reset

```bash
rm -rf ~/.llama_stack
mkdir -p ~/.llama_stack
```

```bash
export LLAMA_STACK_MODEL="meta-llama/Llama-3.2-3B-Instruct"
export INFERENCE_MODEL="meta-llama/Llama-3.2-3B-Instruct"
export LLAMA_STACK_PORT=8321
export LLAMA_STACK_SERVER=http://localhost:$LLAMA_STACK_PORT
export LLAMA_STACK_ENDPOINT=$LLAMA_STACK_SERVER
```

```bash
podman run -it \
  -p $LLAMA_STACK_PORT:$LLAMA_STACK_PORT \
  -v ~/.llama:/root/.llama_stack \
  --env INFERENCE_MODEL=$INFERENCE_MODEL \
  --env OLLAMA_URL=http://host.containers.internal:11434 \
  llamastack/distribution-ollama \
  --port $LLAMA_STACK_PORT
```

```bash
podman ps
```

## Add Vision Model

```bash
pip install -r requirements.txt
```

```bash
ollama serve
```

```bash
ollama run granite3.2-vision:2b-fp16 --keepalive 60m
```

```bash
python register-vision-model.py
```
```bash
python list-models.py
```
