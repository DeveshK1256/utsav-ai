import ChangeProposalDiffClient from './ChangeProposalDiffClient';

export function generateStaticParams() {
  return [
    { id: 'default', change_id: 'default' }
  ];
}

export default function ChangeProposalDiffPage() {
  return <ChangeProposalDiffClient />;
}
