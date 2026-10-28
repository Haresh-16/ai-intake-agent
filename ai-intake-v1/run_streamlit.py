#!/usr/bin/env python
"""Convenience launcher for Streamlit defendant intake UI."""

import subprocess
import sys
from pathlib import Path


def main():
    """Run the Streamlit app."""
    app_path = Path(__file__).parent / "streamlit_app" / "main.py"

    if not app_path.exists():
        print(f"Error: {app_path} not found", file=sys.stderr)
        sys.exit(1)

    print("Starting Streamlit defendant intake UI...")
    print(f"App will be available at: http://localhost:8501")
    print("Press Ctrl+C to stop the server")
    print("-" * 60)

    # Run streamlit
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.port",
            "8501",
            "--server.headless",
            "true",
        ]
    )


if __name__ == "__main__":
    main()
