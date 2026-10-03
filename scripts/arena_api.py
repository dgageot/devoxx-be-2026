#!/usr/bin/env python3
"""Local synthetic arena. Run: python3 scripts/arena_api.py [--port 8090].

GET /health, /rules, /challenges/{challenge_id}, /catalog/{name}, /state,
/leaderboard, /matches/{match_id}, /. POST /spar {challenge_id,team,level};
/join {challenge_id,agent_id,team}. Matching sealed entries fight automatically.
POST /tournaments {tournament_id,challenge_id}, /tournaments/join {tournament_id,agent_id,team};
GET /tournaments/{id}. Fixed 32-player brackets advance automatically.
Sparring checks eligibility without sealing entries or awarding points.
Challenge manifests come from fixtures/arena-challenges.json; teams are checked
inside every new spar/join and automatic match. Results use sorted IDs as left/right. Restart to reset local in-memory state.
IDs are local demo labels, not authenticated identities.
"""

import argparse
import hashlib
import json
import threading
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from tournament import TournamentError, Tournaments

from arena_rules import (
    LEVELS,
    RULES_VERSION,
    SPARRING_RANKING,
    canonical_id,
    complete_pokemon,
    fight,
    rules_payload,
    sparring_team,
    valid_challenge,
    validate_team,
)

ROOT = Path(__file__).resolve().parent.parent
MAX_BODY = 4096
REQUEST_KEYS = {"/spar": {"challenge_id", "team", "level"},
                "/join": {"challenge_id", "agent_id", "team"},
                "/tournaments": {"tournament_id", "challenge_id"},
                "/tournaments/join": {"tournament_id", "agent_id", "team"}}


class RequestError(ValueError):
    def __init__(self, message, validation=None, *, status=None):
        super().__init__(message)
        self.validation = validation
        self.status = validation["status"] if validation is not None else status


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON keys")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("Non-finite JSON numbers are not supported")


def parse_request(path, raw):
    if path not in REQUEST_KEYS:
        raise RequestError("Unknown endpoint")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                             parse_constant=reject_constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise RequestError("Malformed JSON body") from error
    if not isinstance(payload, dict) or set(payload) != REQUEST_KEYS[path]:
        raise RequestError("Missing or unknown request keys")
    if "tournament_id" in payload and not canonical_id(payload["tournament_id"]):
        raise RequestError("Invalid tournament ID")
    if "challenge_id" in payload and not canonical_id(payload["challenge_id"]):
        raise RequestError("challenge_id must be a canonical challenge name")
    if "team" in payload and (not isinstance(payload["team"], list) or len(payload["team"]) > 3 or
                              not all(canonical_id(name) for name in payload["team"])):
        raise RequestError("team must contain at most three canonical species strings")
    for key in ("agent_id",):
        if key in payload and not canonical_id(payload[key]):
            raise RequestError("IDs must match [a-z][a-z0-9-]{0,39}; "
                               "they are local labels, not authenticated identities")
    if "level" in payload and (not isinstance(payload["level"], str) or payload["level"] not in LEVELS):
        raise RequestError("level must be beginner, intermediate or advanced")
    return payload


class ArenaState:
    """All entry/match transitions and snapshots share one per-server lock."""

    def __init__(self):
        self.lock = threading.Lock()
        self.entries = {}
        self.matches = {}

    def join(self, payload, raw, challenge, catalog):
        challenge_id, agent_id = payload["challenge_id"], payload["agent_id"]
        key = (challenge_id, agent_id)
        with self.lock:
            existing = self.entries.get(key)
            if existing is not None:
                if existing["raw"] != raw:
                    raise RequestError("FAIR-1: Entry is sealed; only byte-identical retries are allowed")
            else:
                if any(scope == challenge_id and entry["challenge"] != challenge
                       for (scope, _), entry in self.entries.items()):
                    raise RequestError("DATA-1: Sealed challenge rules changed; human review required",
                                       status="needs_review")
                if valid_challenge(challenge) and challenge["challenge_id"] != challenge_id:
                    challenge = None
                validation = validate_team(challenge, payload["team"], catalog)
                if validation["status"] != "ready":
                    raise RequestError("Entry refused; only ready teams may join the local arena", validation)
                pending = {}
                for (scope, opponent), entry in sorted(self.entries.items()):
                    if scope != challenge_id:
                        continue
                    left, right = sorted((agent_id, opponent))
                    teams = {agent_id: payload["team"], opponent: entry["team"]}
                    try:
                        result = fight(challenge, teams[left], teams[right], catalog)
                    except ValueError as error:
                        # Never publish either team when sealed evidence fails its recheck.
                        raise RequestError("DATA-1: Sealed evidence recheck failed; human review required",
                                           status="needs_review") from error
                    digest = hashlib.sha256(json.dumps([challenge_id, left, right], separators=(",", ":")).encode()).hexdigest()
                    match_id = "match-" + digest
                    result.update({"match_id": match_id, "challenge_id": challenge_id,
                                   "left_agent_id": left, "right_agent_id": right,
                                   "challenge": deepcopy(challenge), "judged": True})
                    pending[match_id] = result
                self.entries[key] = {"team": list(payload["team"]), "raw": raw,
                                     "challenge": deepcopy(challenge)}
                self.matches.update(pending)
            match_ids = sorted(match_id for match_id, result in self.matches.items()
                               if result["challenge_id"] == challenge_id and
                               agent_id in (result["left_agent_id"], result["right_agent_id"]))
            return {"challenge_id": challenge_id, "agent_id": agent_id, "joined": True, "sealed": True,
                    "status": "judged" if match_ids else "waiting", "match_ids": match_ids,
                    "rule_ids": ["FAIR-1"]}

    def match(self, match_id):
        with self.lock:
            if match_id not in self.matches:
                raise RequestError("Unknown completed match")
            return deepcopy(self.matches[match_id])

    def snapshot(self):
        with self.lock:
            agents = [{"challenge_id": challenge_id, "agent_id": agent, "joined": True}
                      for challenge_id, agent in sorted(self.entries)]
            matches = [deepcopy(self.matches[key]) for key in sorted(self.matches)]
            return {"rules_version": RULES_VERSION, "agents": agents, "matches": matches,
                    "leaderboard": self._leaderboard(), "synthetic": True}

    def leaderboard(self):
        with self.lock:
            return {"leaderboard": self._leaderboard(), "rules_version": RULES_VERSION,
                    "synthetic": True}

    def _leaderboard(self):
        rows = {agent: {"agent_id": agent, "wins": 0, "losses": 0, "draws": 0,
                        "matches": 0, "points": 0} for _, agent in self.entries}
        for match in self.matches.values():
            left, right = rows[match["left_agent_id"]], rows[match["right_agent_id"]]
            left["matches"] += 1
            right["matches"] += 1
            if match["outcome"] == "draw":
                for row in (left, right):
                    row["draws"] += 1
                    row["points"] += 1
            else:
                winner, loser = (left, right) if match["outcome"] == "win" else (right, left)
                winner["wins"] += 1
                winner["points"] += 3
                loser["losses"] += 1
        return sorted(rows.values(), key=lambda row: (-row["points"], -row["wins"], row["agent_id"]))


class ArenaServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address=("127.0.0.1", 8090), fixtures_dir=ROOT / "fixtures", *, container=False, public_port=None):
        permitted = "0.0.0.0" if container else "127.0.0.1"
        if address[0] != permitted:
            raise ValueError("Native mode requires loopback; container mode requires explicit 0.0.0.0")
        if public_port is not None and (type(public_port) is not int or not 1 <= public_port <= 65535):
            raise ValueError("Invalid published port")
        self.container = container
        self.public_port = public_port
        self.fixtures_dir = Path(fixtures_dir)
        self.state = ArenaState()
        self.tournaments = Tournaments()
        super().__init__(address, Handler)

    def fixture(self, filename):
        try:
            value = json.loads((self.fixtures_dir / filename).read_text(encoding="utf-8"),
                               object_pairs_hook=unique_object, parse_constant=reject_constant)
            return value if isinstance(value, dict) else None
        except (OSError, ValueError, UnicodeError, RecursionError):
            return None

    def catalog(self):
        return self.fixture("arena-catalog.json")

    def challenges(self):
        value = self.fixture("arena-challenges.json")
        if (not value or any(not canonical_id(key) or not valid_challenge(challenge) or
                             challenge["challenge_id"] != key for key, challenge in value.items())):
            return None
        return value


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *_args):
        pass  # Never log bodies, IDs, paths or sealed teams.

    def send(self, status, value, content_type="application/json; charset=utf-8"):
        data = value if isinstance(value, bytes) else json.dumps(value, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                         "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors http://localhost:8888 http://127.0.0.1:8888")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        if self.command != "HEAD":
            self.wfile.write(data)

    def send_error(self, _code, message=None, explain=None):
        self.send(400, {"error": "Unsupported or malformed HTTP request"})

    def checked_path(self):
        ports = {self.server.server_port}
        if self.server.public_port is not None:
            ports.add(self.server.public_port)
        hosts = {f"{host}:{port}" for host in ("127.0.0.1", "localhost") for port in ports}
        if self.server.container:
            hosts.add(f"arena:{self.server.server_port}")
        host_headers = self.headers.get_all("Host", [])
        if len(host_headers) != 1 or host_headers[0] not in hosts:
            raise RequestError("A loopback or permitted container Host header is required")
        origins = self.headers.get_all("Origin", [])
        if origins and (len(origins) != 1 or origins[0] != "http://" + host_headers[0]):
            raise RequestError("Cross-origin requests are not allowed")
        try:
            request = urlsplit(self.path)
        except ValueError as error:
            raise RequestError("Malformed request path") from error
        if request.scheme or request.netloc or request.query or request.fragment or "%" in request.path:
            raise RequestError("Queries, encoded paths, absolute URLs and fragments are not supported")
        return request.path

    def do_HEAD(self):
        try:
            if self.checked_path() != "/":
                raise RequestError("Unknown endpoint")
            self.send(200, b"", "text/html; charset=utf-8")
        except RequestError as error:
            self.send_request_error(error)

    def do_GET(self):
        try:
            path = self.checked_path()
            if path == "/":
                self.send(200, (ROOT / "arena" / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif path == "/health":
                challenges = self.server.challenges()
                catalog = self.server.catalog()
                ready = (challenges is not None and catalog is not None and
                         all(complete_pokemon(name, catalog.get(name))
                             for challenge in challenges.values() for name in challenge["allowed"]))
                result = {"status": "ok" if ready else "needs_review", "synthetic": True,
                          "loopback_only": not self.server.container,
                          "deployment": "container" if self.server.container else "native"}
                if not ready:
                    result.update({"rule_ids": ["DATA-1"],
                                   "error": "DATA-1: Challenge or catalog evidence unavailable or incomplete; "
                                            "human review required"})
                self.send(200 if ready else 503, result)
            elif path == "/rules":
                result = rules_payload()
                challenges = self.server.challenges()
                result["challenges"] = [challenges[key] for key in sorted(challenges)] if challenges else []
                if challenges is None:
                    result.update({"status": "needs_review",
                                   "error": "DATA-1: Challenge manifest unavailable; human review required"})
                self.send(503 if challenges is None else 200, result)
            elif path.startswith("/challenges/"):
                challenge_id = path.removeprefix("/challenges/")
                if not canonical_id(challenge_id):
                    raise RequestError("Invalid canonical challenge name")
                challenges = self.server.challenges()
                if challenges is None or challenge_id not in challenges:
                    raise RequestError("DATA-1: Challenge unavailable; human review required", status="needs_review")
                self.send(200, challenges[challenge_id])
            elif path == "/state":
                state = self.server.state.snapshot()
                state["tournaments"] = self.server.tournaments.snapshots()
                self.send(200, state)
            elif path.startswith("/tournaments/"):
                tournament_id = path.removeprefix("/tournaments/")
                if not canonical_id(tournament_id):
                    raise RequestError("Invalid tournament ID")
                self.send(200, self.server.tournaments.snapshot(tournament_id))
            elif path == "/leaderboard":
                self.send(200, self.server.state.leaderboard())
            elif path.startswith("/matches/"):
                match_id = path.removeprefix("/matches/")
                if (len(match_id) != 70 or not match_id.startswith("match-") or
                        any(c not in "0123456789abcdef" for c in match_id[6:])):
                    raise RequestError("Invalid match ID")
                self.send(200, self.server.state.match(match_id))
            elif path.startswith("/catalog/"):
                name = path.removeprefix("/catalog/")
                if not canonical_id(name):
                    raise RequestError("Invalid canonical species name")
                catalog = self.server.catalog()
                if catalog is not None and name in catalog and complete_pokemon(name, catalog[name]):
                    self.send(200, catalog[name])
                else:
                    error = ("Catalog unavailable" if catalog is None else
                             "Unknown catalog species" if name not in catalog else "Incomplete catalog evidence")
                    status = 400 if catalog is not None and name not in catalog else 503
                    self.send(status, {"status": "needs_review", "rule_ids": ["DATA-1"],
                                       "error": error + "; human review required"})
            else:
                raise RequestError("Unknown endpoint")
        except TournamentError as error:
            self.send_request_error(RequestError(str(error), status="needs_review" if "DATA-1" in str(error) else None))
        except RequestError as error:
            self.send_request_error(error)
        except OSError:
            self.send(503, {"status": "needs_review", "error": "Local UI unavailable"})

    def do_POST(self):
        try:
            path = self.checked_path()
            lengths = self.headers.get_all("Content-Length", [])
            if (self.headers.get_all("Transfer-Encoding") or len(lengths) != 1 or
                    not lengths[0].isascii() or not lengths[0].isdigit() or len(lengths[0]) > 6):
                raise RequestError("One bounded Content-Length is required; chunked bodies are not accepted")
            length = int(lengths[0])
            if not 0 < length <= MAX_BODY:
                raise RequestError(f"Body must be between 1 and {MAX_BODY} bytes")
            content_types = self.headers.get_all("Content-Type", [])
            if len(content_types) != 1 or content_types[0].split(";", 1)[0].strip().lower() != "application/json":
                raise RequestError("Content-Type must be application/json")
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise RequestError("Incomplete body")
            payload = parse_request(path, raw)
            catalog = self.server.catalog()
            challenges = self.server.challenges()
            challenge_id = (self.server.tournaments.challenge_id(payload["tournament_id"])
                            if path == "/tournaments/join" else payload["challenge_id"])
            challenge = challenges.get(challenge_id) if challenges else None
            if path == "/tournaments":
                result = self.server.tournaments.create(payload, challenge)
            elif path == "/tournaments/join":
                result = self.server.tournaments.join(payload, raw, challenge, catalog)
            elif path == "/join":
                result = self.server.state.join(payload, raw, challenge, catalog)
            else:
                validation = validate_team(challenge, payload["team"], catalog)
                if validation["status"] != "ready":
                    raise RequestError("Sparring refused; team checks failed", validation)
                try:
                    opponent = sparring_team(challenge, catalog, payload["level"])
                    result = fight(challenge, payload["team"], opponent, catalog)
                except ValueError as error:
                    validation.update({"status": "needs_review", "reason": str(error)})
                    raise RequestError(str(error), validation) from error
                result.update({"status": "ready", "validation": validation, "challenge": challenge,
                               "level": payload["level"], "ranking": SPARRING_RANKING})
            self.send(200, result)
        except TournamentError as error:
            self.send_request_error(RequestError(str(error), status="needs_review" if "DATA-1" in str(error) else None))
        except RequestError as error:
            self.send_request_error(error)
        except (TimeoutError, OSError):
            self.send(400, {"error": "Incomplete or timed-out request"})

    def send_request_error(self, error):
        value = {"error": str(error)}
        if error.status is not None:
            value["status"] = error.status
        if error.validation is not None:
            value["validation"] = error.validation
        if error.status == "needs_review":
            value["rule_ids"] = ["DATA-1"]
        self.send(400, value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--container", action="store_true", help="Bind inside a container; publish only on host loopback")
    parser.add_argument("--public-port", type=int, help="Explicit host loopback published port")
    args = parser.parse_args()
    host = "0.0.0.0" if args.container else "127.0.0.1"
    with ArenaServer((host, args.port), container=args.container, public_port=args.public_port) as server:
        print(f"Synthetic local arena: http://127.0.0.1:{server.server_port} "
              "— restart to reset", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
