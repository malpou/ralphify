#!/usr/bin/env python3
"""Audit website/index.html for SEO best practices."""

import sys
from html.parser import HTMLParser
from pathlib import Path

HTML_FILE = Path("website/index.html")


class SEOParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title_text = ""
        self.meta_tags = {}  # name/property -> content
        self.h1_count = 0
        self.h1_text = ""
        self.in_h1 = False
        self.has_lang = False
        self.has_viewport = False
        self.has_canonical = False
        self.images_without_alt = []
        self.has_json_ld = False
        self.heading_order = []  # list of (level, line)
        self.in_heading = 0
        self.current_line = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self.current_line = self.getpos()[0]

        if tag == "html":
            if "lang" in attrs_dict:
                self.has_lang = True

        if tag == "title":
            self.in_title = True

        if tag == "meta":
            name = attrs_dict.get("name", "")
            prop = attrs_dict.get("property", "")
            content = attrs_dict.get("content", "")
            if name:
                self.meta_tags[name] = content
            if prop:
                self.meta_tags[prop] = content
            if name == "viewport":
                self.has_viewport = True

        if tag == "link":
            if attrs_dict.get("rel") == "canonical":
                self.has_canonical = True

        if tag == "img":
            if "alt" not in attrs_dict or not attrs_dict["alt"].strip():
                src = attrs_dict.get("src", "unknown")
                self.images_without_alt.append(f"line {self.getpos()[0]}: {src}")

        if tag == "script":
            if attrs_dict.get("type") == "application/ld+json":
                self.has_json_ld = True

        if tag == "h1":
            self.h1_count += 1
            self.in_h1 = True

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            self.heading_order.append((level, self.getpos()[0]))
            self.in_heading = level

    def handle_data(self, data):
        if self.in_title:
            self.title_text += data
        if self.in_h1:
            self.h1_text += data

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "h1":
            self.in_h1 = False
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.in_heading = 0


def main():
    if not HTML_FILE.exists():
        print(f"FAIL: {HTML_FILE} not found")
        sys.exit(1)

    html = HTML_FILE.read_text()
    parser = SEOParser()
    parser.feed(html)

    issues = []
    warnings = []

    # Title tag
    title = parser.title_text.strip()
    if not title:
        issues.append("Missing <title> tag")
    elif len(title) < 30:
        warnings.append(f"Title too short ({len(title)} chars, aim for 50-60): \"{title}\"")
    elif len(title) > 70:
        warnings.append(f"Title too long ({len(title)} chars, aim for 50-60): \"{title}\"")

    # Meta description
    desc = parser.meta_tags.get("description", "")
    if not desc:
        issues.append("Missing meta description")
    elif len(desc) < 120:
        warnings.append(f"Meta description short ({len(desc)} chars, aim for 150-160)")
    elif len(desc) > 170:
        warnings.append(f"Meta description long ({len(desc)} chars, aim for 150-160)")

    # Language
    if not parser.has_lang:
        issues.append("Missing lang attribute on <html> tag")

    # Viewport
    if not parser.has_viewport:
        issues.append("Missing viewport meta tag")

    # Canonical URL
    if not parser.has_canonical:
        warnings.append("Missing canonical URL (<link rel=\"canonical\" href=\"...\">)")

    # Open Graph
    for og in ("og:title", "og:description", "og:image", "og:url", "og:type"):
        if og not in parser.meta_tags:
            warnings.append(f"Missing {og} meta tag")

    # Twitter Card
    if "twitter:card" not in parser.meta_tags:
        warnings.append("Missing twitter:card meta tag")

    # H1 tag
    if parser.h1_count == 0:
        issues.append("Missing <h1> tag")
    elif parser.h1_count > 1:
        warnings.append(f"Multiple <h1> tags found ({parser.h1_count}) — use only one")

    # Heading hierarchy
    if parser.heading_order:
        prev_level = 0
        for level, line in parser.heading_order:
            if prev_level > 0 and level > prev_level + 1:
                warnings.append(f"Heading skip at line {line}: h{prev_level} -> h{level} (don't skip levels)")
            prev_level = level

    # Images without alt
    for img in parser.images_without_alt:
        warnings.append(f"Image missing alt text: {img}")

    # Structured data
    if not parser.has_json_ld:
        warnings.append("No JSON-LD structured data found (recommended for rich search results)")

    # Print results
    if issues:
        print(f"ISSUES ({len(issues)}):")
        for issue in issues:
            print(f"  [FAIL] {issue}")

    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"  [WARN] {warning}")

    if not issues and not warnings:
        print("OK: All SEO checks passed")
        sys.exit(0)
    elif issues:
        print(f"\n{len(issues)} issue(s) must be fixed, {len(warnings)} warning(s) to consider.")
        sys.exit(1)
    else:
        print(f"\nNo blocking issues. {len(warnings)} warning(s) to improve.")
        # Warnings alone don't fail the check — they guide the agent
        sys.exit(1)


if __name__ == "__main__":
    main()
