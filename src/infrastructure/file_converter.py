import os
import pandas as pd
from pypdf import PdfReader
from docx import Document

from src.application.interfaces import FileContentProvider


class FileConverter(FileContentProvider):
    def read_text(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return self._read_pdf(file_path)
        elif ext in [".docx", ".doc"]:
            return self._read_docx(file_path)
        elif ext in [".xlsx", ".xls"]:
            return self._read_excel(file_path)
        else:
            # Default to text
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    def _read_pdf(self, path: str) -> str:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

    def _read_docx(self, path: str) -> str:
        doc = Document(path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text

    def _read_excel(self, path: str) -> str:
        # Read all sheets, convert to markdown tables
        sheets = pd.read_excel(path, sheet_name=None)
        text = ""
        for sheet_name, df in sheets.items():
            text += f"## Sheet: {sheet_name}\n\n"
            text += df.to_markdown(index=False)
            text += "\n\n"
        return text
