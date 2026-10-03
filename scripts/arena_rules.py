"""Pure rules for a local synthetic arena, not an official battle simulator."""

import re
from fractions import Fraction

RULES_VERSION = "arena-v3"
RULE_IDS = ("TEAM-1", "SPECIES-1", "BUDGET-1", "COVERAGE-1", "DATA-1", "FAIR-1")
ALLOWED = (
    "bulbasaur", "ivysaur", "venusaur", "charmander", "charmeleon", "charizard", "squirtle",
    "wartortle", "blastoise", "caterpie", "metapod", "butterfree", "weedle", "kakuna", "beedrill",
    "pidgey", "pidgeotto", "pidgeot", "rattata", "raticate", "spearow", "fearow", "ekans", "arbok",
    "pikachu", "raichu", "sandshrew", "sandslash", "nidoran-f", "nidorina", "nidoqueen", "nidoran-m",
    "nidorino", "nidoking", "clefairy", "clefable", "vulpix", "ninetales", "jigglypuff", "wigglytuff",
    "zubat", "golbat", "oddish", "gloom", "vileplume", "paras", "parasect", "venonat", "venomoth",
    "diglett", "dugtrio", "meowth", "persian", "psyduck", "golduck", "mankey", "primeape", "growlithe",
    "arcanine", "poliwag", "poliwhirl", "poliwrath", "abra", "kadabra", "alakazam", "machop", "machoke",
    "machamp", "bellsprout", "weepinbell", "victreebel", "tentacool", "tentacruel", "geodude",
    "graveler", "golem", "ponyta", "rapidash", "slowpoke", "slowbro", "magnemite", "magneton",
    "farfetchd", "doduo", "dodrio", "seel", "dewgong", "grimer", "muk", "shellder", "cloyster",
    "gastly", "haunter", "gengar", "onix", "drowzee", "hypno", "krabby", "kingler", "voltorb",
    "electrode", "exeggcute", "exeggutor", "cubone", "marowak", "hitmonlee", "hitmonchan", "lickitung",
    "koffing", "weezing", "rhyhorn", "rhydon", "chansey", "tangela", "kangaskhan", "horsea", "seadra",
    "goldeen", "seaking", "staryu", "starmie", "mr-mime", "scyther", "jynx", "electabuzz", "magmar",
    "pinsir", "tauros", "magikarp", "gyarados", "lapras", "ditto", "eevee", "vaporeon", "jolteon",
    "flareon", "porygon", "omanyte", "omastar", "kabuto", "kabutops", "aerodactyl", "snorlax",
    "articuno", "zapdos", "moltres", "dratini", "dragonair", "dragonite", "mewtwo", "mew",
)
SPECIES_IDS = {name: index for index, name in enumerate(ALLOWED, 1)}
STAT_NAMES = ("hp", "attack", "defense", "special_attack", "special_defense", "speed")
LEVELS = ("beginner", "intermediate", "advanced")
CHALLENGE_KEYS = frozenset({"challenge_id", "rules_version", "team_size", "budget_limit",
                            "allowed", "required_type", "rule_ids"})

# Captured modern type chart; omitted pairs are neutral, dual defenses multiply.
TYPE_EFFECTIVENESS = {
    "bug": {
        "grass": 2, "psychic": 2, "dark": 2, "fighting": Fraction(1, 2), "flying": Fraction(1, 2),
        "poison": Fraction(1, 2), "ghost": Fraction(1, 2), "steel": Fraction(1, 2), "fire": Fraction(1, 2),
        "fairy": Fraction(1, 2),
    },
    "dark": {
        "ghost": 2, "psychic": 2, "fighting": Fraction(1, 2), "dark": Fraction(1, 2),
        "fairy": Fraction(1, 2),
    },
    "dragon": {
        "dragon": 2, "steel": Fraction(1, 2), "fairy": 0,
    },
    "electric": {
        "flying": 2, "water": 2, "grass": Fraction(1, 2), "electric": Fraction(1, 2),
        "dragon": Fraction(1, 2), "ground": 0,
    },
    "fairy": {
        "fighting": 2, "dragon": 2, "dark": 2, "poison": Fraction(1, 2), "steel": Fraction(1, 2),
        "fire": Fraction(1, 2),
    },
    "fighting": {
        "normal": 2, "rock": 2, "steel": 2, "ice": 2, "dark": 2, "flying": Fraction(1, 2),
        "poison": Fraction(1, 2), "bug": Fraction(1, 2), "psychic": Fraction(1, 2), "fairy": Fraction(1, 2),
        "ghost": 0,
    },
    "fire": {
        "bug": 2, "steel": 2, "grass": 2, "ice": 2, "rock": Fraction(1, 2), "fire": Fraction(1, 2),
        "water": Fraction(1, 2), "dragon": Fraction(1, 2),
    },
    "flying": {
        "fighting": 2, "bug": 2, "grass": 2, "rock": Fraction(1, 2), "steel": Fraction(1, 2),
        "electric": Fraction(1, 2),
    },
    "ghost": {
        "ghost": 2, "psychic": 2, "dark": Fraction(1, 2), "normal": 0,
    },
    "grass": {
        "ground": 2, "rock": 2, "water": 2, "flying": Fraction(1, 2), "poison": Fraction(1, 2),
        "bug": Fraction(1, 2), "steel": Fraction(1, 2), "fire": Fraction(1, 2), "grass": Fraction(1, 2),
        "dragon": Fraction(1, 2),
    },
    "ground": {
        "poison": 2, "rock": 2, "steel": 2, "fire": 2, "electric": 2, "bug": Fraction(1, 2),
        "grass": Fraction(1, 2), "flying": 0,
    },
    "ice": {
        "flying": 2, "ground": 2, "grass": 2, "dragon": 2, "steel": Fraction(1, 2), "fire": Fraction(1, 2),
        "water": Fraction(1, 2), "ice": Fraction(1, 2),
    },
    "normal": {
        "rock": Fraction(1, 2), "steel": Fraction(1, 2), "ghost": 0,
    },
    "poison": {
        "grass": 2, "fairy": 2, "poison": Fraction(1, 2), "ground": Fraction(1, 2), "rock": Fraction(1, 2),
        "ghost": Fraction(1, 2), "steel": 0,
    },
    "psychic": {
        "fighting": 2, "poison": 2, "steel": Fraction(1, 2), "psychic": Fraction(1, 2), "dark": 0,
    },
    "rock": {
        "flying": 2, "bug": 2, "fire": 2, "ice": 2, "fighting": Fraction(1, 2), "ground": Fraction(1, 2),
        "steel": Fraction(1, 2),
    },
    "steel": {
        "rock": 2, "ice": 2, "fairy": 2, "steel": Fraction(1, 2), "fire": Fraction(1, 2),
        "water": Fraction(1, 2), "electric": Fraction(1, 2),
    },
    "water": {
        "ground": 2, "rock": 2, "fire": 2, "water": Fraction(1, 2), "grass": Fraction(1, 2),
        "dragon": Fraction(1, 2),
    },
}

RULE_TEXT = """Arena rules. Canonical fixture stats; simplified local mechanics only.
TEAM-1: A team contains exactly three distinct canonical species.
SPECIES-1: All 151 Generation I species are allowed, default varieties only; alternate forms and later generations are excluded.
BUDGET-1: Sum of base stats must not exceed the challenge budget, inclusive.
COVERAGE-1: Include at least one species of the challenge required type.
DATA-1: Unknown species, incomplete evidence or failed catalog checks require human review. Recheck fixtures before a duel; real availability is not checked.
FAIR-1: Teams are sealed until both submissions are ready and a duel is judged. The arena judges automatically when another eligible entry arrives. Entries cannot be replaced; byte-identical join retries never create extra matches.
"""
COMBAT_EXPLANATION = (
    "For every one of the nine cross-team pairs, add the attacker's base-stat total "
    "times its best own-type effectiveness against all defender types (dual types multiply). "
    "Both teams use the identical formula; larger summed score wins, equality draws. "
    "Neutral pairs use 1; immunity uses 0. No random combat, moves, turns, levels, "
    "STAB or model judging. This is a teaching mechanic, not an official battle simulator."
)
SPARRING_RANKING = (
    "Fixed published benchmark teams, retained from the original seven-species arena. "
    "Beginner/intermediate/advanced are benchmark labels, not rankings of the expanded pool "
    "or guarantees of matchup difficulty. No exhaustive search occurs during sparring."
)
SPARRING_TEAMS = {
    "electric-budget": (
        ("charmander", "horsea", "pikachu"),
        ("charmander", "eevee", "pikachu"),
        ("eevee", "onix", "pikachu"),
    ),
    "fire-budget": (
        ("charmander", "horsea", "squirtle"),
        ("charmander", "pikachu", "squirtle"),
        ("charmander", "horsea", "onix"),
    ),
    "fire-open": (
        ("charmander", "horsea", "squirtle"),
        ("charmander", "eevee", "squirtle"),
        ("charmander", "eevee", "onix"),
    ),
    "grass-budget": (
        ("bulbasaur", "charmander", "horsea"),
        ("bulbasaur", "charmander", "pikachu"),
        ("bulbasaur", "horsea", "onix"),
    ),
    "water-budget": (
        ("charmander", "horsea", "squirtle"),
        ("eevee", "horsea", "pikachu"),
        ("horsea", "onix", "pikachu"),
    ),
    "water-open": (
        ("charmander", "horsea", "squirtle"),
        ("charmander", "eevee", "squirtle"),
        ("eevee", "onix", "squirtle"),
    ),
}


def canonical_id(value):
    return isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,39}", value) is not None


def valid_challenge(challenge):
    return (isinstance(challenge, dict) and challenge.keys() == CHALLENGE_KEYS and
            canonical_id(challenge.get("challenge_id")) and
            challenge.get("rules_version") == RULES_VERSION and
            type(challenge.get("team_size")) is int and challenge["team_size"] == 3 and
            type(challenge.get("budget_limit")) is int and 0 <= challenge["budget_limit"] <= 100000 and
            challenge.get("allowed") == list(ALLOWED) and
            challenge.get("required_type") in ("water", "fire", "grass", "electric") and
            challenge.get("rule_ids") == list(RULE_IDS))


def complete_pokemon(name, pokemon):
    if not isinstance(pokemon, dict) or pokemon.get("name") != name:
        return False
    if (pokemon.get("is_default") is not True or type(pokemon.get("species_id")) is not int or
            pokemon["species_id"] != SPECIES_IDS.get(name)):
        return False
    types = pokemon.get("types")
    stats = pokemon.get("stats")
    return (isinstance(types, list) and 1 <= len(types) <= 2 and
            all(isinstance(kind, str) and kind in TYPE_EFFECTIVENESS for kind in types) and
            len(set(types)) == len(types) and isinstance(stats, dict) and set(stats) == set(STAT_NAMES) and
            all(type(stats[key]) is int and 1 <= stats[key] <= 255 for key in STAT_NAMES) and
            type(pokemon.get("base_stat_total")) is int and pokemon["base_stat_total"] == sum(stats.values()) and
            isinstance(pokemon.get("source"), str) and bool(pokemon["source"].strip()) and
            (pokemon.get("fixture") is True or
             isinstance(pokemon.get("fixture"), str) and bool(pokemon["fixture"].strip())))


def validate_team(challenge, team, catalog):
    """Missing evidence takes precedence over known violations; never mutate inputs."""
    review = []
    violations = []
    valid_names = isinstance(team, list) and all(canonical_id(name) for name in team)
    output_team = list(team) if valid_names else []
    rules_ok = valid_challenge(challenge)
    if not rules_ok:
        review.append("DATA-1: Current challenge evidence is incomplete or unsupported")
    if not valid_names:
        review.append("DATA-1: Team must be a list of canonical species names")
    if not isinstance(catalog, dict):
        catalog = {}
        review.append("DATA-1: Catalog check unavailable")

    total = 0 if valid_names else None
    types = set()
    for name in output_team:
        pokemon = catalog.get(name)
        if not complete_pokemon(name, pokemon):
            total = None
            review.append(f"DATA-1: Unknown species or incomplete evidence for {name}")
        else:
            if total is not None:
                total += pokemon["base_stat_total"]
            types.update(pokemon["types"])
    if rules_ok and valid_names:
        if len(team) != challenge["team_size"] or len(set(team)) != len(team):
            violations.append("TEAM-1: Exactly three distinct species are required")
        if any(name in catalog and name not in challenge["allowed"] for name in team):
            violations.append("SPECIES-1: Species outside the Generation I default-variety allowlist")
        if total is not None and total > challenge["budget_limit"]:
            violations.append(f"BUDGET-1: Total exceeds {challenge['budget_limit']}")
        if total is not None and challenge["required_type"] not in types:
            violations.append(f"COVERAGE-1: Include a {challenge['required_type']}-type species")
    status = "needs_review" if review else "ineligible" if violations else "ready"
    reason = "; ".join(review + violations) or (
        "TEAM-1 / SPECIES-1 / BUDGET-1 / COVERAGE-1 / DATA-1: Current fixture checks passed")
    reason += ". FAIR-1: Entries stay sealed until a duel is judged."
    return {"team": output_team, "stat_total": total, "status": status,
            "rule_ids": list(RULE_IDS), "reason": reason,
            "challenge_id": challenge.get("challenge_id") if isinstance(challenge, dict) else None}


def effectiveness(attack_type, defender_types):
    """Product of captured modern type-chart entries."""
    result = Fraction(1)
    for kind in defender_types:
        result *= TYPE_EFFECTIVENESS[attack_type].get(kind, 1)
    return result


def fight(challenge, left_team, right_team, catalog):
    """Judge symmetrically with exact rational arithmetic after checking both teams."""
    validations = [validate_team(challenge, team, catalog) for team in (left_team, right_team)]
    if any(result["status"] != "ready" for result in validations):
        raise ValueError("DATA-1: Combat requires two ready teams; invalid or uncertain evidence is refused")

    def score(attackers, defenders):
        return sum((catalog[name]["base_stat_total"] *
                    max(effectiveness(kind, catalog[target]["types"]) for kind in catalog[name]["types"])
                    for name in attackers for target in defenders), Fraction(0))

    left_score = score(left_team, right_team)
    right_score = score(right_team, left_team)
    return {"left_team": list(left_team), "right_team": list(right_team),
            "left_score": float(left_score), "right_score": float(right_score),
            "outcome": "win" if left_score > right_score else "loss" if left_score < right_score else "draw",
            "rules_version": RULES_VERSION, "challenge_id": challenge["challenge_id"],
            "rule_ids": list(RULE_IDS), "explanation": COMBAT_EXPLANATION}


def sparring_team(challenge, catalog, level):
    if not isinstance(level, str) or level not in LEVELS:
        raise ValueError("Unknown sparring level")
    if (not valid_challenge(challenge) or not isinstance(catalog, dict) or
            any(not complete_pokemon(name, catalog.get(name)) for name in challenge["allowed"])):
        raise ValueError("DATA-1: Complete challenge and catalog evidence is required for sparring")
    benchmarks = SPARRING_TEAMS.get(challenge["challenge_id"])
    if benchmarks is None:
        raise ValueError("DATA-1: No published sparring benchmark; human review required")
    team = list(benchmarks[LEVELS.index(level)])
    if validate_team(challenge, team, catalog)["status"] != "ready":
        raise ValueError("DATA-1: Sparring benchmark does not meet current rules; human review required")
    return team


def rules_payload():
    return {"rules_version": RULES_VERSION, "rule_ids": list(RULE_IDS), "rules": RULE_TEXT,
            "combat": COMBAT_EXPLANATION, "sparring_ranking": SPARRING_RANKING,
            "sparring_teams": {name: dict(zip(LEVELS, teams)) for name, teams in SPARRING_TEAMS.items()},
            "type_effectiveness": {kind: {target: float(value) for target, value in row.items()}
                                   for kind, row in TYPE_EFFECTIVENESS.items()},
            "neutral_multiplier": 1, "synthetic": True}
