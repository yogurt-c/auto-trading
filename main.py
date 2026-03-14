"""Entry point for running the Streamlit app via PyCharm (or python main.py)."""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    app = Path(__file__).parent / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app)])
