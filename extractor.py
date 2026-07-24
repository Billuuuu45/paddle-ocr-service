import re
from typing import List, Dict, Any, Optional

def clean_amount(val_str: str) -> str:
    # Remove currency symbols and formatting characters, keeping digits and decimal dot
    # e.g. "₹12,500.50" -> "12500.50", "₹12,500" -> "12500"
    cleaned = re.sub(r"[^\d.]", "", val_str)
    # If it ends with a dot, strip it
    if cleaned.endswith("."):
        cleaned = cleaned[:-1]
    return cleaned

def extract_amount_field(keywords: List[str], text: str, lines: List[Dict[str, Any]]) -> Optional[str]:
    # Look for keywords and try to extract the amount near them
    # First search line by line
    for idx, line_data in enumerate(lines):
        line_text = line_data.get("text", "")
        for kw in keywords:
            pattern = rf"(?i)\b{re.escape(kw)}\b"
            if re.search(pattern, line_text):
                # Search for a numeric amount on the same line after the keyword
                # Amount pattern matching things like 12,500.00, 12500, 1,200 etc.
                match = re.search(r"[:\-\s₹$€£]*([\d,]+(?:\.\d{2})?)", line_text[re.search(pattern, line_text).end():])
                if match:
                    val = clean_amount(match.group(1))
                    if val:
                        return val
                
                # If not found on same line, look at the next line or two
                for offset in [1, 2]:
                    if idx + offset < len(lines):
                        next_line = lines[idx + offset].get("text", "")
                        # Check if this next line is just a number
                        match_next = re.search(r"^\s*[:\-\s₹$€£]*([\d,]+(?:\.\d{2})?)\s*$", next_line)
                        if match_next:
                            val = clean_amount(match_next.group(1))
                            if val:
                                return val
                            
                        # Or contains an amount
                        match_next_any = re.search(r"[:\-\s₹$€£]*([\d,]+(?:\.\d{2})?)", next_line)
                        if match_next_any:
                            val = clean_amount(match_next_any.group(1))
                            if val:
                                return val
                            
    # Fallback to search raw text with regex
    for kw in keywords:
        pattern = rf"(?i)\b{re.escape(kw)}\b\s*[:\-\s₹$€£]*([\d,]+(?:\.\d{2})?)"
        match = re.search(pattern, text)
        if match:
            val = clean_amount(match.group(1))
            if val:
                return val
                
    return None

def extract_invoice_number(text: str, lines: List[Dict[str, Any]]) -> Optional[str]:
    # Regex pattern for invoice number keyword and value
    pattern = r"(?i)(?:invoice\s*number|invoice\s*no\.?|inv\s*no\.?|invoice\s*#|inv\s*#|bill\s*no\.?|bill\s*number)\s*[:#-]?\s*([A-Za-z0-9-/]+)"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
        
    # Line by line check
    for idx, line_data in enumerate(lines):
        line_text = line_data.get("text", "")
        if re.search(r"(?i)(?:invoice\s*number|invoice\s*no|inv\s*no|invoice\s*#|inv\s*#|bill\s*no|bill\s*number)", line_text):
            # Extract trailing alphanumeric string
            match_line = re.search(r"[:#-]?\s*([A-Za-z0-9-/]+)\s*$", line_text)
            if match_line and match_line.group(1).lower() not in ["number", "no", "invoice", "inv", "bill"]:
                return match_line.group(1).strip()
            # If not in same line, maybe next line has it
            if idx + 1 < len(lines):
                next_line = lines[idx + 1].get("text", "").strip()
                if re.match(r"^[A-Za-z0-9-/]+$", next_line):
                    return next_line

    return None

def extract_invoice_date(text: str, lines: List[Dict[str, Any]]) -> Optional[str]:
    # Look for keywords: date, invoice date, bill date, date of issue
    # Look for common date formats: YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, etc.
    date_patterns = [
        r"\b\d{4}[-/]\d{2}[-/]\d{2}\b",                      # YYYY-MM-DD
        r"\b\d{2}[-/]\d{2}[-/]\d{4}\b",                      # DD-MM-YYYY or MM-DD-YYYY
        r"\b\d{1,2}[-\s/]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s/]+\d{4}\b",  # DD-Mon-YYYY or DD Mon YYYY
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s/]+\d{1,2},?[-\s/]+\d{4}\b"  # Mon-DD-YYYY or Mon DD, YYYY
    ]
    
    # Check lines near date keywords
    for idx, line_data in enumerate(lines):
        line_text = line_data.get("text", "")
        if re.search(r"(?i)(?:date|issue\s*date|bill\s*date)", line_text):
            # Try to match any date format on same line
            for dp in date_patterns:
                match = re.search(dp, line_text, re.IGNORECASE)
                if match:
                    return match.group(0).strip()
            # Look at next line
            if idx + 1 < len(lines):
                next_line = lines[idx + 1].get("text", "").strip()
                for dp in date_patterns:
                    match = re.search(dp, next_line, re.IGNORECASE)
                    if match:
                        return match.group(0).strip()

    # Search entire text for any date pattern near "date" keyword
    for dp in date_patterns:
        pattern = rf"(?i)(?:date|issue\s*date|bill\s*date)\s*[:#-]?\s*({dp})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
            
    # As a last fallback, search for any date in the entire document
    for dp in date_patterns:
        match = re.search(dp, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()

    return None

def extract_gst_number(text: str, lines: List[Dict[str, Any]]) -> Optional[str]:
    # GSTIN format: 15 characters alphanumeric
    gst_pattern = r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Zz]{1}[A-Z\d]{1}\b"
    match = re.search(gst_pattern, text, re.IGNORECASE)
    if match:
        return match.group(0).upper()
    return None

def extract_po_number(text: str, lines: List[Dict[str, Any]]) -> Optional[str]:
    pattern = r"(?i)(?:purchase\s*order(?:\s*no\.?)?|po\s*no\.?|po\s*#)\s*[:#-]?\s*([A-Za-z0-9-/]+)"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    return None

def extract_currency(text: str, lines: List[Dict[str, Any]]) -> Optional[str]:
    # Look for currency symbols or codes
    currency_map = {
        "$": "USD",
        "₹": "INR",
        "rs": "INR",
        "€": "EUR",
        "£": "GBP"
    }
    
    # Try looking for codes first
    for code in ["USD", "INR", "EUR", "GBP", "CAD", "AUD"]:
        if re.search(rf"\b{code}\b", text, re.IGNORECASE):
            return code
            
    # Try symbols
    for sym, code in currency_map.items():
        if sym in text.lower():
            return code
            
    return None

def extract_vendor_name(text: str, lines: List[Dict[str, Any]]) -> Optional[str]:
    # Often the first line or two, unless prefixed by From/Vendor
    for idx, line_data in enumerate(lines):
        line_text = line_data.get("text", "").strip()
        if re.search(r"(?i)\b(?:from|vendor|sold\s*by)\b", line_text):
            # Check same line
            match = re.search(r"(?i)\b(?:from|vendor|sold\s*by)\s*[:\-]?\s*(.+)$", line_text)
            if match and len(match.group(1).strip()) > 2:
                return match.group(1).strip()
            # Or next line
            if idx + 1 < len(lines):
                next_line = lines[idx + 1].get("text", "").strip()
                if len(next_line) > 2 and not any(kw in next_line.lower() for kw in ["invoice", "date", "bill"]):
                    return next_line
                    
    # Default fallback: return the first line if it's not a common invoice label
    if len(lines) > 0:
        first_line = lines[0].get("text", "").strip()
        if len(first_line) > 2 and not any(kw in first_line.lower() for kw in ["invoice", "bill", "tax", "date"]):
            return first_line
            
    return None

def extract_customer_name(text: str, lines: List[Dict[str, Any]]) -> Optional[str]:
    # Look for bill to, ship to, customer, client, to:
    keywords = [r"bill\s*to", r"ship\s*to", r"invoice\s*to", r"sold\s*to", r"customer", r"client", r"\bto\b"]
    for idx, line_data in enumerate(lines):
        line_text = line_data.get("text", "").strip()
        for kw in keywords:
            if re.search(rf"(?i)\b{kw}\b", line_text):
                # Check same line
                match = re.search(rf"(?i)\b{kw}\s*[:\-]?\s*(.+)$", line_text)
                if match and len(match.group(1).strip()) > 2:
                    return match.group(1).strip()
                # Check next line
                if idx + 1 < len(lines):
                    next_line = lines[idx + 1].get("text", "").strip()
                    if len(next_line) > 2 and not any(k in next_line.lower() for k in ["invoice", "date", "tax", "amount"]):
                        return next_line
    return None

def extract_structured_invoice_data(raw_text: str, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "invoice_number": extract_invoice_number(raw_text, lines),
        "invoice_date": extract_invoice_date(raw_text, lines),
        "vendor_name": extract_vendor_name(raw_text, lines),
        "customer_name": extract_customer_name(raw_text, lines),
        "gst_number": extract_gst_number(raw_text, lines),
        "po_number": extract_po_number(raw_text, lines),
        "subtotal": extract_amount_field(["subtotal", "sub-total", "net amount", "sum"], raw_text, lines),
        "discount": extract_amount_field(["discount", "disc", "less"], raw_text, lines),
        "tax": extract_amount_field(["tax", "vat", "gst", "cgst", "sgst", "igst", "sales tax"], raw_text, lines),
        "total": extract_amount_field(["total", "grand total", "total amount", "amount due"], raw_text, lines),
        "balance_due": extract_amount_field(["balance due", "balance", "due amount", "remaining"], raw_text, lines),
        "currency": extract_currency(raw_text, lines)
    }
