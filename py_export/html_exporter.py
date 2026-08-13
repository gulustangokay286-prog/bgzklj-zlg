import os

def export_to_html(classes, teachers, data_store, placed_lessons, save_path):
    # CSS ve HTML İskeleti
    html_content = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ders Programı - Web Görünümü</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; padding: 20px; color: #333; }
        h1 { text-align: center; color: #2c3e50; }
        .timetable { width: 100%; border-collapse: collapse; margin-bottom: 40px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); background-color: white; }
        .timetable th, .timetable td { border: 1px solid #ddd; padding: 12px; text-align: center; }
        .timetable th { background-color: #34495e; color: white; font-weight: bold; }
        .timetable td.lesson { background-color: #e8f4f8; font-weight: bold; color: #2980b9; }
        .timetable td.empty { background-color: #fafafa; color: #ccc; }
        .section-title { font-size: 24px; color: #e67e22; border-bottom: 2px solid #e67e22; padding-bottom: 5px; margin-bottom: 15px; }
        .school-name { text-align: center; font-size: 14px; color: #7f8c8d; margin-bottom: 30px; }
    </style>
</head>
<body>
    <h1>Haftalık Ders Programı</h1>
    <div class="school-name">Özel Çorum Birey Özel Öğretim Kursu</div>
"""

    days = data_store.get("settings", {}).get("days", ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
    periods = int(data_store.get("settings", {}).get("periods", 8))

    # Sınıflar İçin Tablolar
    for c in classes:
        class_name = c.get("ad", "Bilinmeyen Sınıf")
        html_content += f'<div class="section-title">Sınıf: {class_name}</div>\n'
        html_content += '<table class="timetable">\n'
        
        # Header (Günler)
        html_content += '  <tr><th>Saat \\ Gün</th>'
        for day in days:
            html_content += f'<th>{day}</th>'
        html_content += '</tr>\n'
        
        # Rows (Saatler)
        for p in range(periods):
            html_content += f'  <tr><th>{p+1}. Ders</th>'
            for d_idx, day in enumerate(days):
                # Bu sınıfa bu gün/saatte atanmış ders var mı?
                col_idx = d_idx
                lesson_info = placed_lessons.get((p, col_idx))
                
                if lesson_info and lesson_info.get("class_name") == class_name:
                    subj = lesson_info.get("subject_name", "")
                    teacher = lesson_info.get("teacher_name", "")
                    html_content += f'<td class="lesson">{subj}<br><span style="font-size:12px; color:#555;">{teacher}</span></td>'
                else:
                    html_content += '<td class="empty">-</td>'
            html_content += '</tr>\n'
            
        html_content += '</table>\n'
        
    html_content += """
</body>
</html>
"""

    # Dosyayı kaydet
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(html_content)
