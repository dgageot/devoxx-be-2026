#!/usr/bin/env python3
"""Capture Generation I default Pokémon and the modern type chart from PokéAPI."""

import argparse
import hashlib
import json
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from arena_rules import ALLOWED, complete_pokemon

BASE = "https://pokeapi.co/api/v2/"


def retrieve(path):
    url = BASE + path.rstrip("/") + "/"
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": "PokemonArenaFixtureCapture/1"}), timeout=30) as response:
                raw = response.read()
            return json.loads(raw), {"url": url, "sha256": hashlib.sha256(raw).hexdigest()}
        except (OSError, ValueError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def capture_species(summary):
    species, species_source = retrieve("pokemon-species/" + summary["name"])
    defaults = [variety["pokemon"]["name"] for variety in species["varieties"] if variety["is_default"]]
    if species["generation"]["name"] != "generation-i" or len(defaults) != 1:
        raise ValueError("DATA-1: Expected one default Generation I variety")
    pokemon, pokemon_source = retrieve("pokemon/" + defaults[0])
    if (not pokemon["is_default"] or pokemon["species"]["name"] != species["name"] or
            pokemon["name"] != species["name"]):
        raise ValueError("DATA-1: Default Pokémon and species must agree")
    stats = {entry["stat"]["name"].replace("-", "_"): entry["base_stat"] for entry in pokemon["stats"]}
    if len(stats) != 6:
        raise ValueError("DATA-1: Expected six base stats")
    entry = {"name": pokemon["name"], "species_id": species["id"], "is_default": True,
             "types": [entry["type"]["name"] for entry in sorted(pokemon["types"], key=lambda entry: entry["slot"])],
             "stats": stats, "base_stat_total": sum(stats.values()),
             "source": pokemon_source["url"], "fixture": "captured PokéAPI facts; not a live response"}
    if not complete_pokemon(pokemon["name"], entry):
        raise ValueError("DATA-1: Captured Pokémon evidence is incomplete or inconsistent")
    return pokemon["name"], entry, [species_source, pokemon_source]


def capture_type(index):
    value, source = retrieve("type/" + str(index))
    row = {}
    for field, multiplier in (("double_damage_to", 2), ("half_damage_to", 0.5), ("no_damage_to", 0)):
        row.update((target["name"], multiplier) for target in value["damage_relations"][field])
    return value["name"], row, source


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def publish_capture(output_dir, artifacts):
    """Stage a capture, reserve its new directory exclusively, and clean up failures."""
    output_dir = Path(output_dir).absolute()
    if output_dir.exists():
        raise FileExistsError("Output directory already exists; reviewed captures are never overwritten")
    with tempfile.TemporaryDirectory(prefix=".arena-capture-", dir=output_dir.parent) as staging:
        staging = Path(staging)
        for filename, value in artifacts.items():
            write_json(staging / filename, value)
        # mkdir is exclusive even if another process creates the destination while staging.
        output_dir.mkdir()
        published = []
        try:
            for filename in artifacts:
                destination = output_dir / filename
                # Hard links publish complete files without replacing concurrent files.
                destination.hardlink_to(staging / filename)
                published.append(destination)
        except BaseException:
            for path in published:
                path.unlink()
            output_dir.rmdir()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory for review; must not exist")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists; choose a new directory")
    generation, source = retrieve("generation/1")
    species = generation["pokemon_species"]
    if generation["name"] != "generation-i" or len(species) != 151:
        raise ValueError("DATA-1: Expected all 151 Generation I species")
    with ThreadPoolExecutor(max_workers=6) as pool:
        entries = list(pool.map(capture_species, species))
        types = list(pool.map(capture_type, range(1, 19)))
    catalog = {name: entry for name, entry, _ in sorted(entries)}
    if {entry["species_id"] for entry in catalog.values()} != set(range(1, 152)):
        raise ValueError("DATA-1: Incomplete Generation I coverage")
    chart = {name: row for name, row, _ in sorted(types)}
    if any(kind not in chart for entry in catalog.values() for kind in entry["types"]):
        raise ValueError("DATA-1: Unsupported Pokémon type")
    if set(catalog) != set(ALLOWED):
        raise ValueError("DATA-1: Captured species disagree with the reviewed Generation I allowlist")
    if len(chart) != 18 or any(target not in chart for row in chart.values() for target in row):
        raise ValueError("DATA-1: Incomplete modern type chart")
    artifacts = {"arena-catalog.json": catalog, "arena-types.json": chart}
    artifacts["arena-catalog.provenance.json"] = {
        "captured_at": datetime.now(timezone.utc).isoformat(), "generation": "generation-i",
        "species_count": len(catalog), "default_varieties_only": True, "type_chart": "modern, 18 types",
        "artifacts": {name: hashlib.sha256((json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()).hexdigest()
                      for name, value in artifacts.items()},
        "responses": [source] + [item for _, _, sources in sorted(entries) for item in sources] +
                     [source for _, _, source in sorted(types)],
    }
    publish_capture(args.output_dir, artifacts)
    print(f"Captured {len(catalog)} default species and {len(chart)} types in {args.output_dir}.")


if __name__ == "__main__":
    main()
