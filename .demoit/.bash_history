docker agent run  --lean 01-pirate.yaml
docker agent run --model=anthropic/claude-haiku-4-5 default
docker agent doctor
docker agent run --lean 02-polite.yaml "we need this thing fixed asap its broken again"
docker agent run 02-polite.yaml
docker agent run --exec 02-polite.yaml "Make this clearer"
echo "Make this clearer" | docker agent run --exec 02-polite.yaml -
docker agent serve chat 02-polite.yaml
curl -sSf http://127.0.0.1:8083/v1/chat/completions -d '{"model":"root","messages":[{"role":"user","content":"we need this thing fixed asap its broken again"}],"stream":true}'
docker agent run 03-gopher.yaml
docker agent debug toolsets 04-pokemon.yaml
docker agent debug toolsets 05-pokemon.yaml
docker agent debug tool 04-pokemon.yaml pokemon_retrieve '{"id":"pikachu"}' | jq
docker agent debug tool 05-pokemon.yaml pokemon_retrieve '{"id":"pikachu"}' | jq
docker agent run 05-pokemon.yaml "What type is Pikachu?"
docker agent run 05-pokemon.yaml "Compare the three Kanto starters by base stat total. Produce a nice table output"
docker agent run 06-random.yaml "Give me 3 random Pokemon"
docker agent run agents/07-guidelines-prompt.yaml "Explain the water-budget team-building guidelines."
docker agent run agents/08-guidelines-file.yaml "Explain the water-budget team-building guidelines."
docker agent run agents/09-team-request.yaml "Choose 3 distinct Pokemon with at most 1000 combined base stats and at least one Water type."
curl --fail-with-body -sS http://127.0.0.1:8090/spar -H 'Content-Type: application/json' --data '{"challenge_id":"water-budget","team":["bulbasaur","charmander","squirtle"],"level":"beginner"}' | jq
docker agent run agents/10-sparring.yaml "Build a team for water-budget and spar with that same team against beginner."
docker agent eval agents/11-builder.yaml evals/arena --repeat 5 --judge-model openai/gpt-5.6-terra
jq '.sessions[] | select(.eval_result.passed == false) | {case: .title, failures: .eval_result.failures}' evals/baselines/arena.json
docker agent eval agents/11-builder.yaml evals/arena --flavor checked-totals --baseline evals/baselines/arena.json --repeat 5 --judge-model openai/gpt-5.6-terra
docker agent eval agents/11-builder.yaml evals/arena --flavor alternate-model --baseline evals/baselines/arena.json --repeat 5 --judge-model openai/gpt-5.6-terra
docker agent run agents/11-prompt-optimizer.yaml "Improve the builder prompt using development evals. Try at most three candidates."
docker agent eval agents/11-builder.yaml evals/arena-stretch --flavor checked-totals --repeat 5 --judge-model openai/gpt-5.6-terra
docker agent eval agents/11-builder.yaml evals/arena-heldout --flavor checked-totals --repeat 5 --judge-model openai/gpt-5.6-terra
docker agent run agents/12-team.yaml "Propose a team for water-budget and spar against beginner."
docker agent run agents/12-team.yaml --flavor all-strong "Propose a team for water-budget and spar against beginner."
docker agent run agents/12-team.yaml --flavor mixed "Propose a team for water-budget and spar against beginner."
docker agent serve chat agents/13-service.yaml --listen 127.0.0.1:8080
python3 scripts/api_client.py
python3 scripts/trace_viewer.py
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318 OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=false docker agent serve chat agents/13-service.yaml --listen 127.0.0.1:8082 --otel
python3 scripts/api_client.py --url http://127.0.0.1:8082
docker agent serve mcp agents/13-service.yaml --http --listen 127.0.0.1:8081
docker agent run --exec agents/14-mcp-client.yaml "Propose a team for water-budget."
OPENAI_API_KEY='op://Team AI Agent/cagent-proxy/OPENAI_API_KEY' op run -- docker compose --env-file /dev/null up --no-build --pull never
python3 scripts/api_client.py
docker compose --env-file /dev/null stop
docker agent run --safety strict agents/15-arena.yaml "Build for the water-budget challenge and enter a local match as agent-a. Submit the team; let the arena handle the match."
docker agent run --safety strict agents/15-arena.yaml --flavor type-aware "Build for the water-budget challenge and enter a local match as agent-b. Submit the team; let the arena handle the match."
curl --fail-with-body -sS http://127.0.0.1:8090/leaderboard | jq
docker agent run agents/16-tournament.yaml "Run the local tournament devoxx-cup for water-budget with 32 background players."
python3 scripts/ensure_arena.py reset
