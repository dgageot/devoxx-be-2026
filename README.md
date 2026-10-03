# Pokemon Arena

**Specialized AI Agents: from concept to production - Devoxx Belgium - three-hour deep dive**

> When I say Pokémon, think “my business use case.”

Look up canonical Pokémon facts, use a local shell tool for random sampling, load
team-building guidelines, propose a team under plain-language constraints, then
practice against known opponents. Improve the builder with native evals before
letting two agents submit sealed teams to the local web arena.

## One toolset, one use case

| Mechanism | Demo | Business parallel |
|---|---|---|
| `openapi` | PokéAPI catalog and types/stats | Product/resource facts |
| `script` | `shuf` returns one random integer | Audit/test sampling |
| `add_prompt_files` | Team-building guidelines | Planning playbook |
| `api` | Sparring, local entry and combat judge | Simulation/workflow service |

The slide deck opens with familiar specialized-agent use cases before introducing
docker-agent, and has no appendix. Each new step explains why, shows how and leads
into the next question; short recaps leave time to discuss the actual outputs.
PokéAPI facts are canonical, but combat, challenges and
tiers are synthetic—not official tournaments or an official battle simulator.
After the business recap, a linked word cloud points to documented capabilities
not demonstrated here: ACP, A2A, memory, RAG, LSP, sandboxes, skills and more.

### Optional advanced detours

Add these one at a time as standalone, skippable slides within the story—not an appendix:

| Detour | Placement | Status |
|---|---|---|
| Tool descriptions: your tools are part of the prompt | After “Use existing Web APIs as tools” | Added; ~3 minutes, static examples |
| Permissions: let lookups run, confirm practice | After “Give the agent the same API call” | Added; ~4 minutes |
| Context budgeting: keep evidence, trim noise | After JSON response trimming | Candidate |
| Mixed models: optimize the whole task, not one call | After “Wire the specialists in YAML” | Added; ~5 minutes |
| Prompt optimization: an agent runs the development loop | After “Keep it only if it helps” | Added; bounded live detour |
| Tracing: see the agent's trace | After “Call the agent from an application” | Added; live detour |
| OCI distribution: ship the exact agent you evaluated | After “Run the packaged agent” | Added; ~4 minutes, static examples |
| Background orchestration: bounded fan-out and failure recovery | Before the 32-player tournament | Candidate |

The OCI detour shows illustrative `share push` and digest-pinned `serve chat`
commands, not a live publication. Freeze the chosen flavor and reviewed guidance,
evaluate the release inputs, and retain results plus runtime/dependency versions.
The artifact contains the YAML configuration: `instruction_file` is inlined, but
`add_prompt_files`, eval setup/results and runtime services are not bundled.
Provision the same reviewed support files separately, verify the retrieved release
and record its full OCI **manifest digest** before promotion. Tags can move; a
digest pins configuration bytes, not model behavior or eval success. Secrets must
stay out of published YAML, which remains clear even with `--encrypt`.
No live-demo config, registry, service or arena state is changed by this slide.

An outlined star in the top-left corner marks an optional slide.
The tool-description detour compares two illustrative OpenAPI operation excerpts:
same endpoint, tool name and input schema, clearer summary and parameter guidance.
In this Docker Agent build, `summary` takes precedence over the operation's
`description` for the model-facing tool description. String examples `"pikachu"`
and `"25"` clarify the required `id` input. Metadata does not trim responses,
grant authority or prove retrieval success (DATA-1). No spec or live-demo config
changes, model calls or services are needed; skip directly to response trimming.

The permissions detour shows a **permissions excerpt**, not a new runnable config:
`runtime.safety: strict`, `allow` for `pokemon_retrieve`, and `ask` for `spar_team`.
It follows the first agent API call and precedes structured output, using only tools
already introduced. The example is illustrative: the existing sparring config uses
restricted mode and is unchanged. To try this policy, use `--safety strict` and retain
allow entries for the other discovery tools. No model calls or local match are
needed to explain it. Permission precedence is
`deny` → `allow` → `ask`: matching allows silence asks. YAML asks yield to
user-selected balanced/restricted/autonomous modes; `--yolo` can bypass the ask,
and an interactive always-allow grant can silence later prompts. This is **not**
equivalent to a mandatory `tool_guard` ask. Speaker notes cover these limits and a
business parallel. Permissions are not a sandbox; confirmation is not authorization
or eligibility evidence (DATA-1). Backend validation and sealed entries (FAIR-1)
remain unchanged. Existing live-demo configs are intentionally untouched.
See [permissions semantics](https://docker.github.io/docker-agent/configuration/permissions/).

The mixed-model detour reuses `12-team.yaml` without changing its default run.
Two flavors change **only model assignments**, keeping roles, prompts, tools and
handoffs fixed. `all-strong` uses Sol for all three roles; `mixed` keeps Sol for
the builder and uses Luna for the coordinator and coach. Both named models have
thinking disabled. This is fixed assignment by role, not automatic routing.
Run the top terminal to completion before the bottom, with the identical request
and fresh sessions:

```sh
docker agent run agents/12-team.yaml --flavor all-strong "Propose a team for water-budget and spar against beginner."
docker agent run agents/12-team.yaml --flavor mixed "Propose a team for water-budget and spar against beginner."
```

Open `/cost` in each TUI for the estimated session total and agent/model
breakdown. Verify both models have pricing; missing or zero estimates are not
proof of free execution. Provider billing is authoritative. For wall-clock
latency, rehearse with `time docker agent run --exec` and the same arguments;
this includes CLI startup and tools, without human pauses. Repeat both variants
at least five times, alternate order and compare medians **and success counts**.
Check final-member lookup evidence, eligibility and the exact team handed to the
coach against the actual beginner result. Missing/conflicting evidence needs
review (DATA-1); no entry tools or local matches are involved (FAIR-1).
No cost or speed improvement has been measured for these flavors. Extra
handoffs, repeated work and retries can erase savings. Keep the mix only if it
retains correctness and improves the chosen metric. The existing builder evals
expect JSON and cannot directly grade this prose coordinator: give it its own
assertions before making a production decision. Subsequent service configs are
independent; skipping the detour changes nothing.

The tracing detour embeds a local Jaeger viewer on the left and **three terminals**
on the right: viewer, traced server, client. It uses loopback chat port **8082**,
leaving the previous application's 8080 listener alone. Prepare the digest-pinned
multi-architecture Jaeger image while online:

```sh
docker compose -p devoxx-tracing -f compose.tracing.yaml pull
```

Start the slide's terminals top to bottom (commands wait for Enter):

```sh
python3 scripts/trace_viewer.py
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318 OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=false docker agent serve chat agents/13-service.yaml --listen 127.0.0.1:8082 --otel
python3 scripts/api_client.py --url http://127.0.0.1:8082
```

Wait for the viewer to load and the server to listen before running the client.
After completion, allow at least five seconds for batched spans. In
[Jaeger](http://127.0.0.1:16686/search), select `docker-agent`, click **Find Traces**,
and open the latest trace. Refresh the embedded browser if its service list
predates the first export. Inspect durations, lookup counts, errors and token
usage when reported. Search results do not auto-refresh. No match or tournament
is requested.

`trace_viewer.py` reads the pinned image/loopback port settings from
`compose.tracing.yaml`, creates a uniquely named container, and displays its logs
while attached to the terminal. **Leaving the slide or pressing Ctrl-C stops and
removes that invocation's container.** Only its immutable container ID is removed;
foreign listeners/containers are never adopted or stopped. Port conflicts fail
rather than replacing anything. No image pull/build or detached viewer is started.
Jaeger keeps traces in memory, so leaving the slide discards them; inspect them
before navigating away. Hard kills or a Docker outage can prevent cleanup and
require human review.

If you previously started the detached rehearsal collector, stop that owned
project deliberately before using the slide's viewer terminal:

```sh
docker compose -p devoxx-tracing -f compose.tracing.yaml stop
```

Docker Agent also constructs metric/log exporters; Jaeger only accepts traces,
so other signal exports can report unsupported-endpoint errors. Standard
exporter-disable variables do not disable these explicitly constructed exporters.

Content capture is explicitly off. Metadata/error descriptions still need care;
agent-turn spans do not imply application/backend instrumentation. DATA-1 review
and FAIR-1 privacy boundaries remain unchanged. See [OpenTelemetry](https://docker.github.io/docker-agent/community/opentelemetry/)
and [Jaeger setup](https://www.jaegertracing.io/docs/2.21/getting-started/).

## Local PokéAPI: prepare once before the demo

The real [PokéAPI application](https://github.com/PokeAPI/pokeapi) runs in one
container with its official populated SQLite snapshot and an in-memory cache.
No PostgreSQL, Redis, GraphQL or CSV import is needed for this REST-only demo.
The multi-architecture upstream image is digest-pinned (Apple Silicon supported);
the database download is checksum-pinned. Migrations run at build time, not startup.

While online, prepare and start it from the repository root:

```sh
docker compose build pokeapi
docker compose up -d --no-build --pull never --wait pokeapi
curl -fsS http://127.0.0.1:8000/api/v2/pokemon/pikachu/
```

The build downloads the ~128 MB [official SQLite snapshot](https://github.com/PokeAPI/pokeapi/releases/tag/master-branch).
Build **before** presenting; afterward the same startup command needs neither
GitHub nor pokeapi.co. Slide terminals automatically run it with no builds/pulls,
reuse the existing container without recreating it, and wait up to 60 seconds for
health. Failed stateless PokéAPI containers are recreated once using the prepared
image; concurrent terminals share a startup lock. Manual startup is only needed
for external terminals. The database lives
in the built image, so stopping or
recreating the container does not require downloading or seeding it again.
`docker compose stop pokeapi` stops only this demo service. Do not rebuild on stage.
The upstream release tag is rolling: if its contents change, a fresh build fails
checksum verification. Review the new snapshot/base image and update their pins
intentionally, then rerun the compatibility check below. Retain the prepared image;
it can also be transferred with `docker image save` / `docker image load`.

All fact agents default to `http://127.0.0.1:8000/openapi.yml`. The container serves
the checked-in upstream spec with just its `servers` URL changed to `/`, so tools
call the **same origin** that served the spec. This removes both the remote schema
fetch and public API calls, while keeping the official operations, named lookups
and real pagination. `allow_private_ips: true` explicitly permits this local service.
Host-based agents use a literal localhost URL. Only `13-service.yaml` reads
`POKEAPI_URL`, because it also runs in Compose: there, the environment sets the
spec URL to `http://pokeapi:8000/openapi.yml` instead of the localhost default.

Only JSON facts are local: sprite/cry links in upstream responses still point to
GitHub, but these demos do not fetch them. LLM calls, image pulls/builds and the
eval setup's package installation still require networking. The referee retains
its separate captured evidence; this is not proof of ownership or official combat.
Check snapshot compatibility with the referee (**DATA-1**) without models or entry:

```sh
POKEAPI_TEST_URL=http://127.0.0.1:8000 python3 -m unittest discover -s scripts -p 'test_pokeapi.py' -v
```

## Presentation and automatic service

```sh
demoit -dev
```

Audience: http://localhost:8888/. Presenter controls: http://localhost:8888/media/speaker.html.
**Command-Enter** maximizes a terminal or restores its original size, just like its
green window button. It restores an already maximized terminal first; otherwise,
it targets the focused terminal, or the first terminal if none has focus. The
shortcut also works while typing inside a terminal.
The **+** button opens a terminal with an empty command line. Its red button
closes it; the red button on each widget's original terminal restarts that shell
with the slide's prefilled command, leaving other terminals unchanged.
Commands wait for Enter. Opening a presentation terminal starts the prepared
PokéAPI container on loopback 8000 and ensures a healthy detached Python arena;
later terminals reuse both without clearing entries. Healthy PokéAPI reuse performs
one read-only Docker health/ownership query instead of invoking Compose; readiness
is checked afresh on every terminal launch. The agent chat
listener runs in the application slide’s top-right terminal; start it before
running the client in the bottom-right terminal. The MCP slide uses the same layout: start its HTTP server above,
then run the agent client below. Do not expose DemoIt or the arena publicly.

```sh
python3 scripts/ensure_arena.py status
python3 scripts/ensure_arena.py reset  # explicitly clears local state
python3 scripts/ensure_arena.py stop
```

The arena listens only on loopback 8090. Startup is locked, project-owned and never
adopts or kills a foreign listener. A validated ownership record for an exited
worker is cleaned up automatically and a fresh worker starts when the port is free.
A live arena is never reset automatically: sealed entries are preserved (FAIR-1),
and failed evidence or ownership checks still require human review (DATA-1).
Health checks verify challenge and catalog evidence (DATA-1). Logs are in
`.state/arena-startup.log`.
`DEMO_POKEAPI_AUTOSTART=0` disables container startup. Startup output is kept in
`.state/pokeapi-startup.log`; failures show a warning but leave the terminal usable.
Docker must be running and `docker compose build pokeapi` must have completed
beforehand. Slide startup never reads a Compose `.env` file, builds/pulls an image,
or starts the Compose agent/backend services. PokéAPI recovery checks the container's
immutable ID and Compose project/service labels before removing just that failed
container, then retries startup once. It does not reset Docker Desktop, remove
volumes, kill port occupants or replace containers that are still starting/paused.
`DEMO_ARENA_AUTOSTART=0` disables arena startup; `DEMO_ARENA_PORT` is test-only
because the agent configs target 8090. For external terminals export
`DOCKER_AGENT_DATA_DIR="$PWD/.state/data"`. Presentation terminals retain the existing
Docker Agent configuration and isolate only session data.

Use the installed Docker Agent build with `transform_json`, `max_output_bytes` and structured-output capture. Never print or read credentials.
Team uniqueness is enforced by the arena, not `uniqueItems` in provider-facing tool
schemas (unsupported by some models). A schema-rejected run is an infrastructure
failure, not evidence about team-building strategy.

## Facts, local randomness and guidelines

```sh
docker agent run agents/05-pokemon.yaml "What type is Pikachu?"
docker agent run agents/06-random.yaml "Give me 3 random Pokemon"
```

The random agent asks PokéAPI for its catalog count, draws indices with the fixed
shell command `shuf -i "0-$max" -n 1`, then resolves them through paginated lookup.
It retries duplicate indices, not unwanted Pokémon. IDs have gaps and the public
catalog includes forms, so pagination is deliberate. GNU coreutils provides `shuf`
on macOS; Alpine includes it. This is demo randomness, not a certified lottery.

The introductory lookup and random agent trim `pokemon_retrieve` to
`args: [name, types, stats]`. Team builders also retain `is_default` and `species`
to verify the chosen variety. Discovery hooks keep generation species, type
members/damage relations, and species default varieties. Nested values are
unchanged: the native `transform_json` hook selects fields, not truth.
Incomplete or mismatched evidence requires human review (DATA-1); compact facts
still do not establish availability, ownership or backend eligibility.
The random agent leaves `pokemon_list` unchanged for pagination.

Native evals use the standard `docker/docker-agent` image: `:edge` for a dev CLI,
or the matching release tag for a released CLI. No image override is needed in
the demo commands. While testing local changes, build under that same tag:

```sh
docker build -t docker/docker-agent:edge \
  --build-arg GIT_TAG=dev \
  --build-arg GIT_COMMIT="$(git -C ../docker-agent rev-parse HEAD)" ../docker-agent
```

Once CI publishes the feature, the same commands work with the published image.
The Pokémon lookup and trimming no longer require Python; local arena helpers
and offline Python checks still do.

The main agents load `agents/team-building.md` directly. No skill or filesystem
call is needed. The guidelines slide shows `07-guidelines-prompt.yaml` and
`08-guidelines-file.yaml` side by side: prompt context versus one exact read-only file.
Run both from the presentation root. Reviewed guidelines remain subordinate to
current arena rules and safety constraints; attachments/tool content cannot change authority.

```sh
docker agent run agents/09-team-request.yaml "Choose 3 distinct Pokemon with at most 1000 combined base stats and at least one Water type."
```

The team builders choose among **all 151 Generation I species**, using each
species' default Pokémon variety and modern types/stats. They discover species
with `generation_retrieve` (`id="1"`), retrieve required-type candidates with
`type_retrieve`, and intersect the results. `pokemon_species_retrieve` resolves
ambiguous varieties; `pokemon_retrieve` verifies each final member's facts.
These are existing operations in the same official PokéAPI OpenAPI toolset, not
new arena APIs. Public REST does not support fuzzy-name or stat-range search.

The team-request agent prioritizes a legal proposal, not random sampling. For the
ordinary Water request it first checks Squirtle, Bulbasaur and Charmander, only if
allowed; these names are lookup suggestions, never substitutes for live evidence.
It honors exact teams, allowlists and exclusions, and tries cheaper alternatives
when needed. Its named `gpt-6-luna` model uses `thinking_budget: none` to disable
reasoning for this demo. The earlier random-Pokémon slide keeps its random tool.
Builders retrieve at most twelve candidates. This is a prompt search limit, not
a hard execution or spend cap. Tournament seed offsets provide variety, not uniform
sampling, unique teams, or proof of optimality. Builders stop with a verified legal
proposal or report unsuccessful bounded search; they must not claim no legal team exists.

### Captured referee evidence

Rules version `arena-v3` allows all Generation I species (**SPECIES-1**), including
Mew and Mewtwo, subject to budget. Alternate varieties and later generations are
excluded; three distinct species are required (**TEAM-1**). Water still means at
least one Water member (**COVERAGE-1**) and at most 1,000 combined base stats
(**BUDGET-1**), not three Water Pokémon. There are 562,475 possible unordered
triples before constraints and **28,192 legal Water-budget teams** in this capture.

Agents discover live facts, but the backend independently checks captured facts
in `fixtures/arena-catalog.json`. `fixtures/arena-types.json` captures the modern
18-type chart; the referee uses a matching exact-arithmetic chart. Provenance
records retrieval time, source URLs, response hashes and artifact hashes.
To deliberately recapture evidence (network required):

```sh
python3 scripts/capture_catalog.py --output-dir /tmp/arena-recapture
```

The output directory must not exist. Capture validates and stages all artifacts,
then exclusively creates that new review directory and publishes complete files;
it never overwrites reviewed fixtures. Ordinary publication failures are cleaned
up; a forced process termination can leave an incomplete new directory, so use
only a completed capture whose provenance hashes verify. Compare and review the
new artifacts before deliberately replacing fixtures. Recapture does not silently edit challenge rules or the referee chart;
disagreement fails offline validation and requires review (DATA-1). No live lookup
is needed by the backend at match time.
After this rule upgrade, explicitly restart/reset an owned arena before running
new agents; resetting discards existing entries. Do not reset a running demo
without deciding to clear its state.

This is the team's objective throughout the live story: three distinct allowed
Pokémon, at most 1,000 total base stats, including Water. It is a proposal, not a
referee verdict. The arena names the same constraints `water-budget` for repeatable
practice. The name is an ordinary scenario label,
not randomness. The team-building guidelines map every named challenge to its
budget and required type, and explain the rule IDs returned by eligibility checks;
no `/rules` tool is needed to propose or practice with the slide agent.
The backend remains authoritative. Service/arena configs still discover current scenarios through `/rules`; the slide
builder and its evals use only PokéAPI and sparring.

## From catalog lookup to a business API

The next tool calls a business operation, not another catalog lookup: submit a
plan, run backend logic and receive a measured result. Think pricing a quote or
simulating a plan in your own domain. Here, sparring is a **practice match against
a known opponent**, before competing with another agent. It reveals matchup
weaknesses without submitting an arena entry or awarding leaderboard points.
Beginner, intermediate and advanced are fixed legal
opponents retained from the original seven-species demo, published in `/rules`.
They are benchmark labels, not rankings of the enlarged pool; matchup difficulty
is not always monotonic. Sparring rechecks evidence without enumerating teams.

First call the service directly—no agent or model involved:

```sh
curl --fail-with-body -sS http://127.0.0.1:8090/spar \
  -H 'Content-Type: application/json' \
  --data '{"challenge_id":"water-budget","team":["bulbasaur","charmander","squirtle"],"level":"beginner"}' \
  | jq
```

The request supplies the scenario, three canonical species names and a tier. A
successful response includes eligibility, the fixed opponent, both scores and a
win/loss/draw from the submitted team's perspective. Invalid teams do not fight.

Explain the judge alongside this call, then add the same POST operation as the
`spar_team` API tool in `agents/10-sparring.yaml`. It extends team building with practice,
using catalog lookup plus loaded guidelines, with no rules-discovery or entry tool.
This first API demo prioritizes a quick legal team, not strength: for ordinary
Water practice it tries Squirtle, Bulbasaur and Charmander first, verifies their
facts, and stops at the first legal team. It practices once per requested tier
and reports the result without searching again after a loss:

```sh
docker agent run agents/10-sparring.yaml "Build a team for water-budget and spar with that same team against beginner."
```

The agent selects its own team in this new session; it does not inherit the curl
example's team or outcome. `11-builder.yaml` adds a structured plan, keeping the
same PokéAPI discovery/fact tools and sparring operation for the eval story.

There is **no separate `/validate` tool or API step**. Sparring checks eligibility
before scoring; local entry and the first duel also check eligibility internally.
The model proposes; backend code enforces team size, allowed species, budget and type
coverage. Unknown/incomplete/conflicting evidence requires human review (**DATA-1**).
A successful practice result establishes `ready`; an untested recommendation is `proposed`.

The judge sums each attacker's base-stat total times its best own-type effectiveness
across every cross-team pair. Same formula on both sides; larger score wins, equality
draws. No random combat, moves, turns, levels, STAB or model adjudication.

## Native evals: the same agent, the same tools

The eval story starts with the Water request already demonstrated: three distinct
allowed Pokémon, at most 1,000 base stats, including Water. `agents/11-builder.yaml`
uses live `generation_retrieve`, `type_retrieve`, `pokemon_species_retrieve`,
`pokemon_retrieve`, and the existing `spar_team`. Its `team_plan` structured output
makes status, team and results easy to check. Discovery and lookup use the same
native OpenAPI toolset and JSON field selectors as the live agents. No local
search endpoint, public-API replacement or preparation workspace is needed.
The standard Docker image must also include the native hook.

From the repository root, with Docker Desktop running and provider access configured:

```sh
# Presentation terminals already start this same service.
python3 scripts/ensure_arena.py start
docker agent eval agents/11-builder.yaml evals/arena --repeat 5 --judge-model openai/gpt-5.6-terra
```

These commands pin the OpenAI judge (`openai/gpt-5.6-terra`
in v1.147.0), independent of the agent model/flavor. Use the same CLI version for
baseline and experiment runs; recapture the baseline if the default judge changes.

| Development case | Expectation |
|---|---|
| `water-proposal` | Legal team from retrieved facts; no practice yet |
| `water-beginner` | The live demo request; practice with the final team |
| `honest-loss` | Keep the specified starters; report the intermediate loss honestly |
| `over-budget` | Reject the specified 1,024-stat team, without silently repairing it |
| `duplicate-team` | Reject repeated Squirtle, without silently repairing it |

Optional `evals/arena-stretch/water-advanced.json` retains legal, honest practice
**and** an advanced win as a separate stretch goal.

Each case is a native session JSON containing a user request, exact assertions and
short `relevance` criteria. Assertions check returned fields and tool attempts;
the native LLM judge sees the transcript and checks successful evidence, arithmetic,
constraint handling and truthful scores. A call alone does not establish success.
There is no custom Python grader. Shape is not truth (DATA-1).

### A repeatable live story

Run five **correctness** cases with `--repeat 5`: 25 repetitions, not a single
lucky answer. The unchanged advanced-win request now lives in `evals/arena-stretch`:
it remains an optional strength experiment, not part of correctness percentages.
No assertion or relevance criterion was weakened. Do not interpret `pass@5`
(passed once) as reliability; inspect each repetition and `pass^5` (passed every time).

The slides show native `docker agent eval` commands with the same repeat count
and explicit judge, using Docker Agent's default concurrency. No command wrapper, result copying or automatic
baseline selection is involved:

```sh
docker agent eval agents/11-builder.yaml evals/arena --repeat 5 --judge-model openai/gpt-5.6-terra
jq '.sessions[] | select(.eval_result.passed == false) | {case: .title, failures: .eval_result.failures}' evals/baselines/arena.json
docker agent eval agents/11-builder.yaml evals/arena --flavor checked-totals --baseline evals/baselines/arena.json --repeat 5 --judge-model openai/gpt-5.6-terra
docker agent eval agents/11-builder.yaml evals/arena --flavor alternate-model --baseline evals/baselines/arena.json --repeat 5 --judge-model openai/gpt-5.6-terra
```

The inspection and comparison commands above use the explicitly named **captured
rehearsal**. To inspect and compare the run you just performed, replace
`evals/baselines/arena.json` in both `jq` and `--baseline` with the JSON path printed
by the native baseline command, for example `evals/arena/results/<run-name>.json`.
Keep the same cases, config, guidelines, setup, CLI, image, judge, provider and
backend evidence during the comparison; rerun baseline if they change.
Regression still returns nonzero, and native result files stay unmodified.

`evals/baselines/arena.json` is a byte-for-byte fallback teaching copy of the first
final repeat-5 rehearsal: **17/25 passed**. It preserves every failure, including
incorrect arithmetic and contradictory prose totals on duplicate and over-budget
requests. The inspection slide and its source pane both show this explicitly
captured example by default. Exact live counts can vary.
Use `session.eval_result.passed`; `summary.failed_evals` counts execution errors.
The baseline is imperfect by design of the fast model, not by inserting bad answers.

`evals/stability/` retains both consecutive final rehearsals for every variant,
with checksums, input hashes, CLI/image IDs, commands and per-case counts. Older
six-case measurements in `evals/measurements/` are historical and not the current
live comparison. Captures are never edited to improve scores.

### Let an agent iterate on the prompt

The optional “An agent improves the prompt” slide uses a dedicated development
agent, `agents/11-prompt-optimizer.yaml`, with filesystem and shell tools:

```sh
docker agent run agents/11-prompt-optimizer.yaml "Improve the builder prompt using development evals. Try at most three candidates."
```

Run from the repository root with the same prerequisites as the native evals.
It creates a unique `.state/prompt-loop/run.*` workspace, copies the builder and
both support files (`team-building.md`, `eval-setup.sh`) into `configs/`, and
measures a **fresh baseline**. Native eval mounts the candidate's parent at
`/configs`, so these support files must accompany every candidate.

The loop is: inspect recurring failures → state one hypothesis → edit only
`agents.root.instruction` → save the attempt's YAML → run the same five cases
with `--repeat 5` and `--judge-model openai/gpt-5.6-terra`. Every run has its own
`--output` directory; comparisons use `--baseline` with the exact **Sessions JSON**
path printed by the CLI. That file contains the summary, transcripts and eval results. Count
`sessions[].eval_result.passed` out of 25, not execution errors or pass-at-least-once.
Keep a change only when more repetitions pass **and** the native gate reports no
regression; inspect per-case failures, cost and latency too. Revert rejected edits.
Stop at three candidate eval runs or a best score of 25/25; do not cherry-pick retries.
If nothing improves, say so. There is no captured claim that prompt-only tuning wins.

All candidate YAMLs and raw results are retained; the source builder, captured
baselines, tests, guidelines, setup, model, tools, hooks and schemas stay unchanged.
The final report proposes the best YAML for **human review**, never automatic
promotion. Freeze the reviewed config before a human runs held-out cases separately.
The optimizer must not inspect `evals/arena-heldout`, other captures, credentials
or frozen `old/` examples. Evidence and privacy rules remain unchanged (DATA-1,
FAIR-1); no entry, tournament, service lifecycle change or arena reset is authorized.

Strict mode asks before every shell command; inspect it and avoid `--yolo` or an
always-allow grant. Filesystem reads are scoped to the source/support files,
development cases and workspace; writes are scoped to the workspace. **These
limits do not sandbox shell access**: human command review and instructions still
matter. Full eval shell calls need an explicit 600-second timeout. Infrastructure
failures or incomplete results require review rather than prompt tuning.
The optimizer's budget covers its own metered calls, **not child eval/judge spend**;
up to four repeat-5 suites are separate paid runs. External commands can outlive
an interruption/timeout: stop only owned processes and retain incomplete evidence.

### The small container plumbing detail

Native evals isolate each case in an Alpine container. The case's standard `setup`
field runs `agents/eval-setup.sh`, which copies the reviewed guidelines from the
read-only config mount, installs jq for the service-health check and socat for forwarding,
and forwards the container's loopback 8090 to the **existing** host sparring service.
Docker Desktop's `host.docker.internal` is required. Socat forks per connection and
propagates EOF, so pooled HTTP connections reconnect after the upstream keep-alive
expires. The old nested-netcat relay left stale sockets open; those timeout-tainted
experiments are excluded from model comparisons. The agent still calls the same
`http://127.0.0.1:8090/spar`; no extra endpoint or tool is introduced. The host service
remains loopback-only, with its Host/origin checks intact. Setup checks service health
and fails early if it is unavailable. No entries are submitted or state reset.

PokéAPI now runs locally: the setup also forwards loopback 8000 to the host
container and checks both the API and spec before running the agent. Bounded
readiness retries prevent a race with the background forwarder's startup; persistent
failures still stop the case for human review (DATA-1). These remain
integration evals, not fully hermetic tests (models and package installation use
the network). The arena's
existing synthetic judge still uses its captured backend data. Record outages or
conflicting facts separately and require review (DATA-1), rather than interpreting
them as a bad team-building strategy.

### Improve one thing and rerun

The `checked-totals` flavor appends an instruction and the same fixed
`sum_team_stats` tool as before: sum eighteen retrieved base stats with awk, copy
that result into `stat_total`, and avoid a conflicting second calculation in prose.
Arithmetic assistance is not eligibility evidence; DATA-1 still requires review
on missing/failed facts. The model-only variant keeps the baseline prompt and tools.

We also compact `pokemon_retrieve` responses to keep all evidence inside the
native judge's **500-byte tool-response excerpt**. Identity, default-variety flag,
species name, all six base stats and type names are unchanged; unused URLs, effort
and slot metadata are removed. No computed totals or guessed facts are injected.
This stops the judge randomly missing Water-type evidence that arrived after the
cutoff. jq is already installed by eval setup; host runs need jq too.

The alternate uses **`gpt-6-sol`**, not `gpt-6.1-sol`: this CLI recognizes real
`thinking_budget: none` for Sol/Luna, but normalizes `none` away for the old 6.1
name. Both current models therefore explicitly disable thinking. We tried lower
sampling temperature and stronger shortlist prompts, but did not keep them:
they did not reliably remove variation and sometimes increased search latency.

| Variant (five cases × five repeats) | Rehearsal 1 | Rehearsal 2 | Median agent time | Whole runs |
|---|---:|---:|---:|---:|
| Baseline Luna, no thinking | 17/25 | 18/25 | 7.5–7.6s | 87–111s |
| Luna + checked totals | 25/25 | 24/25 | 9.3–10.1s | 93–99s |
| Model-only Sol, no thinking | 21/25 | 24/25 | 7.9–9.3s | 88–90s |

The useful story is stable **ordering and failure category**, not a guaranteed
score: arithmetic fails repeatedly in baseline, largely disappears with the tool,
and improves but still varies with the model change. The second patch run had one
incomplete model turn after generation lookup; it remains a failed repetition.
These are native judge pass counts, not independently audited correctness rates:
some passing baseline judgments acknowledge contradictory prose arithmetic.
Baseline round 2 also contains an invalid lookup of `water-budget` as a Pokémon
(404), retained for DATA-1 review—not presented as an infrastructure outage.
No majority vote, best-of-five selection or ignored failure. Infrastructure/provider
failures and incomplete output require separate diagnosis (DATA-1).

These historical rehearsals used concurrency 5; the live commands now use the
CLI default. Their whole-run timings are not predictions for default concurrency.
Median agent time is first-to-last transcript time; run duration includes setup
and judge. These are integration evals: provider/network failures are still possible.
For live comparison, use the native commands above with your printed result path. The optional
unchanged stretch goal is deliberately separate:

```sh
docker agent eval agents/11-builder.yaml evals/arena-stretch --flavor checked-totals --repeat 5 --judge-model openai/gpt-5.6-terra
```

Keep, revise or drop based on repeat evidence, legality, honest outcomes, latency
and spend—not whether a larger model wins one open-ended search.

Freeze the chosen configuration before using the held-out requests: intermediate
practice and a proposal excluding the Kanto starters. They keep the same Water
constraints and tools, not another environment or new challenge taxonomy.

```sh
docker agent eval agents/11-builder.yaml evals/arena-heldout --flavor checked-totals
```

The earlier frozen arithmetic patch passed 6/6 held-out judge checks across three
repeats. An independent trace audit found one no-starters run retrieved 13 candidates,
exceeding the 12-candidate prompt limit; a judge pass is not full policy compliance. They have now
been inspected and are no longer unseen; replace them
for the next experiment. Ordinary failed checks are reported; a baseline regression
returns nonzero. The runner uses privileged containers/autonomous approval: reviewed
synthetic configs only, not a security sandbox.

## Two independent agents and the web arena

```sh
docker agent run --safety strict agents/15-arena.yaml "Build for water-budget and enter a local match as agent-a. Submit the team; let the arena handle the match."
docker agent run --safety strict agents/15-arena.yaml --flavor type-aware "Build for water-budget and enter a local match as agent-b. Submit the team; let the arena handle the match."
```

The two submission slides embed http://127.0.0.1:8090/ on the left of each terminal:
seal A, then seal B independently. The second valid entry triggers backend judging,
and the result appears alongside the second submission without another command. The arena permits
framing only from DemoIt at `http://localhost:8888` or `http://127.0.0.1:8888`.
You can still open the arena separately. The page opens as a spectator
view: submitted IDs, judged matches and standings. There are no manual controls
or standalone rules panel.
Public arena snapshots omit both teams until the backend judges the duel (**FAIR-1**).
Sealing locks a submission; it does not hide the team from its own session or the backend.
One immutable entry per challenge/ID; byte-identical retries are allowed. Each new
eligible entry automatically fights every existing entry for its challenge, once
per ID pair. The arena rechecks both teams and records the results atomically;
failed evidence publishes no match and leaves earlier entries sealed. Agents have
no duel tool or duel endpoint, and retries never award additional points.

The arena agent defaults to strict safety: lookup/practice tools are allowed, but
entry requires confirmation; judging is automatic. IDs are demo labels, not authenticated identities.

## Final demo: 32 background players

`16-tournament.yaml` coordinates 32 independent background invocations of one
player agent. The user explicitly requests the local tournament. Each player
discovers Generation I and required-type candidates, explores a shortlist of up
to twelve Pokémon with seed-varied offsets, and submits one sealed team to a
fixed seed slot. It has no sparring tool; no unique-team or optimality guarantee.
The coordinator launches four batches of eight, below docker-agent's 20-task
concurrency cap, and joins every batch before finishing. Provider calls are paid;
these demo configs do not impose runtime cost, token or time budgets.

```sh
docker agent run agents/16-tournament.yaml "Run the local tournament devoxx-cup for water-budget with 32 background players."
```

The arena page shows a tennis-style bracket: seeds 1–2, 3–4, and so on; adjacent
winners meet until the final. Thirty-one matches across five rounds are automatic.
A combat draw stays a draw; the lower original seed advances as the published
bracket tie-break. Tournament entries/results are separate from the earlier
round-robin standings. IDs are fixed before players arrive, retries cannot change
teams or duplicate matches, and failed evidence blocks advancement for review.
Use a new tournament ID for a new run. At most eight brackets are kept in memory;
resetting the arena clears them together with ordinary entries.

## Fast final builders and reliability

The served builder, local-match builder and tournament players use `gpt-6-luna`
with thinking disabled, cheap required-type shortlists and the same fixed
`sum_team_stats` tool. The tool uses POSIX awk (available in the stock agent image),
not jq or Python. It sums inputs; successful live lookup and backend evidence checks
remain mandatory (DATA-1). The tournament varies cheap candidates by seed, stopping
at the first verified legal team instead of spending time filling the budget.
There is no claim of optimality, unique teams or guaranteed wins.

We ran proposal checks with the final configs' model, instructions and building tools,
under a restricted permission overlay denying entry, sparring and background
launches. Checks span Water and other published constraints; no match or tournament
was requested. The checker verifies fixture legality and accurate totals, rejects
explicit review statuses, but does not audit live retrieval evidence:

- `15-arena.yaml`: **100/100** fixture-legal team/total outputs, median **11.6s**.
- `16-tournament.yaml` player: **99/100** fixture-legal team/total outputs, median **10.2s**.
  One output selected later-generation Politoed and was rejected (DATA-1); no entry
  was authorized or accepted.

These observations meet the demo's 99% target in this sample, not proof of a 99%
population success rate. They do not test successful live evidence or submission/orchestration reliability.
Proposal timing includes CLI startup and validation, unlike native transcript timing.
Backend validation still gates all entries under TEAM-1, SPECIES-1, BUDGET-1,
COVERAGE-1 and DATA-1; FAIR-1 still keeps teams sealed. Repeat the proposal checks
without granting entry authority (paid model calls):

```sh
python3 scripts/check_team_reliability.py agents/15-arena.yaml --repeat 100 --output .state/reliability/arena.json
python3 scripts/check_team_reliability.py agents/16-tournament.yaml --agent-name player --repeat 100 --output .state/reliability/player.json
```

## Endpoints and state

| Endpoint | Purpose | State |
|---|---|---|
| `GET /rules`, `/challenges/{name}` | Current published scenarios and judge | Read-only |
| `GET /catalog/{name}` | Captured canonical facts for evals | Read-only |
| `POST /spar` | Check legality and judge practice | Stateless |
| `POST /join` | Check, seal, and automatically judge eligible pairs | Atomic mutation |
| `GET /state`, `/leaderboard`, `/matches/{id}` | Public snapshots | Read-only |
| `POST /tournaments`, `/tournaments/join` | Create a bracket and seal assigned player entries | Atomic mutation |
| `GET /tournaments/{id}` | Read the bracket and champion | Read-only |

Internal rule IDs remain backend diagnostics, not presentation jargon:
TEAM-1, SPECIES-1, BUDGET-1, COVERAGE-1, DATA-1, FAIR-1.

## Services, containers and validation

`13-service.yaml` exposes the same single-agent builder over OpenAI-compatible chat and MCP.
It keeps structured output because the application client parses and validates the
plan. The separate `12-team.yaml` coordinator is a TUI demonstration with no machine
consumer: it returns a plain-language answer, and its specialist handoff is not
schema-enforced.
The application slide stacks two terminals on the right. Start the chat listener
in the top terminal, wait until it is listening, then run the client below:

```sh
docker agent serve chat agents/13-service.yaml --listen 127.0.0.1:8080
```

The client makes one standard `POST /v1/chat/completions` request with
`model: "root"` (the exposed agent name) and `stream: false`. The server runs the
agent's tools and returns the final plan in `choices[0].message.content`.
There is no native session API or SQLite database. The client prints a short
waiting message, then a numbered team card, total stats, an aligned sparring
table and a wrapped explanation rather than raw JSON. Completion and plan checks still happen before displaying
the result; proposals are explicitly labeled as untested. For authenticated
servers, the client sends `DEMO_API_TOKEN` as a bearer token; start the server with
`--api-key-env DEMO_API_TOKEN` to require it.
The MCP slide also stacks a server terminal above its client. Start the HTTP
MCP server on loopback 8081, then the agent client, which connects to that server
rather than launching a separate stdio process:

```sh
docker agent serve mcp agents/13-service.yaml --http --listen 127.0.0.1:8081
```

Run both clients from the repository root:

```sh
python3 scripts/api_client.py
docker agent run --exec agents/14-mcp-client.yaml "Propose a team for water-budget."
```

The MCP client uses `--exec` for this one-shot request. In the current Docker Agent
build, TUI startup can initialize MCP concurrently with the initial prompt; that
first turn can see zero tools even when the server is already listening. Headless
execution avoids that overlap. To use the TUI, launch without a prompt, wait until
its tools have loaded, then submit the request.

To check discovery without calling the model, run
`docker agent debug toolsets agents/14-mcp-client.yaml`; it should list `root`.
This is a connection diagnostic, not a warm-up for a separate client process.

Both consume the builder; 8090 remains the arena backend, not an agent API.
The HTTP MCP server has no entry or duel tools; the client only permits the builder tool.
The Compose file uses `docker/docker-agent` directly, with no wrapper
Dockerfile. It illustrates deployment boundaries: read-only workspace mounts,
provider credentials injected through the environment, separate runtime state and
loopback-published access without a demo API token.
Its sibling `arena` service runs the synthetic backend on the Compose network;
the `pokeapi` sibling serves snapshot-backed canonical facts and the local OpenAPI spec.
The `container` flavor points the builder’s shared rules and sparring tools at
`http://arena:8090`.
The builder waits for both backend and PokéAPI health. Chat port 8080 and PokéAPI
port 8000 are published only on `127.0.0.1`; the arena is private. No host networking
or host arena startup is needed for Compose.
Without that flavor, host-based slides still use the native loopback arena.
Read-only mounts are not a network sandbox. Keep published listeners on loopback.

### Live Compose slide: preparation and two terminals

The “Run the packaged agent” slide follows the Compose source slide. It has two
side-by-side terminals: attached Compose logs on the left, the existing Python
application client on the right. Both commands wait for Enter.

Before presenting, from the repository root:

1. Start Docker Desktop and prepare the images while online:

   ```sh
   docker compose --env-file /dev/null build pokeapi
   docker compose --env-file /dev/null pull pokemon-arena arena
   ```

   The agent image must support `transform_json`, `max_output_bytes` and
   structured-output capture. Compose uses `docker/docker-agent:latest`, not the
   host CLI or the eval runner's `:edge` tag. If those features are only in your
   local source, build that source under the exact Compose tag instead of pulling
   the agent image:

   ```sh
   docker compose --env-file /dev/null pull arena
   docker build -t docker/docker-agent:latest \
     --build-arg GIT_TAG=dev \
     --build-arg GIT_COMMIT="$(git -C ../docker-agent rev-parse HEAD)" ../docker-agent
   ```

2. Install the [1Password CLI](https://developer.1password.com/docs/cli/get-started/)
   (`brew install 1password-cli`) on the Mac. Enable **Settings → Developer →
   Integrate with 1Password CLI** in the 1Password desktop app and unlock it.
   Your account must be able to read `op://Team AI Agent/cagent-proxy/OPENAI_API_KEY`.
   The slide resolves this reference using host-side `op run`; approve its
   authentication prompt when asked. No raw key needs to be exported before
   launching DemoIt. The key must have access to the configured `gpt-6-luna` model;
   model calls still require network access. An API key is not needed for PokéAPI
   or the synthetic arena alone.
3. Stop your earlier host chat listener on **8080** with Ctrl-C in its own terminal.
   Keep the host arena on **8090** running for the later leaderboard slides;
   Compose's arena is a separate private service. Port **8000** must be free or
   occupied by this project's prepared PokéAPI container. Use the same repository
   root/default Compose project as the slide startup helper so it is reused.

On stage, start the **left terminal** in the foreground (no `-d` or `--wait`):

```sh
OPENAI_API_KEY='op://Team AI Agent/cagent-proxy/OPENAI_API_KEY' op run -- docker compose --env-file /dev/null up --no-build --pull never
```

`op run` resolves the reference on the Mac and supplies the key to its Compose
subprocess. Compose then injects `OPENAI_API_KEY` into the agent container's
environment. No launcher, temporary secret file, container-side `op` or custom
image is needed; the read-only root filesystem is unchanged. The command ignores
Compose `.env` files and writes no key into project files.

This is environment injection, not a Docker secret: Docker administrators can
read the key through container inspection. `op run` masks secrets in output by
default, but masking is best-effort, not a security boundary. Do not print the
resolved Compose configuration or dump the container environment.
The empty default in Compose permits build/pull/stop and PokéAPI-only startup
without credentials; starting the agent without a resolved key fails its
provider-key check. See
[`op run`](https://developer.1password.com/docs/cli/reference/commands/run/).

Wait for healthy dependencies and the chat server's listening message on 8080,
then run the **right terminal**:

```sh
python3 scripts/api_client.py
```

The default client request proposes a Water team without practice or arena entry.
Missing/conflicting evidence still requires human review (DATA-1); sealed entries
remain governed by FAIR-1. This deployment is not certified by the separate
builder evals; rehearse this exact service/image with the client before the talk.

After the client completes, Ctrl-C in the left terminal stops the attached services,
including PokéAPI. Do not rely on leaving the slide to stop Compose containers;
if needed, run `docker compose --env-file /dev/null stop` from the repository root.
The next slide terminal restarts prepared PokéAPI automatically. The host arena
and its entries remain untouched; do not reset it or use `down -v`.

```sh
python3 scripts/validate.py --schema /Users/dgageot/src/docker-agent/agent-schema.json
python3 -m unittest discover -s scripts -p 'test_*.py' -v
node --check .demoit/js/demoit.js
shellcheck .demoit/.bashrc agents/eval-setup.sh
```

Requires PyYAML/jsonschema for config validation and regression tests. Demo and backend runtime helpers use the Python standard library. `scripts/`
contains demo clients, service/validation helpers and regression tests;
other slide-authoring utilities are not retained. `.demoit/.bash_history` is maintained directly.

The arena UI regression tests use a mocked read-only backend and Node.js; no
browser, live service or model is needed.

Frozen `old/` and credential files remain untouched. Stop only owned services; retain eval evidence.
