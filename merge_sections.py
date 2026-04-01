"""
Merges new_sections.docx body XML into methodology.docx and product_documentation.docx.

Strategy:
1. Extract word/document.xml from new_sections.docx — get the inner body content
   (everything between <w:body> and </w:body>, excluding any final <w:sectPr>)
2. Extract word/document.xml from each target docx
3. Insert the new content before the closing </w:body> (or before an existing <w:sectPr> at end)
4. Repack the docx with the modified document.xml
5. Also copy any new numbering/styles entries if needed (for bullet lists)
"""

import zipfile
import shutil
import re
import os
from pathlib import Path
import xml.etree.ElementTree as ET

DOCS_DIR = Path("D:/Claude Code Projects/Consumer Research/docs")
NEW_SECTIONS = DOCS_DIR / "new_sections.docx"
TARGETS = [
    DOCS_DIR / "methodology.docx",
    DOCS_DIR / "product_documentation.docx",
]

# XML namespaces
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

def read_file_from_zip(zip_path: Path, inner_path: str) -> bytes:
    with zipfile.ZipFile(zip_path, "r") as zf:
        return zf.read(inner_path)

def list_zip_files(zip_path: Path) -> list:
    with zipfile.ZipFile(zip_path, "r") as zf:
        return zf.namelist()

def extract_body_inner_xml(doc_xml_bytes: bytes) -> str:
    """
    Returns the XML string of everything inside <w:body>...</w:body>,
    excluding any trailing <w:sectPr> element (which is the page layout section).
    """
    content = doc_xml_bytes.decode("utf-8")

    # Find <w:body> ... </w:body>
    body_start = content.find("<w:body>")
    body_end = content.rfind("</w:body>")

    if body_start == -1 or body_end == -1:
        raise ValueError("Could not find <w:body> tags in document.xml")

    inner = content[body_start + len("<w:body>"):body_end]

    # Remove trailing <w:sectPr ...>...</w:sectPr> if present
    # This is the section properties element at the end of the body
    # Use regex to remove the last <w:sectPr> block
    inner = re.sub(r'\s*<w:sectPr\b[^>]*>.*?</w:sectPr>\s*$', '', inner, flags=re.DOTALL)
    inner = re.sub(r'\s*<w:sectPr\b[^>]*/>\s*$', '', inner, flags=re.DOTALL)

    return inner.strip()

def insert_before_closing_body(target_doc_xml_bytes: bytes, new_content_xml: str) -> bytes:
    """
    Inserts new_content_xml into the target document's body,
    just before the </w:body> tag (or before the final w:sectPr if present).
    """
    content = target_doc_xml_bytes.decode("utf-8")

    body_end = content.rfind("</w:body>")
    if body_end == -1:
        raise ValueError("Could not find </w:body> in target document.xml")

    # Check if there's a sectPr just before </w:body>
    # We want to keep sectPr at the END of the body (it defines the last section's page layout)
    before_body_end = content[:body_end]

    # Find the last <w:sectPr> that is a direct child of body
    sectpr_match = re.search(r'(<w:sectPr\b[^>]*>.*?</w:sectPr>)\s*$', before_body_end, re.DOTALL)
    sectpr_self_closing = re.search(r'(<w:sectPr\b[^>]*/>)\s*$', before_body_end, re.DOTALL)

    if sectpr_match:
        insert_pos = sectpr_match.start()
    elif sectpr_self_closing:
        insert_pos = sectpr_self_closing.start()
    else:
        insert_pos = body_end

    result = (
        content[:insert_pos]
        + "\n" + new_content_xml + "\n"
        + content[insert_pos:]
    )

    return result.encode("utf-8")

def merge_numbering(new_zip: Path, target_zip: Path, temp_dir: Path):
    """
    If new_sections.docx has numbering.xml, merge its abstract/concrete numbering
    into the target's numbering.xml, remapping IDs to avoid conflicts.
    Returns a dict mapping old abstract numId -> new abstract numId,
    and old numId -> new numId (for updating document.xml references).
    """
    new_files = list_zip_files(new_zip)
    target_files = list_zip_files(target_zip)

    has_new_numbering = "word/numbering.xml" in new_files
    has_target_numbering = "word/numbering.xml" in target_files

    if not has_new_numbering:
        return {}, {}

    new_numbering_xml = read_file_from_zip(new_zip, "word/numbering.xml").decode("utf-8")

    if not has_target_numbering:
        # Just use new numbering as-is
        return None, None  # Signal to copy new numbering directly

    target_numbering_xml = read_file_from_zip(target_zip, "word/numbering.xml").decode("utf-8")

    # Parse both
    ET.register_namespace("w", "http://schemas.openxmlformats.org/wordprocessingml/2006/main")
    ET.register_namespace("w14", "http://schemas.microsoft.com/office/word/2010/wordml")
    ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")

    # Find highest IDs in target
    target_abs_ids = [int(m) for m in re.findall(r'w:abstractNumId="(\d+)"', target_numbering_xml)]
    target_num_ids = [int(m) for m in re.findall(r'<w:num\s+w:numId="(\d+)"', target_numbering_xml)]

    max_abs_id = max(target_abs_ids) if target_abs_ids else 0
    max_num_id = max(target_num_ids) if target_num_ids else 0

    # Find IDs in new numbering
    new_abs_ids = list(set(int(m) for m in re.findall(r'<w:abstractNum\s+w:abstractNumId="(\d+)"', new_numbering_xml)))
    new_num_ids = list(set(int(m) for m in re.findall(r'<w:num\s+w:numId="(\d+)"', new_numbering_xml)))

    # Build remapping
    abs_remap = {}
    for old_id in sorted(new_abs_ids):
        max_abs_id += 1
        abs_remap[old_id] = max_abs_id

    num_remap = {}
    for old_id in sorted(new_num_ids):
        max_num_id += 1
        num_remap[old_id] = max_num_id

    # Apply remapping to new numbering XML
    remapped_new = new_numbering_xml

    # Remap abstractNumId references in abstractNum elements
    for old_id, new_id in sorted(abs_remap.items(), reverse=True):
        remapped_new = re.sub(
            r'(<w:abstractNum\s+w:abstractNumId=")' + str(old_id) + r'"',
            r'\g<1>' + str(new_id) + '"',
            remapped_new
        )

    # Remap numId references in num elements
    for old_id, new_id in sorted(num_remap.items(), reverse=True):
        remapped_new = re.sub(
            r'(<w:num\s+w:numId=")' + str(old_id) + r'"',
            r'\g<1>' + str(new_id) + '"',
            remapped_new
        )

    # Also remap the w:abstractNumId references inside w:num elements
    for old_id, new_id in sorted(abs_remap.items(), reverse=True):
        remapped_new = re.sub(
            r'(<w:abstractNumId\s+w:val=")' + str(old_id) + r'"',
            r'\g<1>' + str(new_id) + '"',
            remapped_new
        )

    # Extract just the abstractNum and num elements from new numbering (not the root element)
    abstract_nums = re.findall(r'<w:abstractNum\b.*?</w:abstractNum>', remapped_new, re.DOTALL)
    num_elements = re.findall(r'<w:num\b[^>]*w:numId="\d+"[^>]*>.*?</w:num>', remapped_new, re.DOTALL)

    # Inject into target numbering (before </w:numbering>)
    new_content = "\n".join(abstract_nums) + "\n" + "\n".join(num_elements)
    merged = target_numbering_xml.replace("</w:numbering>", new_content + "\n</w:numbering>")

    # Save merged numbering to temp dir
    num_path = temp_dir / "numbering.xml"
    num_path.write_text(merged, encoding="utf-8")

    return abs_remap, num_remap

def remap_numids_in_doc(doc_xml: bytes, num_remap: dict) -> bytes:
    """Remap w:numId val references in document.xml"""
    if not num_remap:
        return doc_xml
    content = doc_xml.decode("utf-8")
    for old_id, new_id in sorted(num_remap.items(), reverse=True):
        content = re.sub(
            r'(<w:numId\s+w:val=")' + str(old_id) + r'"',
            r'\g<1>' + str(new_id) + '"',
            content
        )
    return content.encode("utf-8")

def merge_styles(new_zip: Path, target_zip: Path, temp_dir: Path):
    """
    Check if new_sections.docx has any styles not in target. If so, add them.
    Returns set of style IDs added.
    """
    new_files = list_zip_files(new_zip)
    target_files = list_zip_files(target_zip)

    if "word/styles.xml" not in new_files:
        return set()

    new_styles_xml = read_file_from_zip(new_zip, "word/styles.xml").decode("utf-8")

    if "word/styles.xml" not in target_files:
        return set()

    target_styles_xml = read_file_from_zip(target_zip, "word/styles.xml").decode("utf-8")

    # Find styleIds in target
    target_style_ids = set(re.findall(r'w:styleId="([^"]+)"', target_styles_xml))
    new_style_ids = set(re.findall(r'w:styleId="([^"]+)"', new_styles_xml))

    missing = new_style_ids - target_style_ids

    if not missing:
        return set()

    # Extract the missing style elements
    added = set()
    new_elements = []
    for style_id in missing:
        # Find the style element with this ID
        pattern = r'<w:style\b[^>]*w:styleId="' + re.escape(style_id) + r'"[^>]*>.*?</w:style>'
        match = re.search(pattern, new_styles_xml, re.DOTALL)
        if match:
            new_elements.append(match.group(0))
            added.add(style_id)

    if new_elements:
        merged = target_styles_xml.replace(
            "</w:styles>",
            "\n".join(new_elements) + "\n</w:styles>"
        )
        styles_path = temp_dir / "styles.xml"
        styles_path.write_text(merged, encoding="utf-8")

    return added

def repack_docx(original_zip: Path, output_path: Path, overrides: dict):
    """
    Repack the docx, replacing files listed in overrides dict.
    overrides: {"word/document.xml": bytes, ...}
    """
    import io
    buffer = io.BytesIO()
    with zipfile.ZipFile(original_zip, "r") as zin:
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename in overrides:
                    zout.writestr(item, overrides[item.filename])
                else:
                    zout.writestr(item, zin.read(item.filename))

    output_path.write_bytes(buffer.getvalue())

def process_target(target_path: Path):
    print(f"\nProcessing: {target_path.name}")

    # Step 1: Get new sections body content
    new_doc_xml = read_file_from_zip(NEW_SECTIONS, "word/document.xml")
    new_body_inner = extract_body_inner_xml(new_doc_xml)
    print(f"  New body content: {len(new_body_inner)} chars")

    # Step 2: Get target document.xml
    target_doc_xml = read_file_from_zip(target_path, "word/document.xml")
    print(f"  Target doc.xml size: {len(target_doc_xml)} bytes")

    # Step 3: Process numbering
    temp_dir = DOCS_DIR / f"temp_{target_path.stem}"
    temp_dir.mkdir(exist_ok=True)

    abs_remap, num_remap = merge_numbering(NEW_SECTIONS, target_path, temp_dir)
    print(f"  Numbering remap: abs={abs_remap}, num={num_remap}")

    # Step 4: If we have a num_remap, apply to the new body content
    if num_remap:
        new_body_inner_remapped = new_body_inner
        for old_id, new_id in sorted(num_remap.items(), reverse=True):
            new_body_inner_remapped = re.sub(
                r'(<w:numId\s+w:val=")' + str(old_id) + r'"',
                r'\g<1>' + str(new_id) + '"',
                new_body_inner_remapped
            )
        new_body_inner = new_body_inner_remapped

    # Step 5: Merge styles
    added_styles = merge_styles(NEW_SECTIONS, target_path, temp_dir)
    print(f"  Added styles: {added_styles}")

    # Step 6: Insert new content into target document
    merged_doc_xml = insert_before_closing_body(target_doc_xml, new_body_inner)
    print(f"  Merged doc.xml size: {len(merged_doc_xml)} bytes")

    # Step 7: Build overrides dict
    overrides = {"word/document.xml": merged_doc_xml}

    # Add merged numbering if we modified it
    numbering_file = temp_dir / "numbering.xml"
    if numbering_file.exists():
        overrides["word/numbering.xml"] = numbering_file.read_bytes()
        print("  Added merged numbering.xml")
    elif abs_remap is None:
        # New numbering was needed but target had none - copy from new_sections
        overrides["word/numbering.xml"] = read_file_from_zip(NEW_SECTIONS, "word/numbering.xml")
        print("  Copied new numbering.xml (target had none)")

    # Add merged styles if we added any
    styles_file = temp_dir / "styles.xml"
    if styles_file.exists():
        overrides["word/styles.xml"] = styles_file.read_bytes()
        print("  Added merged styles.xml")

    # Step 8: Repack
    backup_path = target_path.with_suffix(".docx.bak")
    shutil.copy2(target_path, backup_path)
    print(f"  Backed up to: {backup_path.name}")

    repack_docx(target_path, target_path, overrides)
    print(f"  Repacked: {target_path.name}")

    # Cleanup temp
    shutil.rmtree(temp_dir)
    print(f"  Done: {target_path.name}")

if __name__ == "__main__":
    for target in TARGETS:
        if not target.exists():
            print(f"ERROR: {target} not found")
            continue
        process_target(target)
    print("\nAll done.")
