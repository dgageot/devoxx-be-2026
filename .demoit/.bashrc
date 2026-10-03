# shellcheck shell=bash
# Find the presentation root from any scoped demo folder.
export DEMO_ROOT="$PWD"
while [ ! -f "$DEMO_ROOT/demoit.html" ] || [ ! -d "$DEMO_ROOT/.demoit" ]; do
    if [ "$DEMO_ROOT" = / ]; then
        printf '%s\n' 'Unable to locate the demo presentation root.' >&2
        break
    fi
    DEMO_ROOT="$(dirname "$DEMO_ROOT")"
done
mkdir -p "$DEMO_ROOT/.state/data"
export DOCKER_AGENT_DATA_DIR="$DEMO_ROOT/.state/data"
export TELEMETRY_ENABLED=false DOCKER_AGENT_HIDE_TELEMETRY_BANNER=1

# Reuse the prepared PokéAPI container; never build or download during a slide.
if [ "${DEMO_POKEAPI_AUTOSTART:-1}" != 0 ] && [ -f "$DEMO_ROOT/compose.yaml" ]; then
    if command -v python3 >/dev/null 2>&1; then
        python3 "$DEMO_ROOT/scripts/ensure_pokeapi.py" --root "$DEMO_ROOT" || true
    else
        printf '%s\n' 'PokéAPI unavailable: python3 is required for the startup helper.' >&2
    fi
fi

# Reuse one detached arena; opening a new slide must not reset its entries.
if [ "${DEMO_ARENA_AUTOSTART:-1}" != 0 ] && [ -f "$DEMO_ROOT/scripts/ensure_arena.py" ]; then
    if command -v python3 >/dev/null 2>&1; then
        python3 "$DEMO_ROOT/scripts/ensure_arena.py" start --root "$DEMO_ROOT" --quiet || true
    else
        printf '%s\n' 'Arena unavailable: python3 is required for the startup helper.' >&2
    fi
fi

# Prompt variables are consumed by the interactive shell.
# shellcheck disable=SC2034
if [ -n "${ZSH_VERSION:-}" ]; then
    precmd_functions=()
    unfunction precmd 2>/dev/null || true
    PROMPT='$ '
    RPROMPT=''
    PROMPT2='> '
    RPS2=''
    # Keep Zsh-only syntax out of this Bash-compatible setup file.
    # shellcheck disable=SC1091
    source "$DEMO_ROOT/.demoit/highlight.zsh"
else
    unset PROMPT_COMMAND
    PS1='$ '
    PS2='> '
fi
