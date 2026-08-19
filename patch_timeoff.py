import os

file_path = "/Users/fookay/ders program/dialogs/timeoff_dialog.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Modify __init__
old_init = """        self.entity_type = entity_type
        self.data_store = data_store if data_store is not None else {}
        
        name = self.entity_dict.get("ad", "İsimsiz")"""

new_init = """        self.entity_type = entity_type
        self.data_store = data_store if data_store is not None else {}
        
        name = self.entity_dict.get("ad", "İsimsiz")
        
        # Load cross-institution locks
        self.cross_institution_locks = set()
        try:
            from version_store import load_global_kisitlamalar
            global_k = load_global_kisitlamalar()
            inst_slug = self.data_store.get("settings", {}).get("institution_slug", "varsayilan_kurum")
            for slug, k_data in global_k.items():
                if slug != inst_slug and isinstance(k_data, dict):
                    other_toff = k_data.get(name)
                    if other_toff and isinstance(other_toff, dict):
                        for k, v in other_toff.items():
                            if not v: # locked
                                try:
                                    parts = k.split(",")
                                    if len(parts) == 2:
                                        self.cross_institution_locks.add((int(parts[0]), int(parts[1])))
                                except: pass
        except Exception as e:
            print("Cross-institution lock load error:", e)
"""

content = content.replace(old_init, new_init)

# 2. Modify _update_item_visuals
old_visuals = """    def _update_item_visuals(self, item, state):
        item.setTextAlignment(Qt.AlignCenter)
        font = QFont("Segoe UI", 11, QFont.Bold)
        item.setFont(font)
        if state == 2:
            item.setText("✔")
            item.setForeground(QBrush(QColor("#15803D"))) # Koyu Yeşil
            item.setBackground(QBrush(QColor("#DCFCE7"))) # Açık Yeşil
        elif state == 0:
            item.setText("✖")
            item.setForeground(QBrush(QColor("#B91C1C"))) # Koyu Kırmızı
            item.setBackground(QBrush(QColor("#FEE2E2"))) # Açık Kırmızı
        elif state == 1:
            item.setText("?")
            item.setForeground(QBrush(QColor("#A16207"))) # Koyu Sarı
            item.setBackground(QBrush(QColor("#FEF9C3"))) # Açık Sarı"""

new_visuals = """    def _update_item_visuals(self, item, state, d_idx, p_idx):
        item.setTextAlignment(Qt.AlignCenter)
        font = QFont("Segoe UI", 11, QFont.Bold)
        item.setFont(font)
        
        is_cross_locked = (d_idx, p_idx) in getattr(self, "cross_institution_locks", set())
        if is_cross_locked:
            item.setToolTip("⚠️ Dikkat: Bu öğretmen bu saatte BAŞKA BİR KURUMDA (şubede) derse girmektedir veya kısıtlanmıştır!")
        else:
            item.setToolTip("")

        base_text = ""
        fg_color = ""
        bg_color = ""

        if state == 2:
            base_text = "✔"
            fg_color = "#15803D"
            bg_color = "#DCFCE7"
        elif state == 0:
            base_text = "✖"
            fg_color = "#B91C1C"
            bg_color = "#FEE2E2"
        elif state == 1:
            base_text = "?"
            fg_color = "#A16207"
            bg_color = "#FEF9C3"
            
        if is_cross_locked:
            base_text += " 🔒"
            if state != 0:
                # If they leave it open locally but it's locked elsewhere, warn them heavily
                bg_color = "#FFEDD5" # Orange
                fg_color = "#C2410C"
                
        item.setText(base_text)
        item.setForeground(QBrush(QColor(fg_color)))
        item.setBackground(QBrush(QColor(bg_color)))"""

content = content.replace(old_visuals, new_visuals)

# Fix callers of _update_item_visuals
content = content.replace("self._update_item_visuals(item, st)", "self._update_item_visuals(item, st, d_idx, p_idx)")
content = content.replace("self._update_item_visuals(item, new_state)", "self._update_item_visuals(item, new_state, col, row)")
content = content.replace("self._update_item_visuals(item, new_st)", "self._update_item_visuals(item, new_st, col if 'col' in locals() else d, p if 'p' in locals() else row)")
content = content.replace("self._update_item_visuals(item, 2)", "self._update_item_visuals(item, 2, d, p)")
content = content.replace("self._update_item_visuals(item, 0)", "self._update_item_visuals(item, 0, d, p)")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("timeoff_dialog patched.")
