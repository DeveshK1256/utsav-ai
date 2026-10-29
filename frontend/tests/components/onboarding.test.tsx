import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import React from 'react';
import OnboardingPage from '@/app/onboarding/page';

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn()
  })
}));

const mockBudgetResponse = {
  city: 'Pune',
  city_tier: 'tier2',
  city_tier_multiplier: 1.0,
  total_budget: 3500000,
  scaled_envelope: 3500000,
  items: [
    {
      category: 'venue',
      percentage: 25.0,
      planned_amount: 875000,
      city_tier: 'tier2',
      city_tier_multiplier: 1.0,
      reasoning_spec: { formula: 'base', city_tier: 'tier2', guest_count: 350, benchmark_basis: 'historical' }
    }
  ]
};

describe('OnboardingPage Component', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal('fetch', vi.fn((url: string, options?: RequestInit) => {
      const urlStr = String(url);
      if (urlStr.includes('/intake/calculate-budget')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockBudgetResponse)
        });
      }
      if (urlStr.includes('/intake/generate')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            event_id: 'evt-onboard-101',
            name: "Ananya & Rohan's Wedding",
            owner_name: 'Ananya Sharma',
            owner_token: 'sec-tok-12345',
            city: 'Pune',
            city_tier: 'tier2',
            guest_count: 350,
            total_budget: 3500000,
            tradition_code: 'maharashtrian_vedic',
            elder_verification_disclaimer: 'Astrological estimate only.',
            sub_events: [],
            budget_breakdown: [],
            tasks: [],
            created_at: new Date().toISOString()
          })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({})
      });
    }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders celebration types and initial intake form fields', () => {
    render(<OnboardingPage />);

    expect(screen.getByRole('heading', { level: 2, name: /Choose Celebration Type/i })).toBeInTheDocument();

    // Celebration type buttons
    expect(screen.getByRole('button', { name: /^💍\s*Wedding/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Birthday Party/i })).toBeInTheDocument();

    // Form inputs
    expect(screen.getByLabelText(/Celebration Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Primary Host \/ Committee Lead/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Celebration City/i)).toBeInTheDocument();
  });

  it('updates form fields and default values on celebration type change', () => {
    render(<OnboardingPage />);

    const birthdayBtn = screen.getByRole('button', { name: /Birthday Party/i });
    fireEvent.click(birthdayBtn);

    const nameInput = screen.getByLabelText(/Celebration Name/i) as HTMLInputElement;
    expect(nameInput.value).toContain('Birthday');
  });

  it('navigates to Step 2: Cultural Tradition Selection', async () => {
    render(<OnboardingPage />);

    // Step 1: Click "Continue to Format & Heritage→"
    const nextBtn = screen.getByRole('button', { name: /Continue to Format & Heritage→/i });
    fireEvent.click(nextBtn);

    await waitFor(() => {
      expect(screen.getByText(/Select Event Format & Heritage/i)).toBeInTheDocument();
    });

    // Check tradition options
    expect(screen.getByText(/Maharashtrian Vedic Lagna/i)).toBeInTheDocument();
    expect(screen.getByText(/Punjabi Traditional Vivah/i)).toBeInTheDocument();
  });
});
