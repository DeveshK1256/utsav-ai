import GuestPageClient from "./GuestPageClient";

export function generateStaticParams() {
  return [{ id: "default" }];
}

export default function GuestPage() {
  return <GuestPageClient />;
}
