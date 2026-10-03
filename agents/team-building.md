# Team-building guidelines

## Discover, shortlist, verify

The arena allows all 151 Generation I species, one default Pokémon variety per
species. Use modern PokéAPI types and stats, not Generation I's historical types.
There are 562,475 unordered three-species combinations before other constraints;
a bounded search is not proof of an overall best team.

For an unspecified team:

1. Call `generation_retrieve` with `id="1"` (or `generation-i`) to discover
   `pokemon_species`. Do not assume Pokémon IDs or a remembered list.
2. Call `type_retrieve` with the required type as `id`. Intersect its
   `pokemon[].pokemon.name` entries with the discovered Generation I species.
   Type lists contain later generations and alternate varieties too.
3. Shortlist several required-type members and complementary species from the
   generation list. Retrieve at most 12 distinct candidates with `pokemon_retrieve`;
   failed calls also count. Require `is_default=true` and `species.name` equal to
   the discovered species name. Check types and sum all six `stats[].base_stat`.
4. Use `pokemon_species_retrieve` when a name or variety is ambiguous; verify
   `generation.name="generation-i"` and choose the `varieties` entry with
   `is_default=true`. Submit that canonical default name, not a regional or Mega form.
5. Compare legal teams from retrieved candidates. Consider matchups, not just
   the stat total. Explain the search's limits; never claim proven optimality.

Public PokéAPI REST has pagination, not fuzzy-name or stat-range search. No new
search API is needed. Discovery does not prove facts for a final member: retrieve
all three final members. Honor narrower user restrictions; check an exact requested
team without silently replacing it; retrieve the generation list once to verify
membership, without sampling replacement candidates. At the lookup limit, choose a verified legal
team if available; otherwise report that the bounded search found none, not that
no legal team exists. Failed or conflicting evidence requires human review.

## Arena rules

- **TEAM-1:** Exactly three distinct species, one default variety each.
- **SPECIES-1:** All 151 Generation I species, including Mew and Mewtwo, are allowed.
  Later generations and alternate varieties are not allowed. The budget still applies.
- **BUDGET-1:** Combined base-stat total must not exceed the challenge budget (inclusive).
- **COVERAGE-1:** Include at least one member of the required type.
- **DATA-1:** Unknown species, missing or conflicting facts, or failed checks
  require human review. Live availability and trainer ownership are not established.
- **FAIR-1:** Entries stay sealed until both are ready and the backend judges.
  Entries cannot be replaced; identical retries do not create extra results.

## Named challenges

Use the requested `challenge_id` unchanged when calling sparring. Current rules
version is `arena-v3`; each challenge uses the same team-size and species rules:

| Challenge | Combined base-stat budget | Required type |
|---|---:|---|
| `water-budget` | 1,000 (inclusive) | Water type |
| `fire-budget` | 1,000 (inclusive) | Fire type |
| `grass-budget` | 1,000 (inclusive) | Grass type |
| `electric-budget` | 1,050 (inclusive) | Electric type |
| `water-open` | 1,100 (inclusive) | Water type |
| `fire-open` | 1,100 (inclusive) | Fire type |

Never change constraints to make a team fit. Unknown scenarios or disagreement
with current backend rules require human review. The backend checks captured
PokéAPI facts before practice or entry; it does not trust agent-supplied stats.
Use returned rule IDs when explaining eligibility or a failed check.

## Measure, do not promise

Combat is synthetic: over all nine cross-team pairs, score each attacker's
base-stat total times its best own-type effectiveness against the defender.
Dual defensive types multiply; immunity is zero. Higher team score wins; equality
draws. No moves, turns, random combat, STAB, levels or model adjudication.
The modern 18-type chart applies, including modern Fairy and Steel typing.

Beginner, intermediate and advanced are fixed published benchmark teams retained
from the original demo, not rankings of all 151 species. Matchup difficulty is not
necessarily monotonic. A practice win does not prove the best team was found.

Report actual scores and outcomes for the same final team, including losses.
An untested recommendation is proposed, not ready. If facts are missing or checks
fail, require human review. Keep opponents' teams private until the backend judges.
Only join when the user explicitly requests a local match.
