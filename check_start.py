
import sys
import os

# Ensure we don't pick up root main.py by prioritizing server directory
server_path = os.path.join(os.getcwd(), 'server')
sys.path.insert(0, server_path)

try:
    print(f"Attempting to import main from {server_path}...")
    # This should load server/main.py
    import main
    print("Import successful! Server file is valid.")
    print(f"Main file location: {main.__file__}")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
