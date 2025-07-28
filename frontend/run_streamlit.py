"""
Script to run the Streamlit application
"""
import subprocess
import sys
import os

if __name__ == "__main__":
    # Run streamlit from the frontend directory
    frontend_dir = os.path.dirname(os.path.abspath(__file__))
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        os.path.join(frontend_dir, "streamlit_app.py"),
        "--server.port=8501",
        "--server.address=0.0.0.0"
    ])