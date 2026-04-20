"""OCR service for document text extraction using Google Cloud Vision API.

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 10.2, 10.3
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class OCRStatus(str, Enum):
    """Status of OCR processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    MANUAL_REVIEW = "manual_review"


@dataclass
class IdentityFields:
    """Extracted fields from identity documents.
    
    Validates: Requirements 7.3
    """
    name: Optional[str] = None
    document_number: Optional[str] = None
    expiry_date: Optional[date] = None
    date_of_birth: Optional[date] = None
    document_type: Optional[str] = None
    confidence: float = 0.0


@dataclass
class EducationFields:
    """Extracted fields from education documents.
    
    Validates: Requirements 7.4
    """
    institution_name: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    grade: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ReceiptFields:
    """Extracted fields from receipt images.
    
    Validates: Requirements 10.2
    """
    merchant_name: Optional[str] = None
    amount: Optional[Decimal] = None
    transaction_date: Optional[date] = None
    currency: Optional[str] = None
    items: list = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class MedicineInfo:
    """Extracted medicine information from prescription.
    
    Validates: Requirements 14.3, 14.4
    """
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    confidence: float = 0.0


@dataclass
class PrescriptionFields:
    """Extracted fields from prescription images.
    
    Validates: Requirements 14.3, 14.4
    """
    doctor_name: Optional[str] = None
    hospital_name: Optional[str] = None
    patient_name: Optional[str] = None
    prescription_date: Optional[date] = None
    diagnosis: Optional[str] = None
    medicines: list = field(default_factory=list)  # List of MedicineInfo
    confidence: float = 0.0


@dataclass
class OCRResult:
    """Result of OCR processing.
    
    Validates: Requirements 7.1, 7.2, 10.2, 14.3
    """
    raw_text: str
    status: OCRStatus
    identity_fields: Optional[IdentityFields] = None
    education_fields: Optional[EducationFields] = None
    receipt_fields: Optional[ReceiptFields] = None
    prescription_fields: Optional["PrescriptionFields"] = None
    error_message: Optional[str] = None
    confidence: float = 0.0
    extracted_fields: dict = field(default_factory=dict)


class GoogleCloudVisionClient:
    """Client for Google Cloud Vision API.
    
    Validates: Requirements 7.1
    
    This is a mock implementation. In production, this would integrate
    with the actual Google Cloud Vision API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Google Cloud Vision client.
        
        Args:
            api_key: Google Cloud API key (optional for mock)
        """
        self.api_key = api_key
        self._initialized = False
    
    def _ensure_initialized(self) -> None:
        """Ensure the client is initialized."""
        if not self._initialized:
            # In production: Initialize Google Cloud Vision client
            # from google.cloud import vision
            # self.client = vision.ImageAnnotatorClient()
            self._initialized = True
            logger.info("Google Cloud Vision client initialized (mock)")
    
    async def detect_text(self, file_content: bytes) -> tuple[str, float]:
        """Detect text in an image using Google Cloud Vision API.
        
        Validates: Requirements 7.1
        
        Args:
            file_content: Raw bytes of the image/document
            
        Returns:
            Tuple of (extracted_text, confidence_score)
            
        Raises:
            OCRProcessingError: If text detection fails
        """
        self._ensure_initialized()
        
        # Mock implementation - in production, this would call the actual API:
        # image = vision.Image(content=file_content)
        # response = self.client.text_detection(image=image)
        # texts = response.text_annotations
        # if texts:
        #     return texts[0].description, 0.95
        # return "", 0.0
        
        logger.info(f"[MOCK] Detecting text from {len(file_content)} bytes")
        
        # For testing purposes, return mock text based on content size
        # In production, this would be replaced with actual API call
        mock_text = self._generate_mock_text(file_content)
        confidence = 0.95 if mock_text else 0.0
        
        return mock_text, confidence
    
    def _generate_mock_text(self, file_content: bytes) -> str:
        """Generate mock text for testing purposes.
        
        This method is only used in the mock implementation.
        In production, actual OCR results would be returned.
        """
        # Return empty string for very small files (likely invalid)
        if len(file_content) < 100:
            return ""
        
        # Return a generic mock text for testing
        return "MOCK OCR TEXT - Replace with actual Google Cloud Vision API integration"


class OCRProcessingError(Exception):
    """Exception raised when OCR processing fails."""
    
    def __init__(self, message: str, document_id: Optional[UUID] = None):
        self.message = message
        self.document_id = document_id
        super().__init__(message)


class FieldExtractor:
    """Extract structured fields from OCR text using NLP.
    
    Validates: Requirements 7.3, 7.4, 10.2
    
    Uses spaCy for named entity recognition and pattern matching
    to extract structured data from raw OCR text.
    """
    
    # Common date patterns
    DATE_PATTERNS = [
        r'\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b',  # DD/MM/YYYY or MM/DD/YYYY
        r'\b(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})\b',  # YYYY/MM/DD
        r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b',
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})\b',
    ]
    
    # Identity document patterns
    IDENTITY_PATTERNS = {
        'passport_number': r'\b[A-Z]{1,2}\d{6,9}\b',
        'aadhaar_number': r'\b\d{4}\s?\d{4}\s?\d{4}\b',
        'pan_number': r'\b[A-Z]{5}\d{4}[A-Z]\b',
        'driving_license': r'\b[A-Z]{2}\d{2}\s?\d{4}\s?\d{7}\b',
    }
    
    # Education document patterns
    DEGREE_PATTERNS = [
        r'\b(Bachelor|Master|Doctor|Ph\.?D|B\.?Tech|M\.?Tech|B\.?E|M\.?E|B\.?Sc|M\.?Sc|B\.?A|M\.?A|B\.?Com|M\.?Com|MBA|BBA|LLB|LLM)\b',
    ]
    
    MONTH_MAP = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    }
    
    def __init__(self):
        """Initialize the field extractor."""
        self._nlp = None
    
    def _get_nlp(self):
        """Lazy load spaCy model."""
        if self._nlp is None:
            try:
                import spacy
                # Try to load the English model
                try:
                    self._nlp = spacy.load("en_core_web_sm")
                except OSError:
                    # If model not found, use blank English model
                    logger.warning("spaCy model 'en_core_web_sm' not found, using blank model")
                    self._nlp = spacy.blank("en")
            except ImportError:
                logger.warning("spaCy not installed, using regex-only extraction")
                self._nlp = None
        return self._nlp
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string into a date object.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            Parsed date or None if parsing fails
        """
        # Try various date formats
        formats = [
            "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d",
            "%d-%m-%Y", "%m-%d-%Y", "%Y-%m-%d",
            "%d.%m.%Y", "%m.%d.%Y", "%Y.%m.%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def _extract_dates(self, text: str) -> list[date]:
        """Extract all dates from text.
        
        Args:
            text: Text to extract dates from
            
        Returns:
            List of extracted dates
        """
        dates = []
        
        for pattern in self.DATE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                
                # Handle different date formats
                if len(groups) == 3:
                    try:
                        # Check if first group is year (YYYY/MM/DD format)
                        if len(groups[0]) == 4:
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        # Check if contains month name
                        elif groups[0].lower()[:3] in self.MONTH_MAP:
                            month = self.MONTH_MAP[groups[0].lower()[:3]]
                            day, year = int(groups[1]), int(groups[2])
                        elif groups[1].lower()[:3] in self.MONTH_MAP:
                            day = int(groups[0])
                            month = self.MONTH_MAP[groups[1].lower()[:3]]
                            year = int(groups[2])
                        else:
                            # Assume DD/MM/YYYY
                            day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                        
                        if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100:
                            dates.append(date(year, month, day))
                    except (ValueError, TypeError):
                        continue
        
        return dates
    
    def _extract_names_with_nlp(self, text: str) -> list[str]:
        """Extract person names using spaCy NER.
        
        Args:
            text: Text to extract names from
            
        Returns:
            List of extracted names
        """
        nlp = self._get_nlp()
        if nlp is None:
            return []
        
        doc = nlp(text)
        names = []
        
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                names.append(ent.text)
        
        return names
    
    def _extract_organizations_with_nlp(self, text: str) -> list[str]:
        """Extract organization names using spaCy NER.
        
        Args:
            text: Text to extract organizations from
            
        Returns:
            List of extracted organization names
        """
        nlp = self._get_nlp()
        if nlp is None:
            return []
        
        doc = nlp(text)
        orgs = []
        
        for ent in doc.ents:
            if ent.label_ == "ORG":
                orgs.append(ent.text)
        
        return orgs
    
    async def extract_identity_fields(self, text: str) -> IdentityFields:
        """Extract structured fields from identity document text.
        
        Validates: Requirements 7.3
        
        Args:
            text: Raw OCR text from identity document
            
        Returns:
            IdentityFields with extracted data
        """
        fields = IdentityFields()
        confidence_scores = []
        
        # Extract document number using patterns
        for doc_type, pattern in self.IDENTITY_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.document_number = match.group(0).upper().replace(" ", "")
                fields.document_type = doc_type
                confidence_scores.append(0.9)
                break
        
        # Extract name using NLP
        names = self._extract_names_with_nlp(text)
        if names:
            # Use the longest name (likely the full name)
            fields.name = max(names, key=len)
            confidence_scores.append(0.8)
        
        # Extract dates
        dates = self._extract_dates(text)
        if dates:
            # Sort dates
            dates.sort()
            today = date.today()
            
            # Find expiry date (future date)
            future_dates = [d for d in dates if d > today]
            if future_dates:
                fields.expiry_date = future_dates[0]
                confidence_scores.append(0.85)
            
            # Find date of birth (past date, reasonable age)
            past_dates = [d for d in dates if d < today and (today.year - d.year) < 120]
            if past_dates:
                # Assume oldest reasonable date is DOB
                fields.date_of_birth = past_dates[0]
                confidence_scores.append(0.75)
        
        # Calculate overall confidence
        if confidence_scores:
            fields.confidence = sum(confidence_scores) / len(confidence_scores)
        
        return fields
    
    async def extract_education_fields(self, text: str) -> EducationFields:
        """Extract structured fields from education document text.
        
        Validates: Requirements 7.4
        
        Args:
            text: Raw OCR text from education document
            
        Returns:
            EducationFields with extracted data
        """
        fields = EducationFields()
        confidence_scores = []
        
        # Extract institution name using NLP
        orgs = self._extract_organizations_with_nlp(text)
        if orgs:
            # Look for keywords indicating educational institution
            edu_keywords = ['university', 'college', 'institute', 'school', 'academy']
            for org in orgs:
                if any(kw in org.lower() for kw in edu_keywords):
                    fields.institution_name = org
                    confidence_scores.append(0.9)
                    break
            
            # If no keyword match, use the first organization
            if not fields.institution_name and orgs:
                fields.institution_name = orgs[0]
                confidence_scores.append(0.7)
        
        # Extract degree using patterns
        for pattern in self.DEGREE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.degree = match.group(0)
                confidence_scores.append(0.85)
                break
        
        # Extract dates
        dates = self._extract_dates(text)
        if dates:
            dates.sort()
            if len(dates) >= 2:
                fields.start_date = dates[0]
                fields.end_date = dates[-1]
                confidence_scores.append(0.8)
            elif len(dates) == 1:
                # Single date likely graduation/completion date
                fields.end_date = dates[0]
                confidence_scores.append(0.7)
        
        # Extract grade/GPA patterns
        grade_patterns = [
            r'\b(CGPA|GPA|Grade)[:\s]*(\d+\.?\d*)\b',
            r'\b(\d+\.?\d*)\s*(CGPA|GPA)\b',
            r'\bFirst\s+Class\b',
            r'\bDistinction\b',
            r'\bHonours?\b',
        ]
        
        for pattern in grade_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.grade = match.group(0)
                confidence_scores.append(0.8)
                break
        
        # Calculate overall confidence
        if confidence_scores:
            fields.confidence = sum(confidence_scores) / len(confidence_scores)
        
        return fields
    
    async def extract_receipt_fields(self, text: str) -> ReceiptFields:
        """Extract structured fields from receipt text.
        
        Validates: Requirements 10.2
        
        Args:
            text: Raw OCR text from receipt image
            
        Returns:
            ReceiptFields with extracted merchant, amount, date
        """
        fields = ReceiptFields()
        confidence_scores = []
        
        # Extract merchant name using NLP (organizations)
        orgs = self._extract_organizations_with_nlp(text)
        if orgs:
            # Use the first organization as merchant name
            fields.merchant_name = orgs[0]
            confidence_scores.append(0.8)
        else:
            # Try to extract from first line (common receipt format)
            lines = text.strip().split('\n')
            if lines:
                first_line = lines[0].strip()
                if len(first_line) > 2 and len(first_line) < 100:
                    fields.merchant_name = first_line
                    confidence_scores.append(0.6)
        
        # Extract amount using patterns
        amount_patterns = [
            r'\b(?:Total|Grand\s*Total|Amount|Subtotal|Net\s*Amount)[:\s]*[\$£€₹]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b',
            r'\b[\$£€₹]\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b',
            r'\b(\d{1,3}(?:,\d{3})*\.\d{2})\s*(?:USD|EUR|GBP|INR|Rs\.?)?\b',
            r'\bRs\.?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b',
        ]
        
        amounts_found = []
        for pattern in amount_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount_str = match.group(1).replace(',', '')
                    amount = Decimal(amount_str)
                    if amount > 0:
                        amounts_found.append(amount)
                except (ValueError, IndexError):
                    continue
        
        if amounts_found:
            # Use the largest amount (likely the total)
            fields.amount = max(amounts_found)
            confidence_scores.append(0.85)
        
        # Extract currency
        currency_patterns = [
            (r'[\$]', 'USD'),
            (r'[£]', 'GBP'),
            (r'[€]', 'EUR'),
            (r'[₹]|Rs\.?|INR', 'INR'),
        ]
        
        for pattern, currency in currency_patterns:
            if re.search(pattern, text):
                fields.currency = currency
                confidence_scores.append(0.9)
                break
        
        # Extract transaction date
        dates = self._extract_dates(text)
        if dates:
            # Use the most recent date (likely transaction date)
            today = date.today()
            valid_dates = [d for d in dates if d <= today]
            if valid_dates:
                fields.transaction_date = max(valid_dates)
                confidence_scores.append(0.8)
        
        # Extract line items (basic extraction)
        item_pattern = r'(\d+)\s*[xX]\s*(.+?)\s+[\$£€₹]?\s*(\d+\.?\d*)'
        item_matches = re.finditer(item_pattern, text)
        for match in item_matches:
            try:
                qty = int(match.group(1))
                name = match.group(2).strip()
                price = Decimal(match.group(3))
                fields.items.append({
                    'quantity': qty,
                    'name': name,
                    'price': float(price),
                })
            except (ValueError, IndexError):
                continue
        
        if fields.items:
            confidence_scores.append(0.7)
        
        # Calculate overall confidence
        if confidence_scores:
            fields.confidence = sum(confidence_scores) / len(confidence_scores)
        
        return fields
    
    async def extract_prescription_fields(self, text: str) -> PrescriptionFields:
        """Extract structured fields from prescription text.
        
        Validates: Requirements 14.3, 14.4
        
        Args:
            text: Raw OCR text from prescription image
            
        Returns:
            PrescriptionFields with extracted doctor name, medicines, dosage, frequency
        """
        fields = PrescriptionFields()
        confidence_scores = []
        
        # Extract doctor name using patterns
        doctor_patterns = [
            r'\b(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\b(?:Physician|Consultant|Specialist)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:Prescribed\s+by|Attending\s+Doctor)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in doctor_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.doctor_name = match.group(1).strip()
                confidence_scores.append(0.85)
                break
        
        # If no pattern match, try NLP for person names near "Dr" keyword
        if not fields.doctor_name:
            names = self._extract_names_with_nlp(text)
            # Look for names near doctor-related keywords
            text_lower = text.lower()
            for name in names:
                name_pos = text_lower.find(name.lower())
                if name_pos != -1:
                    # Check if "dr" or "doctor" appears within 50 chars before the name
                    context_start = max(0, name_pos - 50)
                    context = text_lower[context_start:name_pos]
                    if 'dr' in context or 'doctor' in context:
                        fields.doctor_name = name
                        confidence_scores.append(0.7)
                        break
        
        # Extract hospital/clinic name using NLP
        orgs = self._extract_organizations_with_nlp(text)
        if orgs:
            # Look for keywords indicating medical facility
            medical_keywords = ['hospital', 'clinic', 'medical', 'healthcare', 'health', 'care', 'pharmacy']
            for org in orgs:
                if any(kw in org.lower() for kw in medical_keywords):
                    fields.hospital_name = org
                    confidence_scores.append(0.85)
                    break
            
            # If no keyword match, use the first organization
            if not fields.hospital_name and orgs:
                fields.hospital_name = orgs[0]
                confidence_scores.append(0.6)
        
        # Extract patient name
        patient_patterns = [
            r'\b(?:Patient|Name|Patient\s+Name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\b(?:Mr\.?|Mrs\.?|Ms\.?|Miss)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in patient_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.patient_name = match.group(1).strip()
                confidence_scores.append(0.8)
                break
        
        # Extract prescription date
        dates = self._extract_dates(text)
        if dates:
            today = date.today()
            valid_dates = [d for d in dates if d <= today]
            if valid_dates:
                # Use the most recent date as prescription date
                fields.prescription_date = max(valid_dates)
                confidence_scores.append(0.8)
        
        # Extract diagnosis
        diagnosis_patterns = [
            r'\b(?:Diagnosis|Dx|Chief\s+Complaint|Condition)[:\s]+([^\n]+)',
            r'\b(?:Suffering\s+from|Diagnosed\s+with)[:\s]+([^\n]+)',
        ]
        
        for pattern in diagnosis_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.diagnosis = match.group(1).strip()[:200]  # Limit length
                confidence_scores.append(0.75)
                break
        
        # Extract medicines with dosage and frequency
        fields.medicines = self._extract_medicines(text)
        if fields.medicines:
            confidence_scores.append(0.8)
        
        # Calculate overall confidence
        if confidence_scores:
            fields.confidence = sum(confidence_scores) / len(confidence_scores)
        
        return fields
    
    def _extract_medicines(self, text: str) -> list:
        """Extract medicine information from prescription text.
        
        Validates: Requirements 14.3, 14.4
        
        Args:
            text: Raw OCR text from prescription
            
        Returns:
            List of MedicineInfo objects
        """
        medicines = []
        
        # Common medicine patterns
        # Pattern 1: Medicine name followed by dosage and frequency
        # e.g., "Paracetamol 500mg - 1 tablet twice daily for 5 days"
        medicine_patterns = [
            # Pattern: Medicine Dosage - Quantity Frequency Duration
            r'(?:^|\n)\s*\d*\.?\s*([A-Za-z][A-Za-z\s\-]+?)\s+(\d+\s*(?:mg|ml|g|mcg|IU))\s*[-–]\s*(.+?)(?=\n|$)',
            # Pattern: Medicine (Dosage) Frequency
            r'(?:^|\n)\s*\d*\.?\s*([A-Za-z][A-Za-z\s\-]+?)\s*\((\d+\s*(?:mg|ml|g|mcg|IU))\)\s*(.+?)(?=\n|$)',
            # Pattern: Tab/Cap Medicine Dosage Frequency
            r'(?:^|\n)\s*\d*\.?\s*(?:Tab\.?|Cap\.?|Syp\.?|Inj\.?)\s+([A-Za-z][A-Za-z\s\-]+?)\s+(\d+\s*(?:mg|ml|g|mcg|IU)?)\s*(.+?)(?=\n|$)',
            # Pattern: Medicine - Dosage - Frequency (with dashes)
            r'(?:^|\n)\s*\d*\.?\s*([A-Za-z][A-Za-z\s]+?)\s*[-–]\s*(\d+\s*(?:mg|ml|g|mcg|IU)?)\s*[-–]\s*(.+?)(?=\n|$)',
        ]
        
        # Frequency patterns for extraction
        frequency_keywords = [
            'once daily', 'twice daily', 'thrice daily', 'three times daily',
            'once a day', 'twice a day', 'three times a day', 'four times a day',
            'every 4 hours', 'every 6 hours', 'every 8 hours', 'every 12 hours',
            'morning', 'evening', 'night', 'bedtime', 'before meals', 'after meals',
            'with food', 'empty stomach', 'as needed', 'prn', 'sos',
            'od', 'bd', 'tid', 'qid', 'hs', 'ac', 'pc',
            '1-0-0', '0-1-0', '0-0-1', '1-1-0', '1-0-1', '0-1-1', '1-1-1',
        ]
        
        # Duration patterns
        duration_patterns = [
            r'(?:for\s+)?(\d+)\s*(?:days?|weeks?|months?)',
            r'x\s*(\d+)\s*(?:days?|weeks?|months?)',
        ]
        
        seen_medicines = set()
        
        for pattern in medicine_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                try:
                    name = match.group(1).strip()
                    dosage = match.group(2).strip() if match.lastindex >= 2 else None
                    rest = match.group(3).strip() if match.lastindex >= 3 else ""
                    
                    # Skip if name is too short or looks like a common word
                    if len(name) < 3 or name.lower() in ['the', 'and', 'for', 'with', 'take']:
                        continue
                    
                    # Normalize medicine name
                    name = re.sub(r'\s+', ' ', name).title()
                    
                    # Skip duplicates
                    if name.lower() in seen_medicines:
                        continue
                    seen_medicines.add(name.lower())
                    
                    # Extract frequency from rest of text
                    frequency = None
                    for freq_kw in frequency_keywords:
                        if freq_kw.lower() in rest.lower():
                            frequency = freq_kw
                            break
                    
                    # Extract duration
                    duration = None
                    for dur_pattern in duration_patterns:
                        dur_match = re.search(dur_pattern, rest, re.IGNORECASE)
                        if dur_match:
                            duration = dur_match.group(0)
                            break
                    
                    medicine = MedicineInfo(
                        name=name,
                        dosage=dosage,
                        frequency=frequency,
                        duration=duration,
                        instructions=rest[:100] if rest else None,
                        confidence=0.75,
                    )
                    medicines.append(medicine)
                    
                except (IndexError, AttributeError):
                    continue
        
        # If no medicines found with patterns, try simpler extraction
        if not medicines:
            medicines = self._extract_medicines_simple(text)
        
        return medicines
    
    def _extract_medicines_simple(self, text: str) -> list:
        """Simple medicine extraction when patterns don't match.
        
        Args:
            text: Raw OCR text
            
        Returns:
            List of MedicineInfo objects
        """
        medicines = []
        
        # Look for lines that might be medicine entries
        # Common indicators: starts with number, contains mg/ml, contains Tab/Cap
        lines = text.split('\n')
        
        medicine_indicators = ['mg', 'ml', 'mcg', 'tab', 'cap', 'syp', 'inj', 'tablet', 'capsule']
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            line_lower = line.lower()
            
            # Check if line contains medicine indicators
            if any(ind in line_lower for ind in medicine_indicators):
                # Try to extract medicine name (first word or words before dosage)
                dosage_match = re.search(r'(\d+\s*(?:mg|ml|g|mcg|IU))', line, re.IGNORECASE)
                
                if dosage_match:
                    # Get text before dosage as medicine name
                    name_part = line[:dosage_match.start()].strip()
                    # Remove common prefixes
                    name_part = re.sub(r'^(?:\d+\.?\s*)?(?:Tab\.?|Cap\.?|Syp\.?|Inj\.?)\s*', '', name_part, flags=re.IGNORECASE)
                    name_part = name_part.strip()
                    
                    if len(name_part) >= 3:
                        medicine = MedicineInfo(
                            name=name_part.title(),
                            dosage=dosage_match.group(1),
                            instructions=line[dosage_match.end():].strip()[:100] or None,
                            confidence=0.5,
                        )
                        medicines.append(medicine)
        
        return medicines[:10]  # Limit to 10 medicines


class OCRService:
    """Service for OCR processing of documents.
    
    Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 14.3, 14.4
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the OCR service.
        
        Args:
            api_key: Google Cloud Vision API key
        """
        self.vision_client = GoogleCloudVisionClient(api_key)
        self.field_extractor = FieldExtractor()
    
    async def process_document(
        self,
        doc_id: UUID,
        file_content: bytes,
        category: str,
    ) -> OCRResult:
        """Process a document for OCR text extraction.
        
        Validates: Requirements 7.1, 7.2, 7.3, 7.4
        
        Args:
            doc_id: UUID of the document
            file_content: Raw bytes of the document file
            category: Document category (Identity, Education, etc.)
            
        Returns:
            OCRResult with extracted text and structured fields
            
        Raises:
            OCRProcessingError: If processing fails
        """
        logger.info(f"Processing document {doc_id} for OCR (category: {category})")
        
        try:
            # Extract text using Google Cloud Vision
            raw_text, confidence = await self.vision_client.detect_text(file_content)
            
            if not raw_text:
                logger.warning(f"No text extracted from document {doc_id}")
                return OCRResult(
                    raw_text="",
                    status=OCRStatus.COMPLETED,
                    confidence=0.0,
                )
            
            result = OCRResult(
                raw_text=raw_text,
                status=OCRStatus.COMPLETED,
                confidence=confidence,
            )
            
            # Extract structured fields based on category
            if category.lower() == "identity":
                result.identity_fields = await self.field_extractor.extract_identity_fields(raw_text)
                result.extracted_fields = {
                    "name": result.identity_fields.name,
                    "document_number": result.identity_fields.document_number,
                    "expiry_date": result.identity_fields.expiry_date.isoformat() if result.identity_fields.expiry_date else None,
                    "date_of_birth": result.identity_fields.date_of_birth.isoformat() if result.identity_fields.date_of_birth else None,
                    "document_type": result.identity_fields.document_type,
                }
            elif category.lower() == "education":
                result.education_fields = await self.field_extractor.extract_education_fields(raw_text)
                result.extracted_fields = {
                    "institution_name": result.education_fields.institution_name,
                    "degree": result.education_fields.degree,
                    "field_of_study": result.education_fields.field_of_study,
                    "start_date": result.education_fields.start_date.isoformat() if result.education_fields.start_date else None,
                    "end_date": result.education_fields.end_date.isoformat() if result.education_fields.end_date else None,
                    "grade": result.education_fields.grade,
                }
            
            logger.info(f"OCR processing completed for document {doc_id}")
            return result
            
        except Exception as e:
            logger.exception(f"OCR processing failed for document {doc_id}: {e}")
            raise OCRProcessingError(str(e), doc_id)
    
    async def extract_identity_fields(self, text: str) -> IdentityFields:
        """Extract identity fields from text.
        
        Validates: Requirements 7.3
        
        Args:
            text: Raw OCR text
            
        Returns:
            IdentityFields with extracted data
        """
        return await self.field_extractor.extract_identity_fields(text)
    
    async def extract_education_fields(self, text: str) -> EducationFields:
        """Extract education fields from text.
        
        Validates: Requirements 7.4
        
        Args:
            text: Raw OCR text
            
        Returns:
            EducationFields with extracted data
        """
        return await self.field_extractor.extract_education_fields(text)
    
    async def extract_receipt_fields(self, text: str) -> ReceiptFields:
        """Extract receipt fields from text.
        
        Validates: Requirements 10.2
        
        Args:
            text: Raw OCR text from receipt
            
        Returns:
            ReceiptFields with extracted merchant, amount, date
        """
        return await self.field_extractor.extract_receipt_fields(text)
    
    async def extract_prescription_fields(self, text: str) -> PrescriptionFields:
        """Extract prescription fields from text.
        
        Validates: Requirements 14.3, 14.4
        
        Args:
            text: Raw OCR text from prescription
            
        Returns:
            PrescriptionFields with extracted doctor name, medicines, dosage, frequency
        """
        return await self.field_extractor.extract_prescription_fields(text)
    
    async def process_prescription(
        self,
        file_content: bytes,
    ) -> PrescriptionFields:
        """Process a prescription image for OCR and extract fields.
        
        Validates: Requirements 14.3, 14.4
        
        Args:
            file_content: Raw bytes of the prescription image
            
        Returns:
            PrescriptionFields with extracted doctor name, medicines, dosage, frequency
            
        Raises:
            OCRProcessingError: If processing fails
        """
        logger.info("Processing prescription for OCR")
        
        try:
            # Extract text using Google Cloud Vision
            raw_text, confidence = await self.vision_client.detect_text(file_content)
            
            if not raw_text:
                logger.warning("No text extracted from prescription")
                return PrescriptionFields(confidence=0.0)
            
            # Extract prescription fields
            fields = await self.field_extractor.extract_prescription_fields(raw_text)
            
            logger.info(
                f"Prescription OCR completed: doctor={fields.doctor_name}, "
                f"medicines_count={len(fields.medicines)}"
            )
            return fields
            
        except Exception as e:
            logger.exception(f"Prescription OCR processing failed: {e}")
            raise OCRProcessingError(str(e))
    
    async def process_receipt(
        self,
        file_content: bytes,
    ) -> ReceiptFields:
        """Process a receipt image for OCR and extract fields.
        
        Validates: Requirements 10.2, 10.3
        
        Args:
            file_content: Raw bytes of the receipt image
            
        Returns:
            ReceiptFields with extracted merchant, amount, date
            
        Raises:
            OCRProcessingError: If processing fails
        """
        logger.info("Processing receipt for OCR")
        
        try:
            # Extract text using Google Cloud Vision
            raw_text, confidence = await self.vision_client.detect_text(file_content)
            
            if not raw_text:
                logger.warning("No text extracted from receipt")
                return ReceiptFields(confidence=0.0)
            
            # Extract receipt fields
            fields = await self.field_extractor.extract_receipt_fields(raw_text)
            
            logger.info(f"Receipt OCR completed: merchant={fields.merchant_name}, amount={fields.amount}")
            return fields
            
        except Exception as e:
            logger.exception(f"Receipt OCR processing failed: {e}")
            raise OCRProcessingError(str(e))


# Singleton instance
ocr_service = OCRService()
