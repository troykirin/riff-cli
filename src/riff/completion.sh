#!/bin/bash
# Bash/Zsh completion script for riff-cli
#
# Installation:
#   bash:  source /path/to/completion.sh  (add to ~/.bashrc)
#   zsh:   source /path/to/completion.sh  (add to ~/.zshrc)
#
# Usage:
#   riff [TAB][TAB]              # Show commands
#   riff sca[TAB]                # Complete to "scan"
#   riff search --[TAB]          # Show flags for search
#   riff scan /path/[TAB]        # File completion

_riff_completion() {
    local cur prev words cword

    # Bash-specific: get current word, previous word, all words, and word index
    if [[ -n "${BASH_VERSION:-}" ]]; then
        COMPREPLY=()
        cur="${COMP_WORDS[COMP_CWORD]}"
        prev="${COMP_WORDS[COMP_CWORD-1]}"
        words=("${COMP_WORDS[@]}")
        cword=$COMP_CWORD
    fi

    # Zsh-specific: convert to bash-like variables
    if [[ -n "${ZSH_VERSION:-}" ]]; then
        cur="${words[CURRENT]}"
        prev="${words[CURRENT-1]}"
    fi

    # All available commands in riff-cli
    local all_commands="search browse visualize scan fix tui graph graph-classic sync:surrealdb"

    # Global flags (available for all commands)
    local global_flags="--help --qdrant-url"

    # Command-specific flags
    local search_flags="--limit --min-score --uuid --ai --days --since --until --interactive --no-interactive --visualize --export"
    local browse_flags="--limit"
    local visualize_flags=""
    local scan_flags="--glob --show"
    local fix_flags="--in-place"
    local tui_flags="--glob --fzf"
    local graph_flags="--interactive --no-interactive --surrealdb-url"
    local graph_classic_flags="--format --out"
    local sync_surrealdb_flags="--force --dry-run --operator --surrealdb-url"

    # Determine which command is being used
    local command=""
    local i
    for ((i = 1; i < ${#words[@]}; i++)); do
        word="${words[i]}"
        # Skip words that start with -- (they're flags, not commands)
        if [[ ! "$word" =~ ^- ]]; then
            # Check if this word is one of our commands
            if [[ "$all_commands" =~ (^|[[:space:]])$word([[:space:]]|$) ]]; then
                command="$word"
                break
            fi
        fi
    done

    # Handle completion based on context

    # If no command yet, or we're completing the command itself
    if [[ -z "$command" && ! "$cur" =~ ^- ]]; then
        if [[ -n "${BASH_VERSION:-}" ]]; then
            COMPREPLY=($(compgen -W "$all_commands" -- "$cur"))
        else
            # Zsh completion
            _values 'command' \
                'search:Search Claude sessions with content preview' \
                'browse:Interactive vim-style conversation browser' \
                'visualize:Explore conversation DAG interactively' \
                'scan:Scan for JSONL issues' \
                'fix:Repair missing tool_result in JSONL' \
                'tui:Interactive TUI for JSONL browsing' \
                'graph:Visualize conversation as semantic DAG tree' \
                'graph-classic:Generate conversation graph (mermaid/dot format)' \
                'sync:surrealdb:Sync JSONL session to SurrealDB immutable event store'
        fi
        return 0
    fi

    # If starting with --, show appropriate flags for the command
    if [[ "$cur" =~ ^- ]]; then
        local flags="$global_flags"
        case "$command" in
            search)
                flags="$flags $search_flags"
                ;;
            browse)
                flags="$flags $browse_flags"
                ;;
            visualize)
                flags="$flags $visualize_flags"
                ;;
            scan)
                flags="$flags $scan_flags"
                ;;
            fix)
                flags="$flags $fix_flags"
                ;;
            tui)
                flags="$flags $tui_flags"
                ;;
            graph)
                flags="$flags $graph_flags"
                ;;
            graph-classic)
                flags="$flags $graph_classic_flags"
                ;;
            sync:surrealdb)
                flags="$flags $sync_surrealdb_flags"
                ;;
        esac

        if [[ -n "${BASH_VERSION:-}" ]]; then
            COMPREPLY=($(compgen -W "$flags" -- "$cur"))
        else
            # Zsh completion for flags
            _values 'flags' ${flags[@]}
        fi
        return 0
    fi

    # Handle file path completion for commands that accept file arguments
    case "$command" in
        scan)
            # scan [target] [flags]
            # Target is a directory path - use file completion
            if [[ "$prev" != "--glob" ]] && [[ "$prev" != "--show" ]]; then
                if [[ -n "${BASH_VERSION:-}" ]]; then
                    COMPREPLY=($(compgen -f -d -- "$cur"))
                else
                    _files -/
                fi
            fi
            ;;
        fix)
            # fix [path] [flags]
            # Path should be a .jsonl file
            if [[ "$prev" != "--in-place" ]]; then
                if [[ -n "${BASH_VERSION:-}" ]]; then
                    # Complete only .jsonl files
                    COMPREPLY=($(compgen -f -- "$cur"))
                    # Filter to only .jsonl files
                    COMPREPLY=($(printf '%s\n' "${COMPREPLY[@]}" | grep -E '\.jsonl$'))
                else
                    _files -g '*.jsonl'
                fi
            fi
            ;;
        visualize)
            # visualize [input] [flags]
            # Input should be a .jsonl file
            if [[ -n "${BASH_VERSION:-}" ]]; then
                # Complete only .jsonl files
                COMPREPLY=($(compgen -f -- "$cur"))
                # Filter to only .jsonl files
                COMPREPLY=($(printf '%s\n' "${COMPREPLY[@]}" | grep -E '\.jsonl$'))
            else
                _files -g '*.jsonl'
            fi
            ;;
        tui)
            # tui [target] [flags]
            # Target is a directory path
            if [[ "$prev" != "--glob" ]] && [[ "$prev" != "--fzf" ]]; then
                if [[ -n "${BASH_VERSION:-}" ]]; then
                    COMPREPLY=($(compgen -f -d -- "$cur"))
                else
                    _files -/
                fi
            fi
            ;;
        graph)
            # graph [session_id] [flags]
            # session_id is UUID or file path - not much we can do for UUID
            # but we can try file completion
            if [[ "$prev" != "--surrealdb-url" ]] && [[ "$prev" != "--interactive" ]] && [[ "$prev" != "--no-interactive" ]]; then
                if [[ -n "${BASH_VERSION:-}" ]]; then
                    COMPREPLY=($(compgen -f -- "$cur"))
                else
                    _files
                fi
            fi
            ;;
        graph-classic)
            # graph-classic [path] [flags]
            # path is a .jsonl file
            if [[ "$prev" != "--format" ]] && [[ "$prev" != "--out" ]]; then
                if [[ -n "${BASH_VERSION:-}" ]]; then
                    # Complete only .jsonl files
                    COMPREPLY=($(compgen -f -- "$cur"))
                    # Filter to only .jsonl files
                    COMPREPLY=($(printf '%s\n' "${COMPREPLY[@]}" | grep -E '\.jsonl$'))
                else
                    _files -g '*.jsonl'
                fi
            fi
            ;;
        sync:surrealdb)
            # sync:surrealdb [session_id] [flags]
            # session_id is UUID or file path
            if [[ "$prev" != "--surrealdb-url" ]] && [[ "$prev" != "--operator" ]]; then
                if [[ -n "${BASH_VERSION:-}" ]]; then
                    COMPREPLY=($(compgen -f -- "$cur"))
                else
                    _files
                fi
            fi
            ;;
    esac

    # Handle flag values
    case "$prev" in
        --format)
            local formats="dot mermaid"
            if [[ -n "${BASH_VERSION:-}" ]]; then
                COMPREPLY=($(compgen -W "$formats" -- "$cur"))
            else
                _values 'format' dot mermaid
            fi
            return 0
            ;;
        --qdrant-url | --surrealdb-url)
            # These take URL values - can't really auto-complete, but hint at defaults
            if [[ -n "${BASH_VERSION:-}" ]]; then
                COMPREPLY=()
            fi
            return 0
            ;;
    esac
}

# Register the completion function for bash
if [[ -n "${BASH_VERSION:-}" ]]; then
    complete -o bashdefault -o default -o filenames -F _riff_completion riff
fi

# Register the completion function for zsh
if [[ -n "${ZSH_VERSION:-}" ]]; then
    compdef _riff_completion riff
fi
