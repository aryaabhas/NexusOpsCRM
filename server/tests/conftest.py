import os
import shutil
import sys
from pathlib import Path

import pytest

# Add server directory to python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables
os.environ["VECTOR_STORE_DIR"] = str(Path(__file__).parent / "test_data")
os.environ["JWT_SECRET_KEY"] = "test_secret_key"

@pytest.fixture(autouse=True)
def setup_and_teardown_test_data():
    test_data_dir = Path(__file__).parent / "test_data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    yield
    # Clean up test directories after each test run
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir)
