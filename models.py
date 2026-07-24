from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Metadata(BaseModel):
    filename: str
    file_type: str
    processing_time: float
    engine: str = "PaddleOCR"


class OCRLine(BaseModel):
    text: str
    confidence: float
    boundingBox: List[List[float]] = Field(
        ..., description="Coordinates [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]"
    )


class OCRResult(BaseModel):
    raw_text: str
    lines: List[OCRLine]


class StructuredInvoiceData(BaseModel):
    model_config = {"extra": "allow"}
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    vendor_name: Optional[str] = None
    customer_name: Optional[str] = None
    gst_number: Optional[str] = None
    po_number: Optional[str] = None
    subtotal: Optional[str] = None
    discount: Optional[str] = None
    tax: Optional[str] = None
    total: Optional[str] = None
    balance_due: Optional[str] = None
    currency: Optional[str] = None


class StructuredAPIResponse(BaseModel):
    success: bool
    document_type: str
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    raw_text: Optional[str] = None
    error: Optional[str] = None


class OCRResponse(BaseModel):
    success: bool
    message: str
    metadata: Optional[Metadata] = None
    raw_text: Optional[str] = None
    lines: Optional[List[OCRLine]] = None
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
