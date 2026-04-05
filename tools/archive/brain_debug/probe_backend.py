import requests
import json

url = "http://localhost:8001/api/floorplan/init"
files = {'file': ('test.m4a', open('test.m4a', 'rb'), 'audio/mp4')}
data = {
    'property_type': 'Test',
    'floors': 1,
    'user_id': 'probe'
}

print(f"Testing {url}...")
try:
    response = requests.post(url, files=files, data=data)
    print(f"Status: {response.status_code}")
    print("Body Suggestion:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
except Exception as e:
    print(f"Connection Error: {e}")
