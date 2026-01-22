
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'server'))

from server.core.tdx_client import tdx_client

def test_tdx():
    print("Testing TDX connection...")
    try:
        # Test connection
        if tdx_client.connect():
            print("Connected successfully.")
        else:
            print("Connection failed.")
            return

        # Test fetching 600001
        print("Fetching quote for 600001...")
        quotes = tdx_client.get_quotes(["600001"])
        print(f"Quotes: {quotes}")

        # Test fetching list
        print("Fetching security list (first 10)...")
        lst = tdx_client.get_security_list(1, 0)
        if lst:
            print(f"List (first 5): {lst[:5]}")
        else:
            print("List is empty.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_tdx()
