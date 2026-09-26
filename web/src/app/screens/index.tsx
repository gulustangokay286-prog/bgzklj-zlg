// Açık pencereleri (store.screens) alttan üste çizer.
import type { ReactNode } from 'react';
import { closeScreen, useApp } from '../store.ts';
import type { Screen } from '../store.ts';
import { Window } from '../ui.tsx';
import { AssignClassScreen, AssignSubjectScreen, AssignTeacherScreen } from './Assign.tsx';
import { AdvisorScreen, PrecheckScreen, StatisticsScreen, VerifyScreen } from './Checks.tsx';
import { ConstraintsScreen, ElectivesScreen, GroupsScreen } from './Definitions.tsx';
import { ExportScreen } from './Export.tsx';
import { FaqScreen, TipsScreen } from './Help.tsx';
import { HomeScreen, NewScheduleScreen } from './Home.tsx';
import { AssignmentListScreen, CompareScreen, RoomsScreen } from './Lists.tsx';
import { MasterDataScreen } from './MasterData.tsx';
import { PrintScreen } from './Print.tsx';
import { RelationsScreen } from './Relations.tsx';
import { SchoolScreen } from './School.tsx';
import { TimeoffScreen } from './Timeoff.tsx';

function render(s: Screen): ReactNode {
  switch (s.kind) {
    case 'master': return <MasterDataScreen tab={s.tab} />;
    case 'assignTeacher': return <AssignTeacherScreen teacher={s.teacher} />;
    case 'assignClass': return <AssignClassScreen className={s.className} />;
    case 'assignSubject': return <AssignSubjectScreen subject={s.subject} className={s.className} />;
    case 'relations': return <RelationsScreen />;
    case 'electives': return <ElectivesScreen />;
    case 'constraints': return <ConstraintsScreen target={s.target} name={s.name} />;
    case 'groups': return <GroupsScreen />;
    case 'school': return <SchoolScreen />;
    case 'precheck': return <PrecheckScreen />;
    case 'verify': return <VerifyScreen />;
    case 'statistics': return <StatisticsScreen />;
    case 'advisor': return <AdvisorScreen />;
    case 'assignmentList': return <AssignmentListScreen />;
    case 'compare': return <CompareScreen />;
    case 'rooms': return <RoomsScreen />;
    case 'info': return <SchoolScreen />;
    case 'print': return <PrintScreen preset={s.preset} />;
    case 'export': return <ExportScreen mail={s.mail} />;
    case 'faq': return <FaqScreen />;
    case 'tips': return <TipsScreen />;
    case 'home': case 'versions': return <HomeScreen />;
    case 'newSchedule': return <NewScheduleScreen inst={s.inst} />;
    case 'wizard': return <NewScheduleScreen />;
    case 'settings': return <SchoolScreen />;
    case 'timeoff': return <TimeoffScreen entityKind={s.entityKind} name={s.name} index={s.index} />;
    default:
      return (
        <Window title="Hazırlanıyor" onClose={closeScreen} width={420}>
          <p className="muted">Bu ekran ({s.kind}) web sürümüne taşınıyor.</p>
        </Window>
      );
  }
}

/** Veri olmadan da açılabilen pencereler. */
const NO_DATA = new Set(['home', 'newSchedule', 'wizard', 'faq', 'tips']);

export function ScreenHost() {
  const screens = useApp((s) => s.screens);
  const hasData = useApp((s) => !!s.data);
  return <>{screens.filter((s) => hasData || NO_DATA.has(s.kind)).map((s) => <div key={s.key} className="screen-layer">{render(s)}</div>)}</>;
}
