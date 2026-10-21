import React from 'react';

interface ElderDisclaimerBannerProps {
  className?: string;
  customText?: string;
}

export const ElderDisclaimerBanner: React.FC<ElderDisclaimerBannerProps> = ({
  className = '',
  customText
}) => {
  return (
    <div className={`p-4 rounded-xl bg-amber-50/90 dark:bg-amber-950/30 border border-amber-300/70 dark:border-amber-800/60 text-amber-900 dark:text-amber-200 text-xs flex items-start space-x-3 shadow-sm ${className}`}>
      <span className="text-marigold text-base flex-shrink-0" aria-hidden="true">🪔</span>
      <div className="leading-relaxed">
        <strong className="font-semibold uppercase tracking-wider block mb-0.5">Cultural Trust Mandate:</strong>
        {customText || "Auspicious timings, ritual sequencing, and samagri requirements are algorithmic estimates computed via astronomical ephemeris models. Always verify with your family Guruji or elders prior to locking ceremony muhurats."}
      </div>
    </div>
  );
};
