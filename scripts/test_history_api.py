import requests
import json
import sys

URL = "http://localhost:8000/api/history"

def test_api():
    print(f">>> Testing API: {URL}")
    try:
        response = requests.get(URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ API Status: 200 OK")
            print(f"✅ Data Points Received: {len(data)}")
            if len(data) > 0:
                print("✅ Sample Data Structure:")
                print(json.dumps(data[-1], indent=2))
        else:
            print(f"❌ API Failed: Status {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print(">> TIP: Is the backend running? Try: ssh cobalt 'pm2 reload all'")
        sys.exit(1)

if __name__ == "__main__":
    test_api()
