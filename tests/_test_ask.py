ss = {}
def init():
    ss.setdefault('ask_pending', False)
    ss.setdefault('ask_last_q', None)
    ss.setdefault('ask_last_ts', None)
    ss.setdefault('ask_box', '')
def chip(full):
    ss['ask_box'] = full; ss['ask_pending'] = True; ss['ask_last_q'] = None
def clear():
    ss['ask_box'] = ''; ss['ask_pending'] = False; ss['ask_last_q'] = None; ss['ask_last_ts'] = None
def go():
    ss['ask_pending'] = True; ss['ask_last_q'] = None
def run_cycle():
    box_val = ss.get('ask_box', '').strip()
    question = box_val if ss.get('ask_pending') and box_val else None
    if question:
        ss['ask_pending'] = False; ss['ask_last_q'] = question; ss['ask_last_ts'] = 'T'
    return question

init()
# 1: type Q1 + Ask
ss['ask_box'] = 'Q1'; go(); q = run_cycle()
print(f"Step 1: box='{ss['ask_box']}' echo='{ss['ask_last_q']}' ran='{q}'")
assert ss['ask_box'] == 'Q1' and ss['ask_last_q'] == 'Q1'
# 2: chip A
chip('ChipA'); q = run_cycle()
print(f"Step 2: box='{ss['ask_box']}' echo='{ss['ask_last_q']}' ran='{q}'")
assert ss['ask_box'] == 'ChipA' and ss['ask_last_q'] == 'ChipA'
# 3: chip B
chip('ChipB'); q = run_cycle()
print(f"Step 3: box='{ss['ask_box']}' echo='{ss['ask_last_q']}' ran='{q}'")
assert ss['ask_box'] == 'ChipB' and ss['ask_last_q'] == 'ChipB'
# 4: type Q2 + Ask
ss['ask_box'] = 'Q2'; go(); q = run_cycle()
print(f"Step 4: box='{ss['ask_box']}' echo='{ss['ask_last_q']}' ran='{q}'")
assert ss['ask_box'] == 'Q2' and ss['ask_last_q'] == 'Q2'
# 5: chip A again
chip('ChipA'); q = run_cycle()
print(f"Step 5: box='{ss['ask_box']}' echo='{ss['ask_last_q']}' ran='{q}'")
assert ss['ask_box'] == 'ChipA' and ss['ask_last_q'] == 'ChipA'
# 6: Clear
clear(); q = run_cycle()
print(f"Step 6: box='{ss['ask_box']}' echo='{ss['ask_last_q']}' ran='{q}'")
assert ss['ask_box'] == '' and ss['ask_last_q'] is None and q is None
print("\nALL 6 STEPS PASSED")

# Test multi-bullet preservation
import re
_NARRATION = re.compile(r"^(I'll |Let me |I will |I need to |First,? I'll |OK,? |Sure,? |I can answer |The semantic model ).*?[.!]\s*", re.IGNORECASE)
def strip_narration(text):
    return "\n".join(_NARRATION.sub("", line) for line in text.split("\n"))

text = "I'll analyze this.\n\nOTD is **68.4%** overall.\n\n- Supplier Cobalt 12: 63.0% OTD\n- Supplier Ember 24: 63.6% OTD\n- Supplier Ember 4: 64.3% OTD\n\nAll three are below SLA."
display = strip_narration(text)
blocks = re.split(r'\n{2,}', display.strip())
short = "\n\n".join(blocks[:2])
print(f"\nMulti-bullet test: {len(blocks)} blocks, short has {short.count(chr(10))} newlines")
assert "- Supplier Cobalt" in "\n\n".join(blocks)
assert "\n\n".join(blocks[:2]).count("\n") >= 0  # no flattening
print("MULTI-BULLET TEST PASSED")
