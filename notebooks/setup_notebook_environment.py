import sys
from pathlib import Path

# Calculate the path to the root of the project
project_root = Path(__file__).parent.parent

# Append the project root to the sys.path if it's not already included
if str(project_root.resolve()) not in sys.path:
    sys.path.append(str(project_root.resolve()))
