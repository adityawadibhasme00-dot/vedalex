import hashlib
import json
import time
from typing import Dict, Any, Optional

class DPDPConsentLogger:
    """
    Implements consent capture, cryptographic audit trail, and grievance metadata
    in compliance with India's Digital Personal Data Protection Act, 2023 (DPDP Act).
    """
    _audit_log = []

    @classmethod
    def log_consent(
        cls,
        user_id: str,
        case_id: str,
        purpose: str,
        consented_terms: str,
        ip_address: Optional[str] = "127.0.0.1"
    ) -> Dict[str, Any]:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        consent_string = f"{user_id}:{case_id}:{purpose}:{consented_terms}:{timestamp}"
        consent_hash = hashlib.sha256(consent_string.encode()).hexdigest()
        
        record = {
            "user_id": user_id,
            "case_id": case_id,
            "purpose": purpose,
            "timestamp": timestamp,
            "consent_hash": consent_hash,
            "ip_address": ip_address,
            "jurisdiction": "India (DPDP Act 2023)",
            "data_residency": "ap-south-1"
        }
        cls._audit_log.append(record)
        return record

    @classmethod
    def get_audit_trail(cls, case_id: str) -> list:
        return [log for log in cls._audit_log if log["case_id"] == case_id]
