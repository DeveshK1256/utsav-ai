import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import React from 'react';
import ComposePageClient from '@/app/dashboard/events/[id]/compose/ComposePageClient';

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'evt-compose-101' }),
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn()
  })
}));

const mockEventData = {
  id: 'evt-compose-101',
  name: 'Meera & Siddharth Vivah',
  city: 'Pune',
  start_date: '2026-12-15',
  metadata_json: {
    venue_name: 'Blue Diamond Ballroom'
  },
  sub_events: [
    {
      id: 'sub-1',
      name: 'Vedic Wedding Ceremony & Pheras',
      start_time: '2026-12-15T10:00:00',
      end_time: '2026-12-15T13:00:00',
      is_muhurat_locked: true
    }
  ]
};

const mockVendorsResponse = {
  source: 'database',
  query_city: 'Pune',
  radius_km: 25.0,
  total_results: 1,
  results: [
    {
      id: 'v-1',
      name: 'Blue Diamond Ballroom Pune',
      category: 'venue',
      city: 'Pune',
      rating_tier: 'top_tier',
      average_rating: 4.8,
      rating_count: 52,
      price_range: '₹₹₹',
      starting_price_inr: 250000.0,
      verified_partner: true,
      distance_km: 2.4
    }
  ]
};

describe('ComposePageClient Component', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/dashboard/events/evt-compose-101/compose');
    localStorage.setItem('current_event_id', 'evt-compose-101');
    vi.stubGlobal('fetch', vi.fn((url: string, options?: RequestInit) => {
      const urlStr = String(url);
      if (urlStr.includes('/discovery/vendors')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockVendorsResponse)
        });
      }
      if (urlStr.includes('/rituals/muhurat-candidates')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ candidates: [] })
        });
      }
      if (options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            ...mockEventData,
            metadata_json: { compose_celebration: { current_step: 'timing' } }
          })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockEventData)
      });
    }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders compose workflow with celebration header and step progress', async () => {
    render(<ComposePageClient />);

    await waitFor(() => {
      expect(screen.getByText(/Compose Celebration \(Stage 4\)/i)).toBeInTheDocument();
    });

    // Step indicators
    expect(screen.getByText(/Step A: Venue/i)).toBeInTheDocument();
    expect(screen.getByText(/Step B: Timing/i)).toBeInTheDocument();
    expect(screen.getByText(/Step C: Invitation/i)).toBeInTheDocument();
    expect(screen.getByText(/Step A: Select or Shortlist a Celebration Venue/i)).toBeInTheDocument();
  });

  it('navigates through composition wizard steps via skip actions', async () => {
    render(<ComposePageClient />);

    await waitFor(() => {
      expect(screen.getByText(/Compose Celebration \(Stage 4\)/i)).toBeInTheDocument();
    });

    // Click "Skip for now →" on venue step to advance to timing step
    const skipVenueBtn = screen.getByRole('button', { name: /Skip for now →/i });
    fireEvent.click(skipVenueBtn);

    await waitFor(() => {
      expect(screen.getByText(/Step B: Confirm Auspicious Muhurat Timing/i)).toBeInTheDocument();
    });
  });

  it('handles error state when event fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('Network offline'))));

    render(<ComposePageClient />);

    await waitFor(() => {
      expect(screen.getByText(/Network offline/i)).toBeInTheDocument();
    });
  });
});
