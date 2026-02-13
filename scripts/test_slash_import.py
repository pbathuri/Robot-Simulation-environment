import requests
import sys

def test_import_with_slash():
    # Simulate the frontend request for an item with a slash
    # Frontend: /api/robodk/import/ABB%20CRB%201300-7%2F1.4
    # We will send the decoded path because requests/curl usually send the path.
    # But wait, if we use requests.get, we provide the URL.
    
    base_url = "http://localhost:8000"
    item_name = "ABB CRB 1300-7/1.4"
    
    # Client-side encoding (like browser)
    import urllib.parse
    encoded_name = urllib.parse.quote(item_name, safe='')
    
    url = f"{base_url}/api/robodk/import/{encoded_name}"
    print(f"Testing URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("SUCCESS: Route matched and handled slash.")
        elif response.status_code == 404:
            print("FAILURE: Route not found (404). Path param fix might not be working or name mismatch.")
        else:
            print("FAILURE: Other error.")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_import_with_slash()
