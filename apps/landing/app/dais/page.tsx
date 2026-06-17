import LaunchFrame from '@/components/site/LaunchFrame';
import DaisBody from './DaisBody';

// /dais — Dais's products hub (spec31 §C / spec30 §13). Uses LaunchFrame for the
// shared nav + footer + EN/JA locale toggle. Body lists all i18n.empireProducts.products
// except `alarm`.

export const dynamic = 'force-static';

export const metadata = {
  title: "Dais's products — Anicca",
  description:
    "Every revenue product Dais ships: Anicca iOS, Life Manager, the weekly web apps, the mobile factory apps, and the content channels. Each one is its own Anicca instance.",
};

export default function Page() {
  return (
    <LaunchFrame>
      <DaisBody />
    </LaunchFrame>
  );
}
