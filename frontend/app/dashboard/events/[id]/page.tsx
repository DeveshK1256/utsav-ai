import EventDashboardClient from './EventDashboardClient';

export function generateStaticParams() {
  return [
    { id: 'default' }
  ];
}

export default function EventDashboardPage() {
  return <EventDashboardClient />;
}
