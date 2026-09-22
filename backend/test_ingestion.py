from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from openpyxl import Workbook

from backend.ingestion import IngestionError, parse_document


def test_docx_preserves_resolvable_source_pointer(tmp_path: Path):
    path = tmp_path / "buyer.docx"
    document_xml = '''<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>EU data residency is mandatory.</w:t></w:r></w:p></w:body></w:document>'''
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", document_xml)
    chunks = parse_document(path, "DOC_RFP_01", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert chunks[0].source_pointer.resolvable is True
    assert chunks[0].source_pointer.section == "paragraph 1"


def test_xlsx_preserves_sheet_and_row_locator(tmp_path: Path):
    path = tmp_path / "pricing.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Pricing"
    sheet.append(["Annual license", 120000])
    workbook.save(path)
    chunks = parse_document(path, "DOC_PRICE_01", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "VEN_A", "PROP_A")
    assert chunks[0].source_pointer.sheet_name == "Pricing"
    assert chunks[0].source_pointer.row_start == 1
    assert chunks[0].vendor_id == "VEN_A"


def test_parser_rejects_partial_vendor_scope(tmp_path: Path):
    with pytest.raises(ValueError, match="supplied together"):
        parse_document(tmp_path / "nope.pdf", "DOC_01", "application/pdf", "VEN_A", None)
