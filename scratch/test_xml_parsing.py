import re
import uuid
import json

def _parse_tool_calls_from_text(content: str) -> list:
    tool_calls = []

    # 1. Try XML parsing (<invoke name="...">...</invoke> or incomplete)
    # Search for any <invoke name="NAME"> tag
    invoke_matches = list(re.finditer(r'<invoke\s+name="([^"]+)"\s*>(.*)', content, re.DOTALL))
    for match in invoke_matches:
        name = match.group(1)
        inner = match.group(2)
        # If there is a closing </invoke>, only take content up to it
        end_invoke = inner.find('</invoke>')
        if end_invoke != -1:
            inner = inner[:end_invoke]
        
        args = {}
        # Find the starting position of all parameters to segment them
        param_starts = [m.start() for m in re.finditer(r'<parameter\s+name=', inner)]
        for i, start_pos in enumerate(param_starts):
            segment = inner[start_pos:]
            if i < len(param_starts) - 1:
                segment = inner[start_pos:param_starts[i+1]]
            
            p_match = re.match(r'<parameter\s+name="([^"]+)"[^>]*>(.*)', segment, re.DOTALL)
            if p_match:
                p_name = p_match.group(1)
                p_val = p_match.group(2).strip()
                # Strip closing parameter tag if present
                if p_val.endswith('</parameter>'):
                    p_val = p_val[:-12].strip()
                elif '</parameter>' in p_val:
                    p_val = p_val.split('</parameter>')[0].strip()
                args[p_name] = p_val
        
        if name:
            tool_calls.append({
                "name": name,
                "args": args,
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call"
            })
    return tool_calls

truncated_log = """
<function_calls>
<invoke name="route_to">
<parameter name="next_node" string="true">architect</parameter>
<parameter name="current_instruction" string="true">Analyze the codebase, index dependencies, parse POM, and run the full 7-step dependency compatibility pipeline to find compatible dependency combinations for Java 17 migration. Generate upgrade_report/solutions.</parameter>
<parameter name="summary_update" string="true">User requested to approve upgrade and proceed with migration. Starting dependency compatibility analysis.</parameter>
<parameter name="response_to_user" string="true">I'll start by analyzing your project's dependencies and finding compatible upgrades for Java 17. This will involve scanning the codebase, parsing the POM,
"""

parsed = _parse_tool_calls_from_text(truncated_log)
print(json.dumps(parsed, indent=2))
assert len(parsed) == 1
assert parsed[0]["name"] == "route_to"
assert parsed[0]["args"]["next_node"] == "architect"
assert "I'll start by analyzing" in parsed[0]["args"]["response_to_user"]
print("XML Tool Call Parsing Verification PASSED!")
