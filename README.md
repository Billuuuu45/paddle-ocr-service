# PaddleOCR Service

A production-ready FastAPI service that provides OCR extraction with PaddleOCR and GPT-OSS-20B-based structured JSON post-processing.

## Features

- RESTful FastAPI endpoint for OCR image upload
- PaddleOCR extraction logic unchanged
- Clean OCR text normalization
- GPT-OSS-20B prompt-driven structured JSON conversion
- JSON validation and retry handling
- Configurable raw OCR text inclusion via environment
- Swagger-compatible API documentation

## Requirements

- Python 3.11+
- Docker (optional)

## Setup and Run Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy configuration template:
   ```bash
   cp .env.example .env
   ```

3. Set `GPT_ENDPOINT`, `GPT_MODEL`, `GPT_PAYLOAD_TYPE`, and optionally `GPT_API_KEY` in `.env`.

The default endpoint uses `http://localhost:8001/v1/completions`, which is more likely to be the model server port than the OCR application port.

4. Run the server:
   ```bash
   uvicorn app:app --reload
   ```

## API Usage

### `POST /ocr`

Extract text from an image and return structured JSON metadata.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `file` (the image file)

**Response:**
```json
{
  "success": true,
  "document_type": "invoice",
  "structured_data": {
    "invoice_number": "INV-12345",
    "invoice_date": "2026-07-23",
    "vendor_name": "Example Supplier",
    "total": 1234.56
  }
}
```

If `INCLUDE_RAW_OCR_TEXT=true` is set, the response may also include `raw_text`.

## Prompt Template

The prompt template is stored in `prompts/ocr_prompt.txt` and instructs GPT-OSS-20B to return only valid JSON with no markdown or extra explanation.

## Endpoints

- `GET /` - Serves the frontend UI if present.
- `POST /ocr` - Upload an image and receive structured JSON output.

## Notes

- The service preserves existing PaddleOCR extraction logic and uses a separate SLM service layer for post-processing.
- Validation ensures the GPT response contains `document_type` and `structured_data`.
- Retries once automatically if GPT returns invalid JSON.
