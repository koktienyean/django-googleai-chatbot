# Plan 01: Ollama Integration

**Status**: Planning
**Priority**: High (foundation for other features)
**Estimated Effort**: Medium

---

## Goal

Add Ollama as a third AI backend so users can run local LLMs (Llama 3, Mistral, Qwen, etc.) without API keys or internet. The chatbot already supports Claude and Gemini via `ask_ai()` router - Ollama slots in the same pattern.

## Why Ollama?

- **Free & local** - no API costs, no rate limits, data stays on-machine
- **Privacy** - sensitive queries never leave the network
- **Offline** - works without internet
- **Model variety** - run Llama 3, Mistral, CodeLlama, Qwen, Phi, etc.
- **Tool calling** - Ollama supports function calling (needed for tasks 2 & 3)

## Current Architecture

```python
# chatbot/views.py - current routing
def ask_ai(message, model='claude-3-5-sonnet-20241022', user=None):
    if model.startswith('claude'):
        return ask_claude(message, model, user)
    elif model.startswith('gemini') or model.startswith('gpt'):
        return ask_gemini_api(message, model, user)
    else:
        return ask_claude(message, model, user)  # default fallback
```

## Implementation Plan

### Phase 1: Basic Ollama Chat

**1.1 Add Ollama dependency**
```
# requirements.txt
ollama>=0.4.0
```

**1.2 Environment config**
```env
# .env
OLLAMA_BASE_URL=http://localhost:11434   # default Ollama endpoint
OLLAMA_DEFAULT_MODEL=llama3.2           # fallback model
```

**1.3 Create `ask_ollama()` function in `chatbot/views.py`**
```python
import ollama as ollama_client

OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_DEFAULT_MODEL = os.getenv('OLLAMA_DEFAULT_MODEL', 'llama3.2')

def ask_ollama(message, model='llama3.2', user=None):
    """Call local Ollama API and return response text"""
    try:
        client = ollama_client.Client(host=OLLAMA_BASE_URL)
        response = client.chat(
            model=model,
            messages=[{"role": "user", "content": message}]
        )
        return response['message']['content']
    except Exception as e:
        return f"Ollama Error: {str(e)}"
```

**1.4 Update `ask_ai()` router**
```python
def ask_ai(message, model='claude-3-5-sonnet-20241022', user=None):
    if model.startswith('claude'):
        return ask_claude(message, model, user)
    elif model.startswith('gemini'):
        return ask_gemini_api(message, model, user)
    elif model.startswith('ollama:') or model in get_ollama_models():
        actual_model = model.replace('ollama:', '') if model.startswith('ollama:') else model
        return ask_ollama(message, actual_model, user)
    else:
        return ask_claude(message, model, user)
```

**1.5 Add Ollama models to model list API**

Update `api_list_models()` to query Ollama for available models:
```python
def get_ollama_models():
    """Fetch available models from local Ollama instance"""
    try:
        client = ollama_client.Client(host=OLLAMA_BASE_URL)
        models = client.list()
        return [m['name'] for m in models.get('models', [])]
    except:
        return []
```

**1.6 Update `ChatSession.model` default choices in UI**

The frontend model selector already works dynamically via `api_list_models`. Just ensure Ollama models appear with an "Ollama" badge/prefix.

### Phase 2: Ollama Tool Calling (Function Calling)

Once basic chat works, add tool/function calling support so Ollama models can query Django data just like Claude and Gemini do.

**2.1 Ollama tool calling format**

Ollama uses the OpenAI-compatible tool calling format:
```python
def ask_ollama(message, model='llama3.2', user=None):
    tools = []
    if user:
        tools = build_ollama_tools(user)  # Same tools, OpenAI format

    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": message}],
        tools=tools if tools else None
    )

    # Handle tool calls in response
    while response['message'].get('tool_calls'):
        for tool_call in response['message']['tool_calls']:
            func_name = tool_call['function']['name']
            func_args = tool_call['function']['arguments']
            result = execute_tool(user, func_name, func_args)
            # Append tool result and continue conversation
        response = client.chat(model=model, messages=messages, tools=tools)

    return response['message']['content']
```

**2.2 Refactor: Extract shared tool definitions**

Currently tool definitions are duplicated between `ask_claude()` and `ask_gemini_api()`. Extract to a shared module:

```
chatbot/
  tools/
    __init__.py
    definitions.py    # Tool schemas (API-agnostic)
    executors.py      # Tool function implementations
    formatters.py     # Convert to Claude/Gemini/Ollama formats
```

This refactor is **critical** before adding a third backend to avoid triple-duplication.

### Phase 3: Ollama Health & Management

**3.1 Health check endpoint**
```python
# GET /api/ollama/status/
def api_ollama_status(request):
    """Check if Ollama is running and return available models"""
    try:
        models = get_ollama_models()
        return JsonResponse({'status': 'connected', 'models': models})
    except:
        return JsonResponse({'status': 'disconnected', 'models': []})
```

**3.2 Model pull endpoint (optional)**
```python
# POST /api/ollama/pull/
def api_ollama_pull(request):
    """Pull/download a new model to Ollama"""
    model_name = request.POST.get('model')
    # Stream pull progress...
```

---

## File Changes Summary

| File | Change |
|------|--------|
| `requirements.txt` | Add `ollama>=0.4.0` |
| `.env` | Add `OLLAMA_BASE_URL`, `OLLAMA_DEFAULT_MODEL` |
| `chatbot/views.py` | Add `ask_ollama()`, update `ask_ai()` router, update `api_list_models()` |
| `chatbot/tools/` (new) | Extract shared tool definitions (Phase 2 refactor) |
| `chatbot/urls.py` | Add `/api/ollama/status/` endpoint |
| `templates/` | Add Ollama badge in model selector |

## Risks & Considerations

1. **Ollama not installed** - Must gracefully handle when Ollama is not running (show "Ollama offline" in model list)
2. **Tool calling support** - Not all Ollama models support tool calling. Need to detect and fallback to prompt-based tool use
3. **Performance** - Local models are slower than API calls. Consider streaming responses
4. **Memory** - Large models need significant RAM/VRAM. Document minimum requirements
5. **Model naming conflicts** - Need prefix strategy (`ollama:llama3.2`) to avoid collision with cloud model names

## Testing

- [ ] Basic chat with Ollama model works
- [ ] Model list includes Ollama models when Ollama is running
- [ ] Graceful fallback when Ollama is offline
- [ ] Tool calling works with compatible models (llama3.2, mistral, qwen)
- [ ] Chat history saved correctly for Ollama sessions
