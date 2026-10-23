import React from 'react';
import Link from 'next/link';
import { Navbar } from '@/components/ui/Navbar';
import { ElderDisclaimerBanner } from '@/components/ui/ElderDisclaimerBanner';

export const metadata = {
  title: 'Privacy Policy | Utsav AI',
  description: 'Privacy Policy and WhatsApp Business API Data Governance for Utsav AI Platform.'
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#FAF7F2] dark:bg-[#0C0F14] text-[#1C1917] dark:text-[#F8FAFC]">
      <Navbar />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-12 space-y-8 animate-fadeIn">
        {/* Header */}
        <div className="pb-6 border-b border-stone-200 dark:border-stone-800 space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 text-xs font-semibold">
            <span>🛡️</span> Data Governance & WhatsApp Privacy
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold font-serif text-stone-900 dark:text-stone-50">
            Privacy Policy
          </h1>
          <p className="text-xs text-stone-500 dark:text-stone-400">
            Effective Date: October 24, 2026 &bull; Version 1.0 &bull; Platform: Utsav (<code className="font-mono">utsav-ai</code>)
          </p>
        </div>

        {/* Core Summary Callout */}
        <div className="p-5 rounded-2xl bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200/80 dark:border-amber-900/60 space-y-1.5 text-xs">
          <div className="font-bold text-amber-900 dark:text-amber-200 flex items-center gap-1.5">
            <span>✨</span> Core Privacy Commitment
          </div>
          <p className="text-amber-800/90 dark:text-amber-300/90 leading-relaxed">
            Utsav never sells your personal data, never uses guest phone numbers for unsolicited marketing or advertising, and strictly enforces WhatsApp opt-outs (<code className="px-1 py-0.5 rounded bg-amber-100 dark:bg-amber-900 font-mono">STOP</code>) at the application send-layer. All guest and host data can be permanently erased upon request.
          </p>
        </div>

        {/* Section 1 */}
        <section className="space-y-3 text-xs leading-relaxed text-stone-700 dark:text-stone-300">
          <h2 className="text-base font-bold font-serif text-stone-900 dark:text-stone-100 flex items-center gap-2">
            <span>1.</span> Information We Collect
          </h2>
          <p>
            To deliver deterministic Indian celebration planning, budget rescaling, and WhatsApp guest coordination, we collect the following categories of information:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-stone-600 dark:text-stone-400">
            <li><strong>Host Identification:</strong> Full name, verified mobile phone number, email address, preferred regional celebration traditions, and event city/pincode.</li>
            <li><strong>Guest Contact Rosters:</strong> Names, mobile phone numbers (normalized to E.164), group/family affiliation (Bride Side, Groom Side, Society), headcount, dietary requirements (Pure Vegetarian, Jain, Non-Vegetarian), and accessibility requirements (wheelchair access).</li>
            <li><strong>Ceremony & Logistics Schedules:</strong> Sub-event timings, venue addresses, parking instructions, dress codes, and ceremonial guidelines.</li>
            <li><strong>Vendor & Financial Records:</strong> Total budget envelope, line-item quotations, payment milestone records, and contracts.</li>
          </ul>
        </section>

        {/* Section 2 */}
        <section className="space-y-3 text-xs leading-relaxed text-stone-700 dark:text-stone-300">
          <h2 className="text-base font-bold font-serif text-stone-900 dark:text-stone-100 flex items-center gap-2">
            <span>2.</span> WhatsApp Messaging & Meta Business API Compliance
          </h2>
          <p>
            Utsav utilizes the <strong>Meta WhatsApp Business Cloud API</strong> exclusively for transactional, event-related coordination authorized by the celebration host:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-stone-600 dark:text-stone-400">
            <li><strong>Digital Invitations:</strong> Dispatching interactive cards with structured RSVP buttons (<code className="font-mono">Attending</code>, <code className="font-mono">Decline</code>, <code className="font-mono">Maybe</code>).</li>
            <li><strong>Ceremony Reminders:</strong> Automated schedule updates dispatched at deterministic intervals (7 days before, 1 day before, and morning-of) computed directly from ceremony start times without artificial delays.</li>
            <li><strong>Event Concierge Bot:</strong> Providing verified answers to guest inquiries regarding venue address, parking, and dress code.</li>
          </ul>
          <div className="p-3.5 rounded-xl bg-stone-100 dark:bg-stone-900 border border-stone-200 dark:border-stone-800 text-[11px] text-stone-600 dark:text-stone-400">
            <strong>Strict Fact Sheet Scope (DEC-025):</strong> The WhatsApp guest bot answers questions strictly from the host-verified event fact sheet. It is technologically restricted from revealing private financial information, vendor costs, or third-party details.
          </div>
        </section>

        {/* Section 3 */}
        <section className="space-y-3 text-xs leading-relaxed text-stone-700 dark:text-stone-300">
          <h2 className="text-base font-bold font-serif text-stone-900 dark:text-stone-100 flex items-center gap-2">
            <span>3.</span> Guest Consent & Mandatory Opt-Out Policy (STOP Keyword)
          </h2>
          <p>
            In compliance with Meta Business Policies and global telecommunications anti-spam standards:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-stone-600 dark:text-stone-400">
            <li><strong>Host-Authorized Dispatch:</strong> Hosts confirm that guests are personal acquaintances, family members, or community attendees before importing contact numbers.</li>
            <li><strong>Instant Opt-Out (DEC-026):</strong> Any recipient may reply <code className="font-mono font-bold">STOP</code>, <code className="font-mono font-bold">UNSUBSCRIBE</code>, <code className="font-mono font-bold">CANCEL</code>, or <code className="font-mono font-bold">HALT</code> at any time.</li>
            <li><strong>Send-Layer Guardrail:</strong> Opt-out requests immediately persist to our database blocklist (<code className="font-mono">opt_outs</code>). Before every single outbound transmission, the phone number is verified; if present, the message is blocked prior to reaching external gateways.</li>
          </ul>
        </section>

        {/* Section 4 */}
        <section className="space-y-3 text-xs leading-relaxed text-stone-700 dark:text-stone-300">
          <h2 className="text-base font-bold font-serif text-stone-900 dark:text-stone-100 flex items-center gap-2">
            <span>4.</span> Data Retention & Right to Erasure (PII Purge)
          </h2>
          <p>
            We adhere to strict data minimization principles:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-stone-600 dark:text-stone-400">
            <li><strong>Immediate Data Deletion:</strong> Event hosts can delete any individual guest record at any time via the unified dashboard or using the direct API endpoint <code className="font-mono">DELETE /api/v1/events/&#123;id&#125;/guests/&#123;guest_id&#125;</code>.</li>
            <li><strong>Lifecycle Retention:</strong> Guest contact lists and RSVP logs are retained only during the planning and execution phase of the event. Data can be permanently expunged upon host request.</li>
          </ul>
        </section>

        {/* Section 5 */}
        <section className="space-y-3 text-xs leading-relaxed text-stone-700 dark:text-stone-300">
          <h2 className="text-base font-bold font-serif text-stone-900 dark:text-stone-100 flex items-center gap-2">
            <span>5.</span> Security & Infrastructure Partners
          </h2>
          <p>
            Data integrity and privacy are protected through enterprise security controls:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-stone-600 dark:text-stone-400">
            <li><strong>Encryption in Transit:</strong> 100% of network traffic is encrypted via TLS 1.3 / HTTPS. Inbound Meta webhooks require cryptographic HMAC-SHA256 signature verification.</li>
            <li><strong>Managed Cloud Infrastructure:</strong> Backend services and managed PostgreSQL databases run in dedicated Singapore data centers on Render; static assets are distributed via Netlify Edge CDN.</li>
          </ul>
        </section>

        {/* Section 6 */}
        <section className="space-y-3 text-xs leading-relaxed text-stone-700 dark:text-stone-300">
          <h2 className="text-base font-bold font-serif text-stone-900 dark:text-stone-100 flex items-center gap-2">
            <span>6.</span> Contact & Data Protection Officer
          </h2>
          <p>
            For privacy inquiries, data access requests, or Meta WhatsApp Business integration questions, contact our security team:
          </p>
          <div className="p-4 rounded-xl bg-stone-50 dark:bg-stone-900/60 border border-stone-200 dark:border-stone-800 space-y-1">
            <div><strong>Email:</strong> <a href="mailto:privacy@utsav.ai" className="text-[#8B1E28] dark:text-[#F4B41A] font-semibold underline">privacy@utsav.ai</a></div>
            <div><strong>Service:</strong> Utsav AI Platform (<code className="font-mono">utsav-ai</code>)</div>
            <div><strong>URL:</strong> <a href="https://utsav-ai.netlify.app" className="text-[#8B1E28] dark:text-[#F4B41A] font-semibold underline">https://utsav-ai.netlify.app</a></div>
          </div>
        </section>

        {/* Footer Navigation */}
        <div className="pt-6 border-t border-stone-200 dark:border-stone-800 flex items-center justify-between text-xs text-stone-500">
          <Link href="/" className="hover:text-stone-900 dark:hover:text-white font-semibold">
            ← Return to Home
          </Link>
          <span className="font-mono">&copy; 2026 Utsav AI</span>
        </div>

        <ElderDisclaimerBanner />
      </main>
    </div>
  );
}
