#!/usr/bin/env python3
import os
import sys
import webview
import threading
import time

# Path to the MkDocs generated site
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    base_path = sys._MEIPASS
    site_path = os.path.join(base_path, "site", "index.html")
else:
    # Running as script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    site_path = os.path.join(current_dir, "..", "site", "index.html")

abs_site_path = os.path.abspath(site_path)

def open_docs():
    """Launch the documentation in a native window."""
    if not os.path.exists(abs_site_path):
        print(f"Error: Documentation build not found at {abs_site_path}")
        print("Please run 'mkdocs build' first.")
        sys.exit(1)

    # Calculate window size (approx 80% of typical screen)
    width = 1200
    height = 900

    print(f"📚 Launching INDB Documentation App...")
    print(f"   Source: {abs_site_path}")
    
    # Create a unified native window
    # Note: 'file://' protocol is required for local files
    webview.create_window(
        title='INDB Documentation v0.3.0',
        url=f'file://{abs_site_path}',
        width=width,
        height=height,
        resizable=True,
        text_select=True
    )
    
    # Start the GUI loop
    webview.start()

if __name__ == "__main__":
    try:
        open_docs()
    except Exception as e:
        print(f"❌ Failed to launch docs: {e}")
