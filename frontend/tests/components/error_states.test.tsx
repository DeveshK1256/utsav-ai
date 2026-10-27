import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import React from 'react';
import { WakingUpNotice } from '@/components/ui/WakingUpNotice';
import { ElderDisclaimerBanner } from '@/components/ui/ElderDisclaimerBanner';
import { LanguageSelector } from '@/components/ui/LanguageSelector';
import NotFound from '@/app/not-found';

describe('Error States & Utility Components', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.lang = 'en';
  });

  describe('WakingUpNotice', () => {
    it('renders server waking notice when loading exceeds timeout', async () => {
      vi.useFakeTimers();
      render(<WakingUpNotice isLoading={true} timeoutMs={100} />);
      
      act(() => {
        vi.advanceTimersByTime(150);
      });

      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.getByText(/Utsav is waking up/i)).toBeInTheDocument();
      vi.useRealTimers();
    });

    it('returns null when isLoading is false', () => {
      const { container } = render(<WakingUpNotice isLoading={false} />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('ElderDisclaimerBanner', () => {
    it('renders cultural tradition disclaimer correctly', () => {
      render(
        <ElderDisclaimerBanner
          customText="Muhurat timings provided are astrological recommendations."
        />
      );
      expect(screen.getByText(/Muhurat timings provided are astrological recommendations./i)).toBeInTheDocument();
    });

    it('renders default cultural disclaimer when customText is omitted', () => {
      render(<ElderDisclaimerBanner />);
      expect(screen.getByText(/Cultural Trust Mandate:/i)).toBeInTheDocument();
      expect(screen.getByText(/Always verify with your family Guruji or elders/i)).toBeInTheDocument();
    });
  });

  describe('LanguageSelector', () => {
    it('renders available Indian languages and switches html lang attribute', () => {
      render(<LanguageSelector />);
      const select = screen.getByRole('combobox', { name: /Language/i });
      expect(select).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /EN/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /हिन्दी/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /मराठी/i })).toBeInTheDocument();

      // Switch to Hindi
      fireEvent.change(select, { target: { value: 'hi' } });
      expect(document.documentElement.lang).toBe('hi');
      expect(localStorage.getItem('utsav_locale')).toBe('hi');

      // Switch to Marathi
      fireEvent.change(select, { target: { value: 'mr' } });
      expect(document.documentElement.lang).toBe('mr');
      expect(localStorage.getItem('utsav_locale')).toBe('mr');
    });
  });

  describe('NotFound Page', () => {
    it('renders 404 message and return home action', () => {
      render(<NotFound />);
      expect(screen.getByText(/Page Not Found/i)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Return to Celebration Home/i })).toHaveAttribute('href', '/');
    });
  });
});
