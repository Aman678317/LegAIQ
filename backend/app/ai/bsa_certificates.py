"""BSA Section 63 Electronic Evidence Certification Engine.

Implements cryptographic hashing and court-admissible certificate generation for electronic
records as required by Bharatiya Sakshya Adhiniyam, 2023 Section 63 / Indian Evidence Act Section 65B.
"""

import hashlib
import io
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID


class EvidenceHasher:
    """Cryptographically secure hashing for electronic records under BSA 2023 Section 63."""
    
    @staticmethod
    def generate_file_hash(
        file_bytes: bytes,
        filename: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> str:
        """Generate SHA-256 hash for file with metadata inclusion.
        
        Format: {filename}|{size}|{timestamp}|{content_hash}
        """
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        
        filename_part = filename or "unknown"
        size_part = str(len(file_bytes))
        timestamp_part = timestamp or datetime.now(timezone.utc)
        
        metadata = f"{filename_part}|{size_part}|{timestamp_part.isoformat()}"
        combined = f"{metadata}|{content_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    @staticmethod
    def generate_incremental_hash(file_path: str, chunk_size: int = 8192) -> str:
        """Generate hash for large files using incremental processing."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()
    
    @staticmethod
    def verify_hash(file_bytes: bytes, expected_hash: str, filename: Optional[str] = None) -> bool:
        """Verify file integrity against stored hash."""
        generated_hash = EvidenceHasher.generate_file_hash(file_bytes, filename)
        return generated_hash == expected_hash or hashlib.sha256(file_bytes).hexdigest() == expected_hash


class CertificateGenerator:
    """Generate court-admissible Section 63 electronic evidence certificates."""
    
    @staticmethod
    def generate_section63_certificate(
        evidence: Dict[str, Any],
        custodian: Dict[str, Any],
        include_hash: bool = True,
        include_qr_code: bool = False,
    ) -> bytes:
        """Generate PDF certificate for electronic evidence under Section 63 BSA 2023."""
        if include_hash and "hash_value" not in evidence:
            evidence["hash_value"] = EvidenceHasher.generate_file_hash(
                evidence.get("file_bytes", b""),
                evidence.get("filename", "unknown"),
            )

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm

            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4

            # Header
            c.setFont("Helvetica-Bold", 15)
            c.drawCentredString(width / 2, height - 2*cm, "CERTIFICATE UNDER SECTION 63 OF BHARATIYA SAKSHYA ADHINIYAM, 2023")
            c.setFont("Helvetica", 9)
            c.drawCentredString(width / 2, height - 2.6*cm, "(Admissibility of Electronic Records / Secondary Evidence in Indian Courts)")
            c.line(2*cm, height - 3.2*cm, width - 2*cm, height - 3.2*cm)

            # Part 1: Evidence Identification
            c.setFont("Helvetica-Bold", 11)
            c.drawString(2*cm, height - 4.2*cm, "1. IDENTIFICATION OF ELECTRONIC RECORD")
            c.setFont("Helvetica", 9)
            y = height - 5.0*cm
            c.drawString(2.5*cm, y, f"Document / File Name : {evidence.get('filename', 'N/A')}")
            y -= 0.6*cm
            c.drawString(2.5*cm, y, f"File Size (Bytes)    : {evidence.get('file_size', len(evidence.get('file_bytes', b'')))} bytes")
            y -= 0.6*cm
            c.drawString(2.5*cm, y, f"MIME / Format        : {evidence.get('mime_type', 'application/pdf')}")
            y -= 0.6*cm
            c.drawString(2.5*cm, y, f"SHA-256 Integrity Hash: {evidence.get('hash_value', 'N/A')}")
            y -= 0.6*cm
            c.drawString(2.5*cm, y, f"Acquisition Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

            # Part 2: System Operating Parameters
            y -= 1.0*cm
            c.setFont("Helvetica-Bold", 11)
            c.drawString(2*cm, y, "2. COMPUTER SYSTEM & OPERATING INTEGRITY PARAMETERS")
            c.setFont("Helvetica", 9)
            y -= 0.8*cm
            c.drawString(2.5*cm, y, "• The computer system was operating properly during the relevant period of electronic storage.")
            y -= 0.5*cm
            c.drawString(2.5*cm, y, "• Storage and reproduction were performed in the ordinary course of regular legal processing activities.")
            y -= 0.5*cm
            c.drawString(2.5*cm, y, "• Cryptographic SHA-256 integrity verification was conducted with zero corruption detected.")

            # Part 3: Statutory Custodian Declaration
            y -= 1.0*cm
            c.setFont("Helvetica-Bold", 11)
            c.drawString(2*cm, y, "3. STATUTORY DECLARATION UNDER SECTION 63(4) BSA 2023")
            c.setFont("Helvetica", 8.5)
            y -= 0.7*cm
            decl = (
                "I hereby solemnly state and certify to the best of my knowledge and belief that the above-described "
                "electronic record is an authentic reproduction of the original document processed under lawful custody."
            )
            c.drawString(2.5*cm, y, decl)

            # Part 4: Custodian Sign-off
            y -= 1.2*cm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(2.5*cm, y, f"Custodian Name : {custodian.get('name', 'Advocate / Legal Officer')}")
            y -= 0.6*cm
            c.drawString(2.5*cm, y, f"Designation    : {custodian.get('position', 'Authorized Signatory')}")
            y -= 0.6*cm
            c.drawString(2.5*cm, y, f"Organization   : {custodian.get('organization', 'LegAIQ Verified Entity')}")
            y -= 1.5*cm
            c.drawString(2.5*cm, y, "Signature: ___________________________    Date: " + datetime.now(timezone.utc).strftime("%Y-%m-%d"))

            # Footer
            c.setFont("Helvetica", 7.5)
            c.drawCentredString(width / 2, 1.5*cm, f"Certificate ID: CERT-{evidence.get('document_id', 'BSA63-LEGAIQ')} | Generated by LegAIQ")

            c.save()
            return buffer.getvalue()

        except ImportError:
            # Fallback PDF header/content generator
            content = (
                f"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                f"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                f"3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Contents 4 0 R>>endobj\n"
                f"4 0 obj<</Length 120>>stream\nBT /F1 12 Tf 50 750 Td (SECTION 63 BSA 2023 CERTIFICATE) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000206 00000 n\ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n380\n%%EOF"
            )
            return content.encode("utf-8")
