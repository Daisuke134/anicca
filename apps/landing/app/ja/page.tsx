import Navbar from '@/components/site/Navbar';
import Hero from '@/components/site/Hero';
import EmpireDashboard from '@/components/site/EmpireDashboard';
import TheEmpireProducts from '@/components/site/TheEmpireProducts';
import BigGive from '@/components/site/BigGive';
import TheSpend from '@/components/site/TheSpend';
import ManifestoStrip from '@/components/site/ManifestoStrip';
import OtherPillars from '@/components/site/OtherPillars';
import Vision from '@/components/site/Vision';
import Philosophy from '@/components/site/Philosophy';
import Roadmap from '@/components/site/Roadmap';
import Footer from '@/components/site/Footer';

export default function Page() {
  const locale = 'ja';

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
      <Vision locale={locale} />
      <Philosophy locale={locale} />
      <Roadmap locale={locale} />
      <Footer locale={locale} />
    </>
  );
}
