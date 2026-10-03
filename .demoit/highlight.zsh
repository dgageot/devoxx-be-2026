# Demo command colors, refreshed before each ZLE redraw.
_demoit_highlight_commands() {
    emulate -L zsh
    setopt extendedglob

    region_highlight=("${(@)region_highlight:#* memo=demoit}")
    local -a match mbegin mend
    if [[ $BUFFER != (#b)([[:blank:]]#docker[[:blank:]]##agent)([[:space:]]*|) ]] &&
       [[ $BUFFER != (#b)([[:blank:]]#docker-agent)([[:space:]]*|) ]]; then
        return 0
    fi

    local prefix_end=$mend[1]
    local -a quoted_regions
    local quote='' char
    local -i i start=0 ansi_quote=0 escaped_dollar=0 command_end=${#BUFFER}
    # Color literal quoted arguments; this is not a shell-expansion parser.
    for ((i = prefix_end + 1; i <= ${#BUFFER}; i++)); do
        char=${BUFFER[i]}
        if [[ $char == '\' && ( $quote != "'" || $ansi_quote == 1 ) ]]; then
            if [[ ${BUFFER[i+1]} == '$' ]]; then
                escaped_dollar=$((i + 1))
            fi
            ((i++))
        elif [[ -z $quote && ( $char == ';' || $char == '|' || $char == '&' || $char == $'\n' ) ]]; then
            command_end=$((i - 1))
            break
        elif [[ -z $quote && ( $char == '"' || $char == "'" ) ]]; then
            quote=$char
            start=$((i - 1))
            ansi_quote=0
            if [[ $char == "'" && ${BUFFER[i-1]} == '$' ]] && ((i - 1 != escaped_dollar)); then
                ansi_quote=1
            fi
        elif [[ -n $quote && $char == "$quote" ]]; then
            quoted_regions+=("$start $i fg=12, memo=demoit")
            quote=''
        fi
    done
    if [[ -n $quote ]]; then
        quoted_regions+=("$start ${#BUFFER} fg=12, memo=demoit")
    fi
    # The comma keeps memo tags compatible with Zsh versions before 5.9.
    region_highlight+=("0 $prefix_end fg=default, memo=demoit")
    region_highlight+=("$prefix_end $command_end fg=green, memo=demoit")
    region_highlight+=("${quoted_regions[@]}")
    return 0
}

if [[ -o interactive ]]; then
    zmodload zsh/zle
    autoload -Uz add-zle-hook-widget
    add-zle-hook-widget zle-line-pre-redraw _demoit_highlight_commands
fi
