"""Create small, deterministic DOCX fixtures for VeriBid acceptance runs."""

from __future__ import annotations

from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1] / "fixtures"


FIXTURES = {
    "buyer_rfp.docx": [
        "Buyer RFP - Cloud Platform Procurement",
        "Technical requirement: monthly availability must be at least 99.99%.",
        "Compliance requirement: customer data and processing must remain in the EU.",
        "Commercial requirement: three-year total cost must not exceed USD 500000.",
    ],
    "buyer_rubric.docx": [
        "Buyer scoring rubric",
        "TECHNICAL weight 40: availability threshold and operational evidence.",
        "COMMERCIAL weight 30: deterministic three-year cost calculation.",
        "COMPLIANCE weight 30: mandatory EU residency and source-backed review.",
    ],
    "vendor_a_proposal.docx": [
        "Vendor A - Northstar Cloud proposal",
        "Availability commitment: 99.90% monthly uptime.",
        "Customer data is hosted in EU regions, but telemetry is processed in the US.",
        "Pricing: USD 120000 annual license, USD 40000 implementation, USD 15000 support per year.",
    ],
    "vendor_b_proposal.docx": [
        "Vendor B - Helix Systems proposal",
        "Availability commitment: 99.995% monthly uptime.",
        "Customer data and operational telemetry are hosted and processed in EU regions only.",
        "Pricing: USD 140000 annual license, USD 35000 implementation, USD 12000 support per year.",
    ],
    "vendor_c_proposal.docx": [
        "Vendor C - Juniper Works proposal",
        "This proposal intentionally omits an availability commitment, residency statement, and pricing schedule.",
        "Please request follow-up evidence before making a procurement decision.",
    ],
}


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOCUMENT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>"""


def document_xml(paragraphs: list[str]) -> str:
    body = "".join(f"<w:p><w:r><w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r></w:p>" for text in paragraphs)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>{body}<w:sectPr/></w:body>
</w:document>"""


def write_docx(path: Path, paragraphs: list[str]) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", RELS)
        archive.writestr("word/document.xml", document_xml(paragraphs))
        archive.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for name, paragraphs in FIXTURES.items():
        write_docx(ROOT / name, paragraphs)
    print(f"created {len(FIXTURES)} synthetic DOCX fixtures in {ROOT}")


if __name__ == "__main__":
    main()
