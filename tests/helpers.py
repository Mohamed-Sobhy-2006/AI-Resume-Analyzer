"""Helpers that create small sample resume files for the tests."""
import io

SAMPLE_RESUME_LINES = [
    "Ahmed Hassan", "ahmed.hassan@example.com | +20 100 123 4567", "Summary",
    "Backend developer who enjoys building APIs.", "Skills",
    "Python, FastAPI, SQL, Git, Docker, teamwork, communication", "Experience",
    "Backend Intern - Nile Software (2024)", "Reduced API response time by 30% using caching.",
    "Education", "BSc Computer Science, Cairo University", "Projects",
    "AI Resume Analyzer built with FastAPI and SQLite", "Certifications", "PCEP certified Python programmer",
]


def make_docx_bytes(lines=None) -> bytes:
    from docx import Document
    document = Document()
    for line in lines or SAMPLE_RESUME_LINES:
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def make_pdf_bytes(lines=None) -> bytes:
    """Build a tiny valid one-page PDF containing the given text lines."""
    def esc(text):
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    body = "BT /F1 11 Tf 40 760 Td 14 TL " + " ".join(f"({esc(l)}) Tj T*" for l in (lines or SAMPLE_RESUME_LINES)) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(body)} >>\nstream\n{body}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for number, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{obj}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out
