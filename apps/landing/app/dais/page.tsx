import LaunchFrame from '@/components/site/LaunchFrame';
import DaisBody from './DaisBody';

// /dais — Dais's products hub (spec31 §C2 / spec30 §13). Uses LaunchFrame for the
// shared nav + footer + EN/JA locale toggle. Body groups Dais's real products:
// Flagship (Anicca iOS + Life Manager) · Anicca Web Apps · Mobile factory apps · (ideal) UBI.

export const dynamic = 'force-static';

export const metadata = {
  title: "Dais's products — Anicca",
  description:
    "Where the money comes from: Anicca iOS, Life Manager, the weekly Anicca Web Apps, the mobile factory apps, and the ideal — an anicca paying basic income with no human in the loop.",
};

export default function Page() {
  return (
    <LaunchFrame>
      <DaisBody />
    </LaunchFrame>
  );
}
