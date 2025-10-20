#!/usr/bin/env python3

import sys
import json
import re
import textwrap
from argparse import ArgumentParser
from rapidfuzz import fuzz
from rich.console import Console
from rich.syntax import Syntax
from rich.traceback import install
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout import Layout
from prompt_toolkit.formatted_text import HTML

install()
console = Console()

def find_match_snippet(text, query, snippet_length=200):
    """Find meaningful content around the search term, not just JSON structure."""
    query_lower = query.lower()
    text_lower = text.lower()
    
    # Find all occurrences of the query and query words
    search_terms = [query_lower] + query_lower.split()
    all_matches = []
    
    for term in search_terms:
        start = 0
        while True:
            pos = text_lower.find(term, start)
            if pos == -1:
                break
            all_matches.append((pos, len(term), term))
            start = pos + 1
    
    if not all_matches:
        # Fallback to beginning
        return {
            'snippet': text[:snippet_length] + "..." if len(text) > snippet_length else text,
            'position': 0,
            'start': 0,
            'end': min(snippet_length, len(text))
        }
    
    # Sort by position and take the first significant match
    all_matches.sort()
    match_pos, match_len, matched_term = all_matches[0]
    
    # Find meaningful context boundaries
    lines = text.split('\n')
    
    # Find which line contains our match
    current_pos = 0
    match_line_idx = 0
    match_line_start = 0
    
    for i, line in enumerate(lines):
        line_start = current_pos
        line_end = current_pos + len(line)
        
        if line_start <= match_pos <= line_end:
            match_line_idx = i
            match_line_start = line_start
            break
        current_pos = line_end + 1  # +1 for newline
    
    # Extract context around the matching line
    context_lines = []
    start_line = max(0, match_line_idx - 2)
    end_line = min(len(lines), match_line_idx + 3)
    
    # Try to include complete key-value pairs or meaningful JSON chunks
    for i in range(start_line, end_line):
        line = lines[i].strip()
        if line and not line in ['{', '}', '[', ']']:  # Skip empty structural lines
            context_lines.append(lines[i])
    
    # If we don't have enough meaningful content, expand the search
    if len(context_lines) < 3:
        context_lines = []
        start_line = max(0, match_line_idx - 5)
        end_line = min(len(lines), match_line_idx + 6)
        
        for i in range(start_line, end_line):
            line = lines[i].strip()
            if line:  # Include any non-empty line
                context_lines.append(lines[i])
    
    snippet_text = '\n'.join(context_lines)
    
    # Highlight the matched terms in the snippet
    highlighted_snippet = snippet_text
    for term in set([m[2] for m in all_matches]):  # Remove duplicates
        if len(term) > 2:  # Only highlight meaningful terms
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            highlighted_snippet = pattern.sub(f"**{term.upper()}**", highlighted_snippet)
    
    # Ensure we don't exceed length limit
    if len(highlighted_snippet) > snippet_length * 1.5:  # Allow some buffer for highlighting
        # Truncate but try to keep the highlighted term visible
        term_pos = highlighted_snippet.lower().find(f"**{matched_term.upper()}**".lower())
        if term_pos != -1:
            # Center around the highlighted term
            start_pos = max(0, term_pos - snippet_length // 2)
            end_pos = min(len(highlighted_snippet), start_pos + snippet_length)
            highlighted_snippet = highlighted_snippet[start_pos:end_pos]
            if start_pos > 0:
                highlighted_snippet = "..." + highlighted_snippet
            if end_pos < len(snippet_text):
                highlighted_snippet = highlighted_snippet + "..."
        else:
            # Fallback truncation
            highlighted_snippet = highlighted_snippet[:snippet_length] + "..."
    
    return {
        'snippet': highlighted_snippet,
        'position': match_pos,
        'start': match_line_start,
        'end': match_line_start + len('\n'.join(context_lines))
    }

def fuzzy_search(filepath, query, threshold=70):
    matches = []
    try:
        with open(filepath, 'r') as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    text = json.dumps(obj, ensure_ascii=False, indent=2)
                    score = fuzz.partial_ratio(query.lower(), text.lower())
                    if score >= threshold:
                        snippet_info = find_match_snippet(text, query)
                        matches.append({
                            'line_number': idx + 1,
                            'object': obj,
                            'score': score,
                            'snippet': snippet_info['snippet'],
                            'full_text': text
                        })
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        console.print_exception()
    
    # Sort by score (highest first)
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches

def pretty_print(obj):
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    syntax = Syntax(text, "json", theme="monokai", line_numbers=False)
    console.print(syntax)

def wrap_text(text, width):
    """Wrap text to specified width, preserving highlighted terms and spaces."""
    lines = text.split('\n')
    wrapped_lines = []
    
    for line in lines:
        if len(line) <= width:
            wrapped_lines.append(line)
        else:
            # Handle highlighting by temporarily replacing markers
            placeholder_map = {}
            temp_line = line
            marker_count = 0
            
            # Replace **text** with temporary placeholders
            while '**' in temp_line:
                start = temp_line.find('**')
                if start == -1:
                    break
                end = temp_line.find('**', start + 2)
                if end == -1:
                    break
                
                original_text = temp_line[start:end+2]
                placeholder = f"__HIGHLIGHT_{marker_count}__"
                placeholder_map[placeholder] = original_text
                temp_line = temp_line[:start] + placeholder + temp_line[end+2:]
                marker_count += 1
            
            # Use textwrap to wrap the line with placeholders
            wrapped = textwrap.fill(temp_line, width=width, 
                                  break_long_words=True, 
                                  break_on_hyphens=False)
            
            # Restore the highlighting markers
            for placeholder, original in placeholder_map.items():
                wrapped = wrapped.replace(placeholder, original)
            
            wrapped_lines.extend(wrapped.split('\n'))
    
    return wrapped_lines

def show_snippet_browser(matches, query):
    """Interactive snippet browser using prompt_toolkit."""
    if not matches:
        console.print("[yellow]No matches found.[/yellow]")
        return
    
    current_index = 0
    snippet_scroll_offset = 0
    max_display_lines = 15
    max_line_length = 80
    
    def get_display_text():
        match = matches[current_index]
        header = f"Match {current_index + 1}/{len(matches)} (Score: {match['score']}) - Line {match['line_number']}"
        snippet = match['snippet']
        
        # First, wrap the raw snippet to our line length
        wrapped_snippet_lines = wrap_text(snippet, max_line_length)
        
        # Apply scrolling to the wrapped lines
        total_lines = len(wrapped_snippet_lines)
        start_line = snippet_scroll_offset
        end_line = min(start_line + max_display_lines, total_lines)
        display_lines = wrapped_snippet_lines[start_line:end_line]
        
        # Create display snippet
        display_snippet = '\n'.join(display_lines)
        
        # Add scroll indicators
        scroll_info = ""
        if total_lines > max_display_lines:
            scroll_info = f" | Showing lines {start_line + 1}-{end_line} of {total_lines}"
            if start_line > 0:
                scroll_info += " | [↑] more above"
            if end_line < total_lines:
                scroll_info += " | [↓] more below"
        
        # Create controls help
        controls = "[n]ext, [p]revious, [v]iew full, [↑/↓] scroll"
        if total_lines > max_display_lines:
            controls += ", [u]p, [d]own"
        controls += ", [q]uit"
        
        return f"{header}{scroll_info}\n{'='*max_line_length}\n{display_snippet}\n{'='*max_line_length}\n{controls}"
    
    bindings = KeyBindings()
    
    @bindings.add('n')
    def next_match(event):
        nonlocal current_index, snippet_scroll_offset
        current_index = (current_index + 1) % len(matches)
        snippet_scroll_offset = 0  # Reset scroll when changing matches
        event.app.invalidate()
    
    @bindings.add('p')
    def prev_match(event):
        nonlocal current_index, snippet_scroll_offset
        current_index = (current_index - 1) % len(matches)
        snippet_scroll_offset = 0  # Reset scroll when changing matches
        event.app.invalidate()
    
    @bindings.add('up')
    @bindings.add('u')
    def scroll_up(event):
        nonlocal snippet_scroll_offset
        snippet_scroll_offset = max(0, snippet_scroll_offset - 3)
        event.app.invalidate()
    
    @bindings.add('down')
    @bindings.add('d')
    def scroll_down(event):
        nonlocal snippet_scroll_offset
        match = matches[current_index]
        wrapped_lines = wrap_text(match['snippet'], max_line_length)
        max_scroll = max(0, len(wrapped_lines) - max_display_lines)
        snippet_scroll_offset = min(max_scroll, snippet_scroll_offset + 3)
        event.app.invalidate()
    
    @bindings.add('v')
    def view_full(event):
        event.app.exit(result='view')
    
    @bindings.add('q')
    def quit_browser(event):
        event.app.exit(result='quit')
    
    @bindings.add('c-c')
    def quit_browser_ctrl_c(event):
        event.app.exit(result='quit')
    
    text_control = FormattedTextControl(
        text=lambda: get_display_text(),
        key_bindings=bindings
    )
    
    layout = Layout(Window(content=text_control))
    app = Application(layout=layout, key_bindings=bindings, full_screen=False)
    
    while True:
        result = app.run()
        
        if result == 'view':
            console.print(f"\n[bold green]Full JSON for Line {matches[current_index]['line_number']}:[/bold green]")
            pretty_print(matches[current_index]['object'])
            console.print("\n[dim]Press Enter to continue browsing...[/dim]")
            input()
            app = Application(layout=layout, key_bindings=bindings, full_screen=False)
        else:
            break

def main():
    parser = ArgumentParser(description="Fuzzy search and drill-down JSONL viewer with snippet browser.")
    parser.add_argument("file", help="Path to JSONL file")
    parser.add_argument("--query", "-q", help="Search query", required=True)
    parser.add_argument("--threshold", "-t", type=int, default=70, help="Fuzzy match threshold (0-100)")
    args = parser.parse_args()

    matches = fuzzy_search(args.file, args.query, args.threshold)
    
    if not matches:
        console.print("[yellow]No matches found.[/yellow]")
        return
    
    console.print(f"[green]Found {len(matches)} matches for '{args.query}'[/green]")
    show_snippet_browser(matches, args.query)

if __name__ == "__main__":
    main()
