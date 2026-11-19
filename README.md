# DocuMind

DocuMind is a FastAPI API for uploading TXT documents and retrieving relevant text fragments with TF-IDF and cosine similarity.

## Requirements

- Python 3.11 or newer

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run tests

```bash
pip install -r requirements-dev.txt
pytest
```
