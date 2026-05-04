import Navbar from '@/components/site/Navbar';
import Hero from '@/components/site/Hero';
import EmpireDashboard from '@/components/site/EmpireDashboard';
import TheEmpireProducts from '@/components/site/TheEmpireProducts';
import BigGive from '@/components/site/BigGive';
import TheSpend from '@/components/site/TheSpend';
import ManifestoStrip from '@/components/site/ManifestoStrip';
import OtherPillars from '@/components/site/OtherPillars';
import Footer from '@/components/site/Footer';

export default function Page() {
  const locale = 'en';

  return (
    <>
      <Navbar locale={locale} />
      <Hero locale={locale} />
      <EmpireDashboard locale={locale} />
      <TheEmpireProducts locale={locale} />
      <BigGive locale={locale} />
      <TheSpend locale={locale} />
      <ManifestoStrip locale={locale} />
      <OtherPillars locale={locale} />
      <Footer locale={locale} />
    </>
  );
}
