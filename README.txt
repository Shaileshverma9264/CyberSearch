CYBERSEARCH FRONTEND
====================

Files:
- index.html
- style.css
- script.js

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
