import json, sys
path = sys.argv[1]
fixed = []
pending_tool_uses = []

with open(path, 'r', encoding='utf-8') as f:
    lines = [json.loads(line) for line in f if line.strip()]

for msg in lines:
    # Collect tool_uses from assistant messages
    if msg.get('type') == 'assistant' or (msg.get('message', {}).get('role') == 'assistant'):
        content = (msg.get('message') or {}).get('content') or msg.get('content') or []
        for c in content:
            if isinstance(c, dict) and c.get('type') == 'tool_use' and c.get('id'):
                pending_tool_uses.append(c['id'])
        fixed.append(msg)
        continue

    # If this is the immediate user message and contains tool_results, clear matched IDs
    if msg.get('type') == 'user' or (msg.get('message', {}).get('role') == 'user'):
        content = (msg.get('message') or {}).get('content') or msg.get('content') or []
        seen_ids = set()
        for c in content:
            if isinstance(c, dict) and c.get('type') == 'tool_result' and c.get('tool_use_id'):
                seen_ids.add(c['tool_use_id'])
        # If previous assistant had tool_use(s) but this user message doesn't cover all, prepend missing tool_results
        if pending_tool_uses:
            missing = [tid for tid in pending_tool_uses if tid not in seen_ids]
            if missing:
                tr = [{"type":"tool_result","tool_use_id":tid,"content":"Tool run cancelled by user before completion.","is_error":True} for tid in missing]
                # Normalize to {message:{role,content}} shape
                if 'message' in msg:
                    msg['message']['content'] = tr + (msg['message'].get('content') or [])
                else:
                    msg['message'] = {"role":"user","content": tr + (msg.get('content') or [])}
                seen_ids.update(missing)
            pending_tool_uses = []
        fixed.append(msg)
        continue

    # Any other message types
    fixed.append(msg)

# If file ends with pending tool_uses, append a final user message with tool_results
if pending_tool_uses:
    fixed.append({
        "type":"user",
        "message":{
            "role":"user",
            "content":[{"type":"tool_result","tool_use_id":tid,"content":"Tool run cancelled by user before completion.","is_error":True} for tid in pending_tool_uses]
        }
    })

with open(path + ".repaired", 'w', encoding='utf-8') as f:
    for m in fixed:
        f.write(json.dumps(m, ensure_ascii=False) + "\n")

print("Wrote", path + ".repaired")