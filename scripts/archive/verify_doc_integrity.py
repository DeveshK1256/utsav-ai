import re
import sys

def slugify(text):
    # GitHub markdown anchor generation
    # remove punctuation except hyphens, spaces to hyphens, lowercase
    text = text.strip().lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text

def main():
    with open("docs/UTSAV_MASTER_DOC.md", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Check for replacement character
    replacement_char_count = content.count('\ufffd')
    print(f"UTF-8 replacement characters (\\ufffd): {replacement_char_count}")
    assert replacement_char_count == 0, f"Found {replacement_char_count} replacement characters!"

    # 2. Extract TOC anchors
    # Look in the Table of Contents block
    toc_match = re.search(r'## Table of Contents(.*?)(?=\n## |\Z)', content, re.DOTALL)
    assert toc_match, "TOC block not found"
    toc_text = toc_match.group(1)

    toc_links = re.findall(r'\[([^\]]+)\]\(#([^\)]+)\)', toc_text)
    print(f"Total TOC links: {len(toc_links)}")

    # Extract all headings from document
    headings = re.findall(r'^(#{1,6})\s+(.*)$', content, re.MULTILINE)
    generated_anchors = {}
    for h_level, h_text in headings:
        # Strip trailing formatting or links in heading if any
        clean_text = re.sub(r'<[^>]+>', '', h_text).strip()
        anchor = slugify(clean_text)
        generated_anchors[anchor] = clean_text

    missing = []
    for title, anchor in toc_links:
        if anchor not in generated_anchors:
            # Check if slight slug difference
            missing.append((title, anchor))

    if missing:
        print(f"Warning: {len(missing)} TOC anchors did not match generated anchors:")
        for title, anchor in missing[:10]:
            print(f"  TOC: '{title}' -> #{anchor}")
    else:
        print("All TOC links resolved perfectly!")

    # Specifically check F16 anchor
    assert "416-f16-invitation-card-generator" in generated_anchors, "F16 anchor missing from headers!"
    print("F16 anchor '#416-f16-invitation-card-generator' verified in headers!")

if __name__ == "__main__":
    main()
