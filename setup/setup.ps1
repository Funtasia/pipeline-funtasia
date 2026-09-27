# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install nipple
pip install git+https://github.com/Funtasia/pipeline-funtasia

# Start setup
nipple setup
