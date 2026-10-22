import VibeToPlanClient from './VibeToPlanClient';

export function generateStaticParams() {
  return [
    { id: 'default' }
  ];
}

export default function VibeToPlanPage() {
  return <VibeToPlanClient />;
}
