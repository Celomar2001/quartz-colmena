from __future__ import annotations

import os
import re
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from slugify import slugify

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


# =========================
# CONFIGURACIÓN
# =========================

DOCUMENT_ID = "15l7Es5D8KIYMkezxIDwH3DLDKl-0zTELmOp4vVnuhwg"

# Este archivo está dentro de:
# C:\Users\Marce\Documents\Obsidian\Quartz\quartz\scripts
SCRIPT_DIR = Path(__file__).resolve().parent

# Raíz del proyecto Quartz:
# C:\Users\Marce\Documents\Obsidian\Quartz\quartz
PROJECT_DIR = SCRIPT_DIR.parent

# Carpeta donde Quartz lee las notas publicables
OUTPUT_DIR = PROJECT_DIR / "content" / "info-obtenida"

# Credenciales en la raíz del proyecto
CREDENTIALS_FILE = PROJECT_DIR / "credentials.json"
TOKEN_FILE = PROJECT_DIR / "token.json"

SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]

LANGUAGE_FILE_MAP = {
    "SPANISH": "spanish.md",
    "ENGLISH": "english.md",
    "FRENCH": "french.md",
    "PORTUGUESE": "portuguese.md",
    "POLSKI": "polski.md",
}


# =========================
# AUTENTICACIÓN
# =========================

def get_credentials() -> Credentials:
    creds: Optional[Credentials] = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                f"No se encontró credentials.json en: {CREDENTIALS_FILE}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            SCOPES
        )

        creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    return creds


def get_docs_service():
    creds = get_credentials()
    return build("docs", "v1", credentials=creds)


# =========================
# GOOGLE DOCS
# =========================

def fetch_document(service) -> Dict[str, Any]:
    return (
        service.documents()
        .get(
            documentId=DOCUMENT_ID,
            includeTabsContent=True
        )
        .execute()
    )


def flatten_tabs(tabs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []

    for tab in tabs:
        result.append(tab)

        child_tabs = tab.get("childTabs", [])
        if child_tabs:
            result.extend(flatten_tabs(child_tabs))

    return result


# =========================
# CONVERSIÓN A MARKDOWN
# =========================

def clean_text(text: str) -> str:
    return text.replace("\u000b", "\n")


def extract_text_run(element: Dict[str, Any]) -> str:
    text_run = element.get("textRun")
    if not text_run:
        return ""

    content = clean_text(text_run.get("content", ""))
    style = text_run.get("textStyle", {})

    if not content.strip():
        return content

    stripped = content.strip()

    if style.get("bold") and style.get("italic"):
        return f"***{stripped}***"
    elif style.get("bold"):
        return f"**{stripped}**"
    elif style.get("italic"):
        return f"*{stripped}*"

    return content


def paragraph_to_markdown(paragraph: Dict[str, Any]) -> str:
    elements = paragraph.get("elements", [])
    text = "".join(extract_text_run(el) for el in elements).rstrip()

    if not text:
        return ""

    paragraph_style = paragraph.get("paragraphStyle", {})
    named_style = paragraph_style.get("namedStyleType", "")

    heading_map = {
        "TITLE": "#",
        "SUBTITLE": "##",
        "HEADING_1": "#",
        "HEADING_2": "##",
        "HEADING_3": "###",
        "HEADING_4": "####",
        "HEADING_5": "#####",
        "HEADING_6": "######",
    }

    if named_style in heading_map:
        return f"{heading_map[named_style]} {text.strip()}"

    if "bullet" in paragraph:
        return f"- {text.strip()}"

    return text.strip()


def table_to_markdown(table: Dict[str, Any]) -> str:
    rows = table.get("tableRows", [])
    markdown_rows = []

    for row in rows:
        cells = row.get("tableCells", [])
        row_values = []

        for cell in cells:
            cell_content = cell.get("content", [])
            cell_text = structural_elements_to_markdown(cell_content)
            cell_text = re.sub(r"\s+", " ", cell_text).strip()
            row_values.append(cell_text)

        markdown_rows.append(row_values)

    if not markdown_rows:
        return ""

    header = markdown_rows[0]
    separator = ["---"] * len(header)

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]

    for row in markdown_rows[1:]:
        while len(row) < len(header):
            row.append("")
        lines.append("| " + " | ".join(row[:len(header)]) + " |")

    return "\n".join(lines)


def structural_elements_to_markdown(elements: List[Dict[str, Any]]) -> str:
    blocks = []

    for element in elements:
        if "paragraph" in element:
            md = paragraph_to_markdown(element["paragraph"])
            if md:
                blocks.append(md)

        elif "table" in element:
            md = table_to_markdown(element["table"])
            if md:
                blocks.append(md)

        elif "tableOfContents" in element:
            continue

    return "\n\n".join(blocks)


def tab_to_markdown(tab: Dict[str, Any]) -> str:
    tab_properties = tab.get("tabProperties", {})
    tab_title = tab_properties.get("title", "Untitled")

    document_tab = tab.get("documentTab", {})
    body = document_tab.get("body", {})
    content = body.get("content", [])

    body_md = structural_elements_to_markdown(content)

    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    frontmatter = f"""---
title: "{tab_title}"
source: "Google Docs"
google_doc_id: "{DOCUMENT_ID}"
updated: "{updated_at}"
---

"""

    return frontmatter + body_md + "\n"


# =========================
# GUARDADO
# =========================

def get_output_filename(tab_title: str) -> str:
    normalized = tab_title.strip().upper()

    if normalized in LANGUAGE_FILE_MAP:
        return LANGUAGE_FILE_MAP[normalized]

    return f"{slugify(tab_title)}.md"


def save_tab(tab: Dict[str, Any]) -> None:
    tab_properties = tab.get("tabProperties", {})
    tab_title = tab_properties.get("title", "Untitled")

    filename = get_output_filename(tab_title)
    output_path = OUTPUT_DIR / filename

    markdown = tab_to_markdown(tab)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print(f"Guardado: {output_path}")


# =========================
# MAIN
# =========================

def main() -> None:
    print("Iniciando sincronización Google Docs → Quartz/Obsidian")
    print(f"Proyecto: {PROJECT_DIR}")
    print(f"Salida: {OUTPUT_DIR}")

    service = get_docs_service()
    document = fetch_document(service)

    tabs = document.get("tabs", [])
    all_tabs = flatten_tabs(tabs)

    if not all_tabs:
        print("No se encontraron tabs en el documento.")
        return

    print(f"Tabs encontradas: {len(all_tabs)}")

    for tab in all_tabs:
        tab_properties = tab.get("tabProperties", {})
        title = tab_properties.get("title", "Untitled")

        print(f"Procesando tab: {title}")
        save_tab(tab)

    print("Sincronización completada.")


if __name__ == "__main__":
    main()