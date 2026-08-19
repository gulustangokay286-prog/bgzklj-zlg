import os

file_path = "/Users/fookay/ders program/dialogs/timeoff_dialog.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("self._update_item_visuals(item, state)", "self._update_item_visuals(item, state, d_idx, p_idx)")
content = content.replace("self._update_item_visuals(item, new_st, col if 'col' in locals() else d, p if 'p' in locals() else row)", "self._update_item_visuals(item, new_st, col, p)")
# But line 262 has 'd' and 'row'
content = content.replace("self._update_item_visuals(item, new_st, col, p)", "self._update_item_visuals(item, new_st, col, p)", 1) # first replace is line 252. Wait, the exact string is in both! I can't do this easily with string replace. Let's use re.sub.
