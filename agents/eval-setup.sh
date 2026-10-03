#!/bin/sh
# Native eval containers keep the same loopback sparring URL as the live demo.
set -eu
mkdir -p agents
cp /configs/team-building.md agents/
apk add --no-cache jq socat >/dev/null
# Fork per connection and propagate EOF so pooled HTTP sockets reconnect correctly.
socat TCP-LISTEN:8090,bind=127.0.0.1,reuseaddr,fork TCP-CONNECT:host.docker.internal:8090 &
socat TCP-LISTEN:8000,bind=127.0.0.1,reuseaddr,fork TCP-CONNECT:host.docker.internal:8000 &
# The background listener may not have bound its port yet.
for pokeapi_attempt in 1 2 3 4 5; do
    if {
        busybox wget -q -T 2 -O /tmp/pokeapi-health.json http://127.0.0.1:8000/api/v2/pokemon/pikachu/ &&
        jq -e -s 'length == 1 and (.[0] | .id == 25 and .name == "pikachu")' /tmp/pokeapi-health.json >/dev/null &&
        busybox wget -q -T 2 -O /dev/null http://127.0.0.1:8000/openapi.yml
    } 2>/tmp/pokeapi-health.log; then
        break
    fi
    if [ "$pokeapi_attempt" = 5 ]; then
        cat /tmp/pokeapi-health.log >&2
        printf '%s\n' 'PokéAPI unavailable (API or spec) after retries: run docker compose up -d --wait pokeapi on the host; human review required (DATA-1).' >&2
        exit 1
    fi
    sleep 0.2
done
for attempt in 1 2 3 4 5; do
    if busybox wget -q -T 1 -O /tmp/arena-health.json http://127.0.0.1:8090/health && jq -e -s '
        length == 1 and (.[0] |
            .status == "ok" and .synthetic == true and .loopback_only == true and
            .deployment == "native")
    ' /tmp/arena-health.json >/dev/null; then
        exit 0
    fi
    [ "$attempt" = 5 ] || sleep 0.2
done
printf '%s\n' 'Sparring unavailable: start scripts/ensure_arena.py on the host (Docker Desktop required).' >&2
exit 1
