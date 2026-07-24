# PaddleOCR Service - Implementation Document

## Project Overview

**PaddleOCR Service** is a production-ready FastAPI-based OCR (Optical Character Recognition) web application that extracts text and structured data from invoices and other documents. It uses PaddleOCR for document analysis and provides both backend API endpoints and a frontend React UI.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  - UI Components (Center, Left, Right Panel)                │
│  - API Service Layer                                         │
│  - Context & Hooks for state management                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP Requests
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                           │
│  - /ocr endpoint: File upload & processing                  │
│  - /: HTML UI serving                                       │
│  - Response Model Layer (Pydantic)                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌─────────┐      ┌──────────────┐   ┌──────────────┐
   │ OCR     │      │ Data         │   │ Models       │
   │ Engine  │      │ Extractor    │   │ (Pydantic)   │
   └─────────┘      └──────────────┘   └──────────────┘
        │
        ▼
   ┌─────────────────┐
   │ PaddleOCR       │
   │ Library         │
   └─────────────────┘
```

---

## Backend Components

### 1. **app.py** - FastAPI Application Server
**Purpose**: Main entry point for the backend service

**Key Responsibilities**:
- Initialize FastAPI application
- Configure environment variables for PaddleOCR (disable MKLDNN)
- Serve static HTML UI
- Handle file upload and OCR processing
- Manage temporary file lifecycle
- Return structured API responses

**Key Routes**:
- `GET /` - Serves the frontend HTML interface (`index.html`)
- `POST /ocr` - Accepts image/PDF file upload, processes with OCR, returns extracted data

**Key Functions**:
- `serve_ui()` - Returns HTML interface for browser access
- `perform_ocr(file)` - Main OCR processing pipeline:
  1. Validates file type (image or PDF)
  2. Saves file temporarily with UUID naming
  3. Runs OCR via `ocr_engine`
  4. Extracts structured data via `extractor`
  5. Builds response model with metadata and results
  6. Cleans up temporary file

**Response Format**:
- Success: `OCRResponse` with metadata, raw_text, lines, and structured_data
- Error: JSON with error message and HTTP 500 status

**Dependencies**:
- FastAPI, Uvicorn, Pydantic
- Models, OCR Engine, Extractor modules

---

### 2. **ocr_engine.py** - OCR Engine Wrapper
**Purpose**: Encapsulates PaddleOCR initialization and execution

**Key Responsibilities**:
- Initialize PaddleOCR with configuration (English language, textline orientation)
- Process image/PDF files and extract text with bounding boxes
- Format OCR results into structured format

**Key Classes**:
- `OCREngine` - Singleton class for OCR operations
  - `__init__()` - Initializes PaddleOCR instance (handles errors gracefully)
  - `run_ocr(filepath)` - Processes file and returns formatted results

**Key Methods**:
- `run_ocr(filepath: str) -> dict`:
  - Takes file path as input
  - Calls PaddleOCR's predict() method
  - Extracts recognition text, confidence scores, and bounding box polygons
  - Returns dictionary with:
    - `raw_text`: Full concatenated text
    - `lines`: List of OCRLine objects with text, confidence, and bounding box

**Global Instance**:
- `ocr_engine = OCREngine()` - Singleton created at module load

**Dependencies**:
- PaddleOCR, PIL

---

### 3. **models.py** - Pydantic Data Models
**Purpose**: Define API request/response schemas and ensure data validation

**Key Classes**:

1. **Metadata** - Document processing metadata
   - `filename`: Original uploaded filename
   - `file_type`: MIME type (image/* or application/pdf)
   - `processing_time`: OCR processing duration in seconds
   - `engine`: OCR engine name (default: "PaddleOCR")

2. **OCRLine** - Single recognized text line
   - `text`: Extracted text content
   - `confidence`: Recognition confidence score (0-1)
   - `boundingBox`: 4 corner coordinates [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]

3. **OCRResult** - Raw OCR output
   - `raw_text`: Full concatenated text
   - `lines`: List of OCRLine objects

4. **StructuredInvoiceData** - Extracted structured fields
   - Invoice fields: `invoice_number`, `invoice_date`, `vendor_name`, `customer_name`
   - Financial fields: `subtotal`, `discount`, `tax`, `total`, `balance_due`
   - Document fields: `gst_number`, `po_number`, `currency`
   - Config: Allows extra fields via `model_config = {"extra": "allow"}`

5. **OCRResponse** - Final API response
   - `success`: Boolean operation status
   - `message`: Human-readable status message
   - `metadata`: Metadata object (optional)
   - `raw_text`: Full extracted text (optional)
   - `lines`: Array of OCRLine objects (optional)
   - `structured_data`: Dictionary of extracted structured fields
   - `error`: Error message if failed (optional)

**Features**:
- Uses Pydantic v2 for validation and serialization
- `exclude_none=True` in responses omits null values
- Custom filtering removes empty strings from responses

---

### 4. **extractor.py** - Invoice Data Extraction
**Purpose**: Extract structured invoice fields from raw OCR text using regex patterns

**Key Responsibilities**:
- Parse OCR output to extract specific invoice fields
- Normalize and clean extracted values
- Handle various format variations (currency symbols, date formats, etc.)

**Key Functions**:

1. **clean_amount(val_str)** - Currency cleanup
   - Removes currency symbols (₹, $, €, £)
   - Removes formatting characters (commas)
   - Keeps only digits and decimal points
   - Example: "₹12,500.50" → "12500.50"

2. **extract_amount_field(keywords, text, lines)** - Generic amount extraction
   - Searches for amount keywords in text
   - Looks for numeric values on same or adjacent lines
   - Returns first matching amount

3. **extract_invoice_number(text, lines)** - Invoice ID extraction
   - Regex patterns: "invoice number", "inv no", "bill no", "invoice #"
   - Extracts alphanumeric ID after colon/dash
   - Checks multiple lines if needed

4. **extract_invoice_date(text, lines)** - Date extraction
   - Supports formats: YYYY-MM-DD, DD-MM-YYYY, DD-Mon-YYYY, etc.
   - Searches near "date" keywords
   - Returns first matching date found

5. **extract_gst_number(text, lines)** - GST ID (India-specific)
   - GSTIN pattern: 15 character alphanumeric format
   - Validates Indian GST number structure

6. **extract_po_number(text, lines)** - Purchase order extraction
   - Keywords: "purchase order", "po no", "po #"
   - Extracts alphanumeric PO identifier

7. **extract_currency(text, lines)** - Currency detection
   - Recognizes currency codes (USD, INR, EUR, GBP, CAD, AUD)
   - Recognizes currency symbols ($, ₹, €, £)

8. **extract_structured_invoice_data(raw_text, lines)** - Main orchestrator
   - Calls all extraction functions
   - Returns dictionary with all extracted fields
   - Handles multiple field extraction for amounts (subtotal, tax, discount, total)

**Supported Fields**:
- vendor_name, customer_name, gst_number, po_number
- invoice_number, invoice_date
- subtotal, discount, tax, total, balance_due
- currency

---

## Frontend Components

### Directory Structure

```
frontend/src/
├── components/
│   ├── center-panel/      # Main content area for OCR results
│   ├── left-panel/        # Document upload & selection
│   ├── right-panel/       # Structured data display
│   ├── layout/            # Page layout wrapper
│   └── common/            # Shared UI components
├── context/               # React context for state management
├── hooks/                 # Custom React hooks
├── pages/                 # Page-level components
├── services/              # API communication layer
├── types/                 # TypeScript interfaces/types
└── utils/                 # Utility functions
```

### Component Purposes

**Layout Components** (`layout/`):
- Define overall page structure
- Manage three-panel layout (left, center, right)

**Center Panel** (`center-panel/`):
- Display OCR results and extracted text
- Show annotated document preview with bounding boxes
- Display processing metadata

**Left Panel** (`left-panel/`):
- File upload interface
- Document list management
- Processing status indicators

**Right Panel** (`right-panel/`):
- Display structured invoice data in key-value format
- Show extracted fields (invoice number, date, amounts, etc.)
- Allow field editing and correction

**Common Components** (`common/`):
- Reusable UI elements (buttons, forms, cards, etc.)
- Shared utilities and styling

**Services** (`services/`):
- API client for backend communication
- OCR endpoint wrapper
- Error handling and request management

**Context & Hooks** (`context/`, `hooks/`):
- Global state management
- Processing state (uploading, processing, completed)
- Document history tracking
- Custom hooks for file handling

**Types** (`types/`):
- TypeScript interfaces for type safety
- OCR response schema mirroring backend models
- Structured data types

---

## Data Flow

### Complete Request-Response Flow

```
1. USER UPLOADS FILE
   └─> Frontend triggers file input
       └─> User selects image or PDF

2. FILE SUBMISSION
   └─> Frontend service sends multipart POST to /ocr endpoint
       ├─> Method: POST
       ├─> Route: /ocr
       └─> Body: multipart/form-data with file

3. BACKEND RECEIVES FILE (app.py)
   ├─> Validates file type (image/* or application/pdf)
   ├─> Generates UUID filename
   ├─> Saves to uploads/ directory
   └─> Starts timer

4. OCR ENGINE PROCESSING (ocr_engine.py)
   ├─> OCREngine.run_ocr() is called
   ├─> PaddleOCR.predict() processes file
   ├─> Extracts:
   │   ├─> rec_texts: Recognized text lines
   │   ├─> rec_scores: Confidence scores
   │   └─> dt_polys: Bounding box polygons
   └─> Returns formatted lines with text, confidence, bbox

5. DATA EXTRACTION (extractor.py)
   ├─> extract_structured_invoice_data() parses text
   ├─> Runs regex patterns for specific fields:
   │   ├─> Invoice number, date
   │   ├─> Vendor, customer names
   │   ├─> Amounts (subtotal, tax, total, etc.)
   │   ├─> GST, PO numbers
   │   └─> Currency detection
   └─> Returns dictionary of extracted fields

6. RESPONSE BUILDING (app.py)
   ├─> Creates Metadata model with processing_time
   ├─> Creates StructuredInvoiceData model from extracted fields
   ├─> Filters empty/null values
   ├─> Builds OCRResponse with:
   │   ├─> success: true
   │   ├─> message: "OCR completed successfully"
   │   ├─> metadata: processing info
   │   ├─> raw_text: full concatenated text
   │   ├─> lines: array with text/confidence/bbox for each line
   │   └─> structured_data: extracted key-value pairs
   └─> Returns JSON response

7. CLEANUP (app.py finally block)
   └─> Deletes temporary file from uploads/

8. FRONTEND RECEIVES RESPONSE
   ├─> API service processes JSON
   ├─> Updates React state via context
   └─> Renders results:
       ├─> Center panel: Display extracted text + metadata
       ├─> Left panel: Add to document history
       └─> Right panel: Show structured fields table

9. USER VIEWS RESULTS
   ├─> Raw text display with line-by-line breakdown
   ├─> Bounding box visualization on document preview
   ├─> Structured data in right panel:
   │   ├─> Invoice number, date
   │   ├─> Vendor/customer names
   │   ├─> Line items and amounts
   │   └─> Totals
   └─> Processing time and confidence metrics
```

---

## Processing Pipeline Summary

```
┌──────────────┐
│ User uploads │
│ image/PDF    │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ app.py/perform_ocr() │
│ - Validate file      │
│ - Save temp file     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ ocr_engine.py        │
│ - PaddleOCR process  │
│ - Extract lines/bbox │
│ - Return raw text    │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ extractor.py         │
│ - Parse raw text     │
│ - Extract fields     │
│ - Normalize values   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ models.py            │
│ - Validate response  │
│ - Filter nulls       │
│ - Serialize JSON     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Frontend receives    │
│ - Display results    │
│ - Show metadata      │
│ - Render structure   │
└──────────────────────┘
```

---

## Key Technologies

### Backend
- **FastAPI**: Modern async web framework with automatic OpenAPI docs
- **Uvicorn**: ASGI server for running FastAPI
- **PaddleOCR**: Baidu's open-source OCR engine with high accuracy
- **PaddlePaddle**: Deep learning framework (PaddleOCR dependency)
- **Pydantic**: Data validation and serialization
- **Python 3.11+**: Language requirement

### Frontend
- **React**: UI component library
- **TypeScript**: Type-safe JavaScript
- **Axios/Fetch**: HTTP client for API calls
- **React Context**: State management
- **Custom Hooks**: Component logic extraction

---

## Important Configuration

### Environment Variables (app.py)
```python
FLAGS_use_mkldnn = "0"                      # Disable CPU optimization
PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT = "0"   # Disable by default
```
These disable MKLDNN optimizations for better compatibility.

### OCREngine Configuration (ocr_engine.py)
```python
PaddleOCR(use_textline_orientation=True, lang='en')
```
- `use_textline_orientation=True`: Detects text orientation
- `lang='en'`: English language recognition

### Upload Directory
```
uploads/     # Temporary storage for uploaded files
```
Files are stored with UUID names and deleted after processing.

---

## Error Handling

### Backend Error Cases

1. **OCR Engine Not Initialized**
   - Status: 500
   - Message: "OCR engine is not initialized"

2. **Invalid File Type**
   - Status: 400
   - Message: "Invalid file type. Please upload an image or PDF"

3. **Processing Exception**
   - Status: 500
   - Message: "OCR processing failed"
   - Includes stack trace in logs

### File Cleanup
- Temporary files are always cleaned up in `finally` block
- Even if processing fails, file is removed

---

## Deployment

### Docker Support
- `Dockerfile` provided for containerized deployment
- Handles PaddleOCR model downloading
- Exposes FastAPI on standard port

### Local Development
```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Access at `http://localhost:8000`

---

## Data Models Relationships

```
OCRResponse (API Response)
├─ success: bool
├─ message: str
├─ metadata: Metadata
│  ├─ filename: str
│  ├─ file_type: str
│  ├─ processing_time: float
│  └─ engine: str
├─ raw_text: str
├─ lines: List[OCRLine]
│  └─ OCRLine
│     ├─ text: str
│     ├─ confidence: float
│     └─ boundingBox: List[List[float]]
└─ structured_data: Dict[str, Any]
   └─ StructuredInvoiceData fields
      ├─ invoice_number: str
      ├─ invoice_date: str
      ├─ vendor_name: str
      ├─ customer_name: str
      ├─ subtotal: str
      ├─ tax: str
      ├─ total: str
      └─ ... (other fields)
```

---

## Performance Considerations

1. **PaddleOCR**: First run downloads models (~100MB), subsequent runs use cached models
2. **Temporary Files**: UUID-named files prevent collisions
3. **Async Processing**: FastAPI handles concurrent requests
4. **MKLDNN Disabled**: Trading CPU optimization for compatibility
5. **Response Filtering**: Empty values removed before serialization

---

## Future Enhancement Opportunities

1. Add batch OCR processing for multiple files
2. Implement document preview with bounding box overlay
3. Add field editing and manual correction
4. Integrate with database for document history
5. Add support for multiple document types (receipts, contracts, etc.)
6. Implement confidence thresholds for field extraction
7. Add user authentication for multi-user support
8. Cache OCR results for identical uploads
9. Add export to various formats (CSV, JSON, PDF)
10. Improve structured field extraction with ML models

