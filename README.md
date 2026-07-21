# PaddleOCR Service

A production-ready FastAPI service that provides an OCR endpoint using PaddleOCR.

## Features

- RESTful API with FastAPI
- OCR processing with PaddleOCR
- Automatic temporary file cleanup
- Dockerized deployment

## Requirements

- Python 3.11+
- Docker (optional)

## Setup and Run Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   uvicorn app:app --reload
   ```

## API Usage

### `POST /ocr`

Extract text from an image.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `file` (the image file)

**Response:**
```json
{
   "success": true,
   "text": "Extracted text here...",
   "lines": [
      {
         "text": "Extracted text here...",
         "confidence": 0.99,
         "boundingBox": [
            [10.0, 10.0],
            [100.0, 10.0],
            [100.0, 50.0],
            [10.0, 50.0]
         ]
      }
   ]
}
```
