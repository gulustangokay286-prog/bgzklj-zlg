import sys

file2 = "/Users/fookay/ders program/main_window.py"
with open(file2, "r", encoding="utf-8") as f:
    content2 = f.read()

# Fix target_entity state loss
target_state = """        # If target_entity is None, infer from active selection in grid table or left tree
        if target_entity is None:
            if hasattr(self._grid, "table"):
                cur_r = self._grid.table.currentRow()
                if cur_r >= 0:"""
replace_state = """        # If target_entity is None, infer from active selection in grid table or left tree
        if target_entity is None:
            if hasattr(self._grid, "table"):
                cur_r = self._grid.table.currentRow()
                if cur_r < 0 and hasattr(self._grid, "_current_selected_pos") and self._grid._current_selected_pos:
                    cur_r = self._grid._current_selected_pos[0]
                
                if cur_r >= 0:"""
content2 = content2.replace(target_state, replace_state)

# Fix stable random generation
target_random = """            if deficit > 0:
                import random
                import uuid
                base_atamalar = list(scoped_atamalar)
                while deficit > 0:
                    chosen = random.choice(base_atamalar)"""

replace_random = """            if deficit > 0:
                import random
                import uuid
                rng = random.Random(target_entity)
                base_atamalar = sorted(list(scoped_atamalar), key=lambda x: str(x.get("subject", "")))
                while deficit > 0:
                    chosen = rng.choice(base_atamalar)"""
content2 = content2.replace(target_random, replace_random)

with open(file2, "w", encoding="utf-8") as f:
    f.write(content2)

print("Patch applied.")
