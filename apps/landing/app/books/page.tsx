import { headers } from 'next/headers';
import { redirect } from 'next/navigation';

export const metadata = {
  title: 'Anicca Books',
  description: 'Anicca Books — Buddhist short reads. Routed by locale.',
};

export default function BooksRedirect() {
  const accept = headers().get('accept-language') ?? '';
  const isJp = /^|[,;]\s*ja(\b|-)/i.test(accept) || accept.toLowerCase().startsWith('ja');
  redirect(isJp ? '/achan' : '/monk');
}
