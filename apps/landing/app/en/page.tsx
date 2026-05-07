import Navbar from '@/components/site/Navbar';
import Hero from '@/components/site/Hero';
import Manifesto from '@/components/site/Manifesto';
import LiveNumbers from '@/components/site/LiveNumbers';
import Pillars from '@/components/site/Pillars';
import RecentWriting from '@/components/site/RecentWriting';
import Footer from '@/components/site/Footer';

export default function Page() {
  const locale = 'en';

  return (
    <>
      <Navbar locale={locale} />
      <main>
        <Hero locale={locale} />
        <Manifesto locale={locale} />
        <LiveNumbers locale={locale} />
        <Pillars locale={locale} />
        <RecentWriting locale={locale} />
      </main>
      <Footer locale={locale} />
    </>
  );
}
