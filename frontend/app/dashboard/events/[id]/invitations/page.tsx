import InvitationsPageClient from "./InvitationsPageClient";

export function generateStaticParams() {
  return [{ id: "default" }];
}

export default function InvitationsPage() {
  return <InvitationsPageClient />;
}
