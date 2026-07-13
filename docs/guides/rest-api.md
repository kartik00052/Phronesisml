# REST API

AetherML exposes a FastAPI-based REST API for running the ML pipeline over HTTP.

!!! info
    Install the API extras first: `pip install aetherml[api]`

## Starting the Server

```bash
aetherml run --help  # CLI
```

Or programmatically:

```python
from aetherml.interfaces.api.app import app
import uvicorn

uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Endpoints

All pipeline endpoints accept a file upload (multipart form) and optional parameters.

### System

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check, version, available engines |
| GET | `/version` | SDK version info |
| GET | `/capabilities` | Supported formats, engines, stages, limits |

### Pipeline

| Method | Path | Description |
|---|---|---|
| POST | `/analyze` | Full pipeline → profile |
| POST | `/clean` | Upload + ETL |
| POST | `/validate` | Upload + ETL + Validation |
| POST | `/detect-target` | Upload → Target Detection |
| POST | `/engineer` | Upload → Feature Engineering |
| POST | `/recommend-model` | Upload → Model Selection |
| POST | `/train` | Full pipeline → Trained Model |
| POST | `/evaluate` | Upload → Model Evaluation |
| POST | `/explain` | Upload → SHAP Explainability |
| POST | `/report` | Full pipeline → Markdown Report |

### Jobs

| Method | Path | Description |
|---|---|---|
| GET | `/jobs` | List all jobs |
| GET | `/jobs/{job_id}` | Get job status and result |

## Example: Analyze via cURL

```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@data.csv" \
  -F "engine=pandas" \
  -F "null_strategy=drop"
```

## Response Format

All endpoints return:

```json
{
  "success": true,
  "data": { ... }
}
```

Errors:

```json
{
  "success": false,
  "error": {
    "code": "UNSUPPORTED_FORMAT",
    "message": "File format '.xyz' is not supported.",
    "documentation": "https://..."
  }
}
```

## Interactive Docs

Once the server is running, visit:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
