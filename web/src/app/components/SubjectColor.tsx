// color_picker_dialog.ModernColorPickerDialog + update_subject_color_globally.
import { useState } from 'react';
import { subjectColor } from '../model.ts';
import { applySubjectColor } from '../screens/MasterData.tsx';
import { mutate, useApp } from '../store.ts';
import { Btn, ColorField, Window } from '../ui.tsx';

export function SubjectColorDialog({ subject, onClose }: { subject: string; onClose: () => void }) {
  const data = useApp((s) => s.data);
  const [c, setC] = useState(() => subjectColor(subject, data));
  return (
    <Window title={`${subject} — Renk Seçimi`} onClose={onClose} width={420}
      footer={<><span className="sp" /><Btn onClick={onClose}>İptal</Btn><Btn kind="primary" onClick={() => { mutate(`${subject} rengi`, (d) => applySubjectColor(d, subject, c)); onClose(); }}>Uygula</Btn></>}>
      <ColorField value={c} onChange={setC} />
      <p className="muted small">Renk bu dersin bütün kartlarına ve atamalarına uygulanır.</p>
    </Window>
  );
}
