import os
import datetime

DOCS_DIR = "docs"
OUTPUT_FILE = "INDB_Documentation_Complete.md"

# Order of files for logical reading
ORDER = [
    "index.md",
    "ROADMAP.md",
    "PHILOSOPHY.md",
    "architecture.md",
    "API.md",
    "PROTOCOLS.md",
    "AUTHENTICATION.md",
    "TYPING.md",
    "COGNITIVE_FIREWALL.md",
    "ecosystem.md",
    "cli.md",
    "DEPLOYMENT.md",
    "CONTRIBUTING.md"
]

def bundle():
    with open(OUTPUT_FILE, "w") as out:
        # Title Page
        out.write(f"# INDB Complete Documentation\n")
        out.write(f"**Generated**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        out.write(f"**Version**: v0.3.0 (Alpha)\n\n")
        out.write("---\n\n")
        
        # Table of Contents
        out.write("## Table of Contents\n\n")
        for filename in ORDER:
            if os.path.exists(os.path.join(DOCS_DIR, filename)):
                title = filename.replace(".md", "").replace("_", " ").title()
                out.write(f"- [{title}](#{filename.lower().replace('.', '').replace('_', '-')})\n")
        out.write("\n---\n\n")

        # Content
        for filename in ORDER:
            path = os.path.join(DOCS_DIR, filename)
            if os.path.exists(path):
                print(f"Propcessing {filename}...")
                with open(path, "r") as f:
                    content = f.read()
                    
                    # Add separator/header
                    out.write(f"<div id='{filename.lower().replace('.', '').replace('_', '-')}' />\n\n")
                    out.write(f"<!-- FILE: {filename} -->\n")
                    out.write(content)
                    out.write("\n\n---\n\n")
            else:
                print(f"Warning: {filename} not found.")

    print(f"✅ Documentation bundled into {OUTPUT_FILE}")

if __name__ == "__main__":
    bundle()
