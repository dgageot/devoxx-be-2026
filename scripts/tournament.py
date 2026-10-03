"""Fixed 32-player knockout brackets; the backend alone judges and advances winners."""

import threading
from copy import deepcopy

from arena_rules import canonical_id, fight, valid_challenge, validate_team

PLAYER_IDS = tuple(f"player-{seed:02}" for seed in range(1, 33))
ROUND_NAMES = ("Round of 32", "Round of 16", "Quarterfinals", "Semifinals", "Final")
TIEBREAK = "Draws advance the lower original seed; the recorded combat outcome remains a draw."


class TournamentError(ValueError):
    pass


class Tournaments:
    def __init__(self):
        self.lock = threading.Lock()
        self.items = {}

    def create(self, payload, challenge):
        tournament_id = payload["tournament_id"]
        if not canonical_id(tournament_id):
            raise TournamentError("Invalid tournament ID")
        if not valid_challenge(challenge) or challenge["challenge_id"] != payload["challenge_id"]:
            raise TournamentError("DATA-1: Challenge unavailable; human review required")
        with self.lock:
            if tournament_id in self.items:
                if self.items[tournament_id]["challenge"] != challenge:
                    raise TournamentError("DATA-1: Tournament rules changed; human review required")
            else:
                if len(self.items) >= 8:
                    raise TournamentError("At most eight tournaments may be held in one arena")
                rounds = []
                for index, name in enumerate(ROUND_NAMES):
                    matches = []
                    for slot in range(16 >> index):
                        matches.append({"match_id": f"{tournament_id}-r{index + 1}-{slot + 1}",
                                        "left_agent_id": PLAYER_IDS[slot * 2] if index == 0 else None,
                                        "right_agent_id": PLAYER_IDS[slot * 2 + 1] if index == 0 else None,
                                        "status": "waiting", "winner": None})
                    rounds.append({"name": name, "matches": matches})
                self.items[tournament_id] = {"tournament_id": tournament_id, "challenge": deepcopy(challenge),
                                             "entries": {}, "rounds": rounds, "reviews": {}}
            return {"tournament_id": tournament_id, "challenge_id": challenge["challenge_id"],
                    "player_ids": list(PLAYER_IDS), "size": 32, "tiebreak": TIEBREAK}

    def join(self, payload, raw, challenge, catalog):
        tournament_id, agent_id = payload["tournament_id"], payload["agent_id"]
        with self.lock:
            current = self.items.get(tournament_id)
            if current is None:
                raise TournamentError("Unknown tournament")
            if agent_id not in PLAYER_IDS:
                raise TournamentError("Player ID must be one of player-01 through player-32")
            if agent_id in current["entries"]:
                if current["entries"][agent_id]["raw"] != raw:
                    raise TournamentError("FAIR-1: Tournament entry is sealed; only identical retries are allowed")
                return self._receipt(current, agent_id)
            if challenge != current["challenge"]:
                current["reviews"][agent_id] = "DATA-1: Tournament rules changed; human review required"
                raise TournamentError(current["reviews"][agent_id])
            validation = validate_team(challenge, payload["team"], catalog)
            if validation["status"] == "needs_review":
                current["reviews"][agent_id] = "DATA-1: Tournament facts unavailable; human review required"
                raise TournamentError(current["reviews"][agent_id])
            if validation["status"] != "ready":
                raise TournamentError("Tournament team does not meet the challenge rules")
            # Publish the entry and all newly resolved matches together, or none of them.
            candidate = deepcopy(current)
            candidate["entries"][agent_id] = {"team": list(payload["team"]), "raw": raw}
            candidate["reviews"].pop(agent_id, None)
            try:
                self._advance(candidate, catalog)
            except ValueError as error:
                current["reviews"][agent_id] = "DATA-1: Tournament evidence recheck failed; human review required"
                raise TournamentError(current["reviews"][agent_id]) from error
            self.items[tournament_id] = candidate
            return self._receipt(candidate, agent_id)

    def _advance(self, tournament, catalog):
        entries, rounds = tournament["entries"], tournament["rounds"]
        for index, round_ in enumerate(rounds):
            for slot, match in enumerate(round_["matches"]):
                if match["status"] == "judged":
                    continue
                if index:
                    previous = rounds[index - 1]["matches"]
                    match["left_agent_id"] = previous[slot * 2]["winner"]
                    match["right_agent_id"] = previous[slot * 2 + 1]["winner"]
                left, right = match["left_agent_id"], match["right_agent_id"]
                if left not in entries or right not in entries:
                    continue
                result = fight(tournament["challenge"], entries[left]["team"], entries[right]["team"], catalog)
                winner = left if result["outcome"] == "win" else right
                if result["outcome"] == "draw":
                    winner = min(left, right)
                match.update(result)
                match.update(status="judged", winner=winner,
                             tiebreak="lower-seed" if result["outcome"] == "draw" else None)

    def _receipt(self, tournament, agent_id):
        return {"tournament_id": tournament["tournament_id"], "agent_id": agent_id,
                "joined": True, "sealed": True, "accepted_entries": len(tournament["entries"]),
                "status": self._snapshot(tournament)["status"], "rule_ids": ["FAIR-1"]}

    def _snapshot(self, tournament):
        champion = tournament["rounds"][-1]["matches"][0]["winner"]
        status = "needs_review" if tournament["reviews"] else "complete" if champion else "running"
        return {"tournament_id": tournament["tournament_id"], "challenge_id": tournament["challenge"]["challenge_id"],
                "status": status, "size": 32, "accepted_entries": len(tournament["entries"]),
                "players": [{"agent_id": player, "seed": seed, "joined": player in tournament["entries"]}
                            for seed, player in enumerate(PLAYER_IDS, 1)],
                "rounds": deepcopy(tournament["rounds"]), "champion": champion,
                "tiebreak": TIEBREAK, "review": "; ".join(sorted(set(tournament["reviews"].values()))) or None}

    def snapshot(self, tournament_id):
        with self.lock:
            if tournament_id not in self.items:
                raise TournamentError("Unknown tournament")
            return self._snapshot(self.items[tournament_id])

    def challenge_id(self, tournament_id):
        with self.lock:
            if tournament_id not in self.items:
                raise TournamentError("Unknown tournament")
            return self.items[tournament_id]["challenge"]["challenge_id"]

    def snapshots(self):
        with self.lock:
            return [self._snapshot(self.items[key]) for key in sorted(self.items)]
