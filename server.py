#!/usr/bin/env python3
import json
import os
import re
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib import parse, request, error

HOST = "0.0.0.0"
PORT = 8000
ROOT = os.path.dirname(os.path.abspath(__file__))
REMOTE_API = "https://deeposint.felixrdx.xyz/api/developer/Cyb3rB4nn3r/"
API_KEY = "58c49cb2dbbf8dc53009705ecd7c4132"
VEHICLE_API = "https://api.sarkariallupdates.com/api"
VEHICLE_API_KEY = os.environ.get("VEHICLE_API_KEY", "30day")
IFSC_API_KEY = os.environ.get("IFSC_API_KEY", "30day")
VEHICLE_FIELDS = {
    "registration_number": "Registration number",
    "registration_date": "Registration date",
    "rc_status": "RC status",
    "vehicle": "Vehicle",
    "manufacturer": "Manufacturer",
    "variant": "Variant",
    "vehicle_type": "Vehicle type",
    "vehicle_class": "Vehicle class",
    "fuel_type": "Fuel type",
    "cubic_capacity": "Cubic capacity",
    "manufacturing_month_year": "Manufacturing month/year",
    "seat_capacity": "Seat capacity",
    "registered_at": "Registered at",
    "rto": "RTO",
    "insurance_company": "Insurance company",
    "insurance_upto": "Insurance valid until",
    "pucc_valid_upto": "PUCC valid until",
}


def normalize_vehicle_payload(payload, registration):
    if not isinstance(payload, dict):
        return None

    if payload.get("status") is False:
        return None

    source = payload.get("data")
    if not isinstance(source, dict):
        source = payload

    if not isinstance(source, dict):
        return None

    vehicle = {
        label: source[key]
        for key, label in VEHICLE_FIELDS.items()
        if source.get(key) not in (None, "")
    }
    if not vehicle:
        return None

    return {
        "status": True,
        "query": registration,
        "data": {"vehicle": {"title": "Vehicle details", "records": [vehicle]}},
        "response_time_ms": int(float(payload.get("response_time_seconds", 0)) * 1000),
    }


def build_vehicle_api_url(registration):
    encoded_registration = parse.quote(registration, safe="")
    encoded_key = parse.quote(VEHICLE_API_KEY, safe="")
    return f"{VEHICLE_API}?=vehicle_full&key={encoded_key}&xr={encoded_registration}"


def build_ifsc_api_url(ifsc):
    encoded_ifsc = parse.quote(ifsc, safe="")
    encoded_key = parse.quote(IFSC_API_KEY, safe="")
    return f"{VEHICLE_API}?=ifse&key={encoded_key}&ifse={encoded_ifsc}"


class ProxyHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/vehicle"):
            self.handle_vehicle_search()
            return
        if self.path.startswith("/api/ifsc"):
            self.handle_ifsc_search()
            return
        if self.path.startswith("/api/search"):
            self.handle_search()
            return
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/search"):
            self.handle_search()
            return
        super().do_POST()

    def handle_vehicle_search(self):
        params = parse.parse_qs(parse.urlsplit(self.path).query)
        registration = params.get("registration", [""])[0].strip().upper()
        if not 4 <= len(registration) <= 20 or not all(
            char.isalnum() or char in " -" for char in registration
        ):
            self.send_json(400, {"status": False, "message": "Invalid registration number"})
            return

        target_url = build_vehicle_api_url(registration)
        try:
            req = request.Request(target_url, headers={"User-Agent": "CyberSearch-Proxy/1.0", "Accept": "application/json"})
            with request.urlopen(req, timeout=25) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))

            normalized = normalize_vehicle_payload(payload, registration)
            if normalized is None:
                self.send_json(502, {"status": False, "message": "Vehicle API did not return displayable details."})
                return

            self.send_json(200, normalized)
        except error.HTTPError as exc:
            try:
                error_payload = json.loads(exc.read().decode("utf-8", errors="replace"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                error_payload = None
            error_code = (
                error_payload.get("error_code")
                if isinstance(error_payload, dict)
                else None
            )
            detail = f" (error code {error_code})" if error_code is not None else ""
            self.send_json(
                502,
                {
                    "status": False,
                    "message": (
                        f"Vehicle provider rejected the request{detail}. "
                        "Check the provider API key/plan and registration number."
                    ),
                },
            )
        except error.URLError:
            self.send_json(502, {"status": False, "message": "Could not connect to the vehicle API."})
        except json.JSONDecodeError:
            self.send_json(502, {"status": False, "message": "Vehicle API returned invalid JSON."})
        except Exception as exc:
            self.send_json(502, {"status": False, "message": f"Vehicle API request failed ({type(exc).__name__})."})

    def handle_ifsc_search(self):
        params = parse.parse_qs(parse.urlsplit(self.path).query)
        ifsc = params.get("ifsc", [""])[0].strip().upper()
        if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", ifsc):
            self.send_json(400, {"status": False, "message": "Enter a valid 11-character IFSC code."})
            return

        try:
            req = request.Request(
                build_ifsc_api_url(ifsc),
                headers={"User-Agent": "CyberSearch-Proxy/1.0", "Accept": "application/json"},
            )
            with request.urlopen(req, timeout=25) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))

            if (
                not isinstance(payload, dict)
                or payload.get("status") is not True
                or not isinstance(payload.get("data"), dict)
            ):
                message = payload.get("message") if isinstance(payload, dict) else None
                self.send_json(
                    502,
                    {"status": False, "message": message or "IFSC API did not return bank details."},
                )
                return

            self.send_json(200, payload)
        except error.HTTPError as exc:
            try:
                error_payload = json.loads(exc.read().decode("utf-8", errors="replace"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                error_payload = None
            error_code = (
                error_payload.get("error_code")
                if isinstance(error_payload, dict)
                else None
            )
            detail = f" (error code {error_code})" if error_code is not None else ""
            self.send_json(
                502,
                {
                    "status": False,
                    "message": (
                        f"IFSC provider rejected the request{detail}. "
                        "Check the provider API key/plan and IFSC code."
                    ),
                },
            )
        except error.URLError:
            self.send_json(502, {"status": False, "message": "Could not connect to the IFSC API."})
        except json.JSONDecodeError:
            self.send_json(502, {"status": False, "message": "IFSC API returned invalid JSON."})
        except Exception as exc:
            self.send_json(502, {"status": False, "message": f"IFSC API request failed ({type(exc).__name__})."})

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_search(self):
        query = None
        api_key = API_KEY

        if "?" in self.path:
            parsed = parse.urlsplit(self.path)
            params = parse.parse_qs(parsed.query)
            query = params.get("query", [None])[0]
            if params.get("key"):
                api_key = params.get("key", [API_KEY])[0]

        if query is None and self.command == "POST":
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                if content_length > 0:
                    body = self.rfile.read(content_length)
                    data = json.loads(body.decode("utf-8", errors="replace"))
                    if isinstance(data, dict):
                        query = data.get("query")
                        if data.get("key"):
                            api_key = data.get("key")
            except (TypeError, ValueError, json.JSONDecodeError):
                query = None

        if not query:
            self.send_json(400, {"status": False, "message": "Missing query"})
            return

        target_url = f"{REMOTE_API}?{parse.urlencode({'key': api_key, 'query': query})}"
        try:
            req = request.Request(target_url, headers={"User-Agent": "CyberSearch-Proxy/1.0", "Accept": "application/json"})
            with request.urlopen(req, timeout=25) as resp:
                payload = resp.read()
            body = payload.decode("utf-8", errors="replace")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
        except Exception as exc:
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            message = {"status": False, "message": f"Proxy request failed: {exc}"}
            self.wfile.write(json.dumps(message).encode("utf-8"))

    def _serve_static(self):
        os.chdir(ROOT)
        return SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    os.chdir(ROOT)
    httpd = ThreadingHTTPServer((HOST, PORT), ProxyHandler)
    print(f"CyberSearch server running at http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        httpd.server_close()
