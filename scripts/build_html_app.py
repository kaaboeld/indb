import markdown
import os

INPUT_FILE = "INDB_Documentation_Complete.md"
OUTPUT_FILE = "INDB_Documentation.html"

# CSS similar to GitHub Markdown/VS Code for a clean, "App-like" feel
CSS = """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        line-height: 1.6;
        padding: 40px;
        max-width: 900px;
        margin: 0 auto;
        color: #24292e;
        background-color: #ffffff;
    }
    h1, h2, h3 { border-bottom: 1px solid #eaecef; padding-bottom: .3em; }
    code { background-color: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px; font-family: SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace; font-size: 85%; }
    pre { background-color: #f6f8fa; padding: 16px; overflow: auto; border-radius: 6px; }
    pre code { background-color: transparent; padding: 0; }
    blockquote { padding: 0 1em; color: #6a737d; border-left: 0.25em solid #dfe2e5; }
    table { border-collapse: collapse; width: 100%; margin-bottom: 16px; }
    th, td { padding: 6px 13px; border: 1px solid #dfe2e5; }
    tr:nth-child(2n) { background-color: #f6f8fa; }
    a { color: #0366d6; text-decoration: none; }
    a:hover { text-decoration: underline; }
    
    /* Navigation Sidebar (Simple TOC) */
    .toc {
        background: #f8f9fa;
        padding: 20px;
        border: 1px solid #e1e4e8;
        border-radius: 6px;
        margin-bottom: 30px;
    }
    .toc ul { list-style: none; padding-left: 0; }
    .toc li { margin-bottom: 5px; }

    /* Dark Mode Support (Automatic) */
    @media (prefers-color-scheme: dark) {
        body { background-color: #0d1117; color: #c9d1d9; }
        h1, h2, h3, th, td { border-color: #30363d; }
        code { background-color: #161b22; }
        pre { background-color: #161b22; }
        blockquote { color: #8b949e; border-color: #30363d; }
        tr:nth-child(2n) { background-color: #161b22; }
        a { color: #58a6ff; }
        .toc { background: #161b22; border-color: #30363d; }
    }
</style>
"""

def generate_html():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found. Run bundle_docs.py first.")
        return

    print("Reading Markdown...")
    with open(INPUT_FILE, "r") as f:
        text = f.read()

    print("Converting to HTML...")
    html_content = markdown.markdown(
        text, 
        extensions=['fenced_code', 'tables', 'toc', 'codehilite']
    )

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>INDB Documentation</title>
        {CSS}
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    with open(OUTPUT_FILE, "w") as f:
        f.write(full_html)

    print(f"✅ Generated Standalone HTML App: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_html()
