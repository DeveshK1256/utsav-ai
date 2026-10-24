import ComposePageClient from './ComposePageClient';

export function generateStaticParams() {
  return [
    { id: 'default' }
  ];
}

export default function ComposePage() {
  return <ComposePageClient />;
}
