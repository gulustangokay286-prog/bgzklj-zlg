import os

file_path = "/Users/fookay/ders program/main_window.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_kontrol2 = """        # ── 2. KONTROL: Öğretmen Kapalı/Kısıtlı Saat Kontrolü
        kisitlamalar = self.data_store.get("kisitlamalar", {})
        if teacher and teacher in kisitlamalar:
            for ext in range(duration):
                check_p = period_idx + ext
                cell_key = f"{day_idx},{check_p}"
                is_available = kisitlamalar[teacher].get(cell_key, True)
                if not is_available:
                    QMessageBox.warning(
                        self, "Kısıtlama Engeli",
                        f"⚠️ '{teacher}' öğretmeninin {day_name} günü {check_p+1}. ders saatinde 'ÇALIŞAMAZ / KAPALI' kısıtlaması bulunmaktadır!\\nDers yerleştirilemez."
                    )
                    self.statusBar().showMessage(f"Kısıtlama engeli: {teacher} - {day_name} {check_p+1}. saat kapalı!")
                    return"""

new_kontrol2 = """        # ── 2. KONTROL: Öğretmen Kapalı/Kısıtlı Saat Kontrolü
        kisitlamalar = self.data_store.get("kisitlamalar", {})
        
        # Sınıf Timeoff Kontrolü
        target_check_classes = combined_classes if (is_comb and combined_classes) else [cls_name] if cls_name else []
        for chk_c in target_check_classes:
            c_info = next((c for c in self.data_store.get("siniflar", []) if c.get("ad", "").strip() == chk_c.strip()), {})
            c_timeoff = c_info.get("timeoff", [])
            if c_timeoff:
                for ext in range(duration):
                    check_p = period_idx + ext
                    if day_idx < len(c_timeoff) and check_p < len(c_timeoff[day_idx]):
                        if c_timeoff[day_idx][check_p] == 0:
                            QMessageBox.warning(
                                self, "Sınıf Kısıtlama Engeli",
                                f"⚠️ '{chk_c}' sınıfının {day_name} günü {check_p+1}. ders saati 'KAPALI' olarak kısıtlanmıştır!\\nDers yerleştirilemez."
                            )
                            self.statusBar().showMessage(f"Sınıf Kısıtlama engeli: {chk_c} - {day_name} {check_p+1}. saat kapalı!")
                            return

        # Öğretmen Timeoff Kontrolü (Global Kisitlamalar ve Yerel Timeoff)
        if teacher:
            t_info = next((t for t in self.data_store.get("ogretmenler", []) if format_tr_name(t.get("ad", "")) == teacher), {})
            t_timeoff = t_info.get("timeoff", [])
            
            for ext in range(duration):
                check_p = period_idx + ext
                cell_key = f"{day_idx},{check_p}"
                
                # Global çapraz kısıtlama
                is_available = kisitlamalar.get(teacher, {}).get(cell_key, True)
                if not is_available:
                    QMessageBox.warning(
                        self, "Kısıtlama Engeli",
                        f"⚠️ '{teacher}' öğretmeninin {day_name} günü {check_p+1}. ders saatinde 'ÇALIŞAMAZ / KAPALI' kısıtlaması bulunmaktadır!\\nDers yerleştirilemez."
                    )
                    self.statusBar().showMessage(f"Kısıtlama engeli: {teacher} - {day_name} {check_p+1}. saat kapalı!")
                    return
                    
                # Yerel timeoff (Grid üzerinden ayarlanan)
                if t_timeoff and day_idx < len(t_timeoff) and check_p < len(t_timeoff[day_idx]):
                    if t_timeoff[day_idx][check_p] == 0:
                        QMessageBox.warning(
                            self, "Öğretmen Kısıtlama Engeli",
                            f"⚠️ '{teacher}' öğretmeninin {day_name} günü {check_p+1}. ders saati 'KAPALI' olarak kısıtlanmıştır!\\nDers yerleştirilemez."
                        )
                        self.statusBar().showMessage(f"Öğretmen Kısıtlama engeli: {teacher} - {day_name} {check_p+1}. saat kapalı!")
                        return"""

content = content.replace(old_kontrol2, new_kontrol2)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Patched timeoff checks in main_window.py")
