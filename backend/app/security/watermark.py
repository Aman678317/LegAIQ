"""Dynamic Document Watermarking Engine for LegAIQ / Jurisiva AI.

Provides configurable watermarking with viewer identity (email/user ID),
timestamp, and IP address for secure document preview and export under DPDP Act 2023.
"""
import hashlib
from datetime import datetime, timezone
from typing import Dict, Optional


class DocumentWatermarker:
    """Engine for generating and applying dynamic watermarks to legal documents."""

    @staticmethod
    def generate_watermark_metadata(
        viewer_email: str,
        viewer_ip: Optional[str] = "127.0.0.1",
        organization_name: Optional[str] = "LegAIQ Enterprise",
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, str]:
        """Generate structured watermark text and tracking hash."""
        ts = timestamp or datetime.now(timezone.utc)
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S UTC")
        watermark_text = f"CONFIDENTIAL — {viewer_email} | IP: {viewer_ip} | {ts_str} | {organization_name}"
        
        # Tamper-evident hash
        audit_hash = hashlib.sha256(f"{viewer_email}:{viewer_ip}:{ts_str}".encode()).hexdigest()[:12]
        
        return {
            "viewer_email": viewer_email,
            "viewer_ip": viewer_ip or "Unknown IP",
            "timestamp": ts_str,
            "organization": organization_name or "Enterprise",
            "watermark_text": watermark_text,
            "audit_hash": audit_hash,
            "watermark_code": f"LEGAIQ-SEC-{audit_hash.upper()}",
        }

    @classmethod
    def apply_text_watermark(
        cls,
        content: str,
        viewer_email: str,
        viewer_ip: Optional[str] = "127.0.0.1",
        organization_name: Optional[str] = "LegAIQ Enterprise",
    ) -> str:
        """Embed security headers and footers with viewer watermark into text content."""
        meta = cls.generate_watermark_metadata(viewer_email, viewer_ip, organization_name)
        
        header = (
            f"/* ==========================================================================\n"
            f"   CONFIDENTIAL & PROPRIETARY — {meta['organization']}\n"
            f"   VIEWED BY: {meta['viewer_email']} | IP: {meta['viewer_ip']} | {meta['timestamp']}\n"
            f"   AUDIT SECURITY TRACKING CODE: {meta['watermark_code']}\n"
            f"   UNAUTHORIZED DISTRIBUTION STRICTLY PROHIBITED UNDER DPDP ACT 2023\n"
            f"   ========================================================================== */\n\n"
        )
        
        footer = (
            f"\n\n/* [END OF PROTECTED DOCUMENT — TRACKING: {meta['watermark_code']} — {meta['viewer_email']}] */"
        )
        
        return header + content + footer

    @classmethod
    def generate_svg_watermark(
        cls,
        viewer_email: str,
        viewer_ip: Optional[str] = "127.0.0.1",
        opacity: float = 0.12,
    ) -> str:
        """Generate SVG overlay pattern for rendering over document viewers."""
        meta = cls.generate_watermark_metadata(viewer_email, viewer_ip)
        text = f"{meta['viewer_email']} • {meta['timestamp']} • {meta['watermark_code']}"
        
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="500" height="300" viewBox="0 0 500 300">
  <style>
    .watermark-text {{
      fill: rgba(148, 163, 184, {opacity});
      font-family: monospace, sans-serif;
      font-size: 14px;
      font-weight: 600;
      letter-spacing: 1px;
    }}
  </style>
  <g transform="rotate(-30 250 150)">
    <text x="50" y="100" class="watermark-text">CONFIDENTIAL &amp; PRIVILEGED</text>
    <text x="20" y="130" class="watermark-text">{text}</text>
    <text x="50" y="200" class="watermark-text">CONFIDENTIAL &amp; PRIVILEGED</text>
    <text x="20" y="230" class="watermark-text">{text}</text>
  </g>
</svg>"""
        return svg


def watermark_document_text(content: str, email: str, ip: str = "127.0.0.1") -> str:
    return DocumentWatermarker.apply_text_watermark(content, email, ip)
