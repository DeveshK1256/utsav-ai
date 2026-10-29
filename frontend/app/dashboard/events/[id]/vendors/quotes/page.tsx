import ScopedQuotesDashboardClient from "./ScopedQuotesDashboardClient";

export function generateStaticParams() {
  return [{ id: "default" }];
}

export default function ScopedQuotesPage() {
  return <ScopedQuotesDashboardClient />;
}
