import os
import re
import argparse
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from playwright.sync_api import sync_playwright

MAIN_ANCHOR = "main-page"

visited = set()
collected_pages = []

HEX_ID_RE = re.compile(
    r"^(?:[0-9a-f]{32}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})$",
    re.I,
)


def load_html(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def resolve_path(base_path: str, href: str) -> str:
    decoded = unquote(href)
    base_dir = Path(base_path).resolve().parent
    return str((base_dir / decoded).resolve())


def pretty_title_from_filename(path: str) -> str:
    stem = Path(path).stem
    stem = re.sub(r"\s+[0-9a-f]{32}$", "", stem, flags=re.I).strip()
    return stem


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def looks_like_id(text: str) -> bool:
    return bool(HEX_ID_RE.fullmatch(normalize_text(text)))


def fix_asset_paths(soup: BeautifulSoup, page_path: str) -> None:
    base_dir = Path(page_path).resolve().parent

    for img in soup.find_all("img"):
        src = img.get("src")
        if not src or src.startswith(("http://", "https://", "data:")):
            continue

        abs_path = (base_dir / unquote(src)).resolve()
        if abs_path.exists():
            img["src"] = abs_path.as_uri()

    for source in soup.find_all("source"):
        src = source.get("src")
        if not src or src.startswith(("http://", "https://", "data:")):
            continue

        abs_path = (base_dir / unquote(src)).resolve()
        if abs_path.exists():
            source["src"] = abs_path.as_uri()


def clean_main_header(soup: BeautifulSoup, page_path: str) -> None:
    if not soup.body:
        return

    page_title = pretty_title_from_filename(page_path)

    for node in list(soup.body.contents)[:8]:
        if isinstance(node, NavigableString):
            if not str(node).strip():
                node.extract()
            continue

        if not isinstance(node, Tag):
            continue

        text = normalize_text(node.get_text(" ", strip=True))

        if looks_like_id(text):
            node.extract()
            continue

        if node.name in ("h1", "h2", "h3") and page_title in text:
            node.clear()
            node.append(page_title)
            break


def sanitize_subpage_header(soup: BeautifulSoup) -> None:
    header = soup.find("header")
    if not header:
        return

    for icon in header.select(".page-header-icon"):
        icon.decompose()

    for desc in header.select(".page-description"):
        desc.decompose()

    for child in list(header.contents):
        if isinstance(child, NavigableString):
            if not str(child).strip():
                child.extract()
            continue

        if isinstance(child, Tag):
            if child.name == "h1" and "page-title" in (child.get("class") or []):
                continue
            child.decompose()


def collect_pages(base_path: str, soup: BeautifulSoup) -> None:
    for link in list(soup.find_all("a")):
        href = link.get("href")
        if not href or not href.lower().endswith(".html"):
            continue

        full_path = resolve_path(base_path, href)

        if full_path in visited:
            continue

        if not os.path.exists(full_path):
            continue

        visited.add(full_path)
        anchor_id = f"page-{len(collected_pages)}"
        print(f"Collected: {full_path}")

        sub_html = load_html(full_path)
        sub_soup = BeautifulSoup(sub_html, "lxml")

        sanitize_subpage_header(sub_soup)
        fix_asset_paths(sub_soup, full_path)

        collected_pages.append(
            {
                "path": full_path,
                "anchor": anchor_id,
                "soup": sub_soup,
            }
        )

        link["href"] = f"#{anchor_id}"
        collect_pages(full_path, sub_soup)


def append_page(target_soup: BeautifulSoup, page_info: dict) -> None:
    wrapper = target_soup.new_tag("div")
    wrapper["id"] = page_info["anchor"]
    wrapper["style"] = "page-break-before: always; break-before: page;"

    nav = target_soup.new_tag("div")
    nav["style"] = "margin-bottom: 10px;"

    back = target_soup.new_tag("a")
    back["href"] = f"#{MAIN_ANCHOR}"
    back.string = "⬅ Back to main"

    nav.append(back)
    wrapper.append(nav)

    source = page_info["soup"].body if page_info["soup"].body else page_info["soup"]
    for child in list(source.contents):
        wrapper.append(child)

    target_soup.body.append(wrapper)


def build_combined_html(start_file: str) -> str:
    print("Loading main file...")

    html = load_html(start_file)
    soup = BeautifulSoup(html, "lxml")

    visited.add(str(Path(start_file).resolve()))

    clean_main_header(soup, start_file)
    fix_asset_paths(soup, start_file)

    if soup.body is None:
        raise RuntimeError("Main HTML has no <body> tag")

    main_anchor = soup.new_tag("div")
    main_anchor["id"] = MAIN_ANCHOR
    soup.body.insert(0, main_anchor)

    print("Collecting pages...")
    collect_pages(start_file, soup)

    sep = soup.new_tag("div")
    sep["style"] = "page-break-before: always;"
    soup.body.append(sep)

    print("Appending pages...")
    for page in collected_pages:
        append_page(soup, page)

    style = soup.new_tag("style")
    style.string = """
    body { font-size: 14px !important; line-height: 1.4; }
    p, li, td, th, div { font-size: 14px !important; }
    h1 { font-size: 20px !important; }
    h2 { font-size: 18px !important; }
    h3 { font-size: 16px !important; }
    a { text-decoration: none; }
    .page-header-icon, .page-description { display: none !important; }
    """

    if soup.head is None:
        head = soup.new_tag("head")
        soup.insert(0, head)

    soup.head.append(style)

    # OUTPUT IS NOW NEXT TO INPUT FILE
    output_dir = Path(start_file).resolve().parent
    output_html = output_dir / "combined.html"

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"Combined HTML saved: {output_html}")
    return str(output_html)


def html_to_pdf(html_path: str, start_file: str) -> None:
    print("Generating PDF...")

    output_dir = Path(start_file).resolve().parent
    output_pdf = output_dir / "Export.pdf"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        page.goto(Path(html_path).resolve().as_uri(), wait_until="load", timeout=0)
        page.emulate_media(media="print")
        page.wait_for_timeout(3000)

        page.pdf(
            path=str(output_pdf),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
        )

        browser.close()

    print(f"PDF created: {output_pdf}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Path to main HTML file")
    args = parser.parse_args()

    start_file = args.file

    if not os.path.exists(start_file):
        raise FileNotFoundError(start_file)

    combined_html = build_combined_html(start_file)
    html_to_pdf(combined_html, start_file)


if __name__ == "__main__":
    main()
