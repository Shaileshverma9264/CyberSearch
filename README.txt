CYBERSEARCH FRONTEND
====================

Files:
- index.html
- style.css
- script.js
- server.py

The frontend sends:
POST /api/search
Content-Type: application/json

{
  "query": "your_query"
}

IMPORTANT:
Keep your private API key on your server. Do not place it in
index.html or script.js.

The UI expects an authorized backend response similar to:

{
  "status": true,
  "query": "your_query",
  "data": {
    "source1": {
      "title": "Authorized Source",
      "description": "Description",
      "records": [
        {
          "FullName": "Example",
          "Region": "India"
        }
      ]
    }
  },
  "response_time_ms": 42
}

The frontend includes a client-side blocklist for some sensitive
field names, but privacy filtering should also be enforced server-side.

Vehicle lookup uses the provider key configured on the server. Set the
VEHICLE_API_KEY environment variable before starting server.py; the default
value is "30day". Do not put provider keys in script.js or index.html.

IFSC lookup uses the same provider API. Set IFSC_API_KEY before starting
server.py if it requires a key different from the default "30day".
