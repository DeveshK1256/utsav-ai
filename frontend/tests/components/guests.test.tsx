import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import React from 'react';
import { GuestCoordinationModule } from '@/components/ui/GuestCoordinationModule';

const mockSummary = {
  total_guests: 3,
  attending_count: 2,
  declined_count: 1,
  maybe_count: 0,
  pending_count: 0,
  total_confirmed_headcount: 4,
  diet_breakdown: { veg: 2, jain: 1, non_veg: 0 },
  mobility_needs_count: 1,
  kids_count: 1,
  accommodation_needed_count: 0
};

const mockGuests = [
  {
    id: 'g-1',
    name: 'Aarav Patel',
    phone: '+919876543210',
    group_side: 'groom',
    diet: 'veg',
    mobility_needs: false,
    kids_count: 1,
    headcount: 2,
    rsvp_status: 'attending',
    created_at: '2026-10-01T10:00:00Z'
  },
  {
    id: 'g-2',
    name: 'Pooja Shah',
    phone: '+919876543211',
    group_side: 'bride',
    diet: 'jain',
    mobility_needs: true,
    kids_count: 0,
    headcount: 1,
    rsvp_status: 'attending',
    created_at: '2026-10-01T10:05:00Z'
  },
  {
    id: 'g-3',
    name: 'Rohan Deshmukh',
    phone: '+919876543212',
    group_side: 'common',
    diet: 'veg',
    mobility_needs: false,
    kids_count: 0,
    headcount: 1,
    rsvp_status: 'declined',
    created_at: '2026-10-01T10:10:00Z'
  }
];

const mockFactSheet = {
  venue_address: 'Taj Palace, Mumbai',
  parking_info: 'Valet parking at Gate 2',
  dress_code: 'Traditional / Formal',
  timing_notes: 'Baraat arrives at 4:30 PM',
  map_link: 'https://maps.google.com/?q=Taj+Palace',
  other_facts: {}
};

describe('GuestCoordinationModule Component', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn((url: string, options?: RequestInit) => {
      const urlStr = String(url);
      if (urlStr.includes('/guests/rsvp-summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary)
        });
      }
      if (urlStr.includes('/fact-sheet')) {
        if (options?.method === 'POST') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ status: 'updated' })
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockFactSheet)
        });
      }
      if (urlStr.includes('/guests/import')) {
        const bodyObj = options?.body ? JSON.parse(options.body) : {};
        const firstGuest = bodyObj.guests?.[0];
        if (firstGuest && firstGuest.phone === '12345') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              successful_count: 0,
              skipped_duplicates_count: 0,
              invalid_rows_count: 1,
              errors: [
                { row_number: 1, name: 'Kabir', phone_raw: '12345', reason: 'Invalid phone number format' }
              ]
            })
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            successful_count: 1,
            skipped_duplicates_count: 0,
            invalid_rows_count: 0,
            errors: []
          })
        });
      }
      if (options?.method === 'DELETE') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ status: 'purged' })
        });
      }
      // Default guests list
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockGuests)
      });
    }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders guest coordination dashboard with metrics and guest table', async () => {
    render(
      <GuestCoordinationModule
        eventId="evt-100"
        eventName="Ananya & Kabir Vivah"
        apiBase="http://localhost:8000"
      />
    );

    // Verify loading resolution
    await waitFor(() => {
      expect(screen.getByText('Aarav Patel')).toBeInTheDocument();
    });

    expect(screen.getByText('Pooja Shah')).toBeInTheDocument();
    expect(screen.getByText('Rohan Deshmukh')).toBeInTheDocument();
    expect(screen.getByText('+919876543210')).toBeInTheDocument();

    // Verify dietary breakdown badges
    expect(screen.getByText(/Pure Veg: 2/i)).toBeInTheDocument();
    expect(screen.getByText(/Jain: 1/i)).toBeInTheDocument();
  });

  it('filters guests by RSVP status tab', async () => {
    render(
      <GuestCoordinationModule
        eventId="evt-100"
        eventName="Ananya & Kabir Vivah"
        apiBase="http://localhost:8000"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Aarav Patel')).toBeInTheDocument();
    });

    // Click "Declined" filter
    const declinedBtn = screen.getByRole('button', { name: /Declined/i });
    fireEvent.click(declinedBtn);

    // Rohan is declined, Aarav is attending
    expect(screen.getByText('Rohan Deshmukh')).toBeInTheDocument();
    expect(screen.queryByText('Aarav Patel')).not.toBeInTheDocument();
  });

  it('opens import modal and handles validation errors on invalid phone numbers', async () => {
    render(
      <GuestCoordinationModule
        eventId="evt-100"
        eventName="Ananya & Kabir Vivah"
        apiBase="http://localhost:8000"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Aarav Patel')).toBeInTheDocument();
    });

    // Open Import Modal
    const importBtn = screen.getByRole('button', { name: /Import Guests/i });
    fireEvent.click(importBtn);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/Import Guest Roster/i)).toBeInTheDocument();

    // Enter invalid guest entry (invalid phone format)
    const textarea = screen.getByPlaceholderText(/Rohan Sharma/i);
    fireEvent.change(textarea, { target: { value: 'Kabir, 12345, veg' } });

    const validateBtn = screen.getByRole('button', { name: /Validate & Import/i });
    fireEvent.click(validateBtn);

    // Assert validation error feedback is rendered
    await waitFor(() => {
      expect(screen.getByText(/1 rows rejected due to invalid numbers/i)).toBeInTheDocument();
    });
  });

  it('purges a guest when delete action is executed', async () => {
    render(
      <GuestCoordinationModule
        eventId="evt-100"
        eventName="Ananya & Kabir Vivah"
        apiBase="http://localhost:8000"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Aarav Patel')).toBeInTheDocument();
    });

    // Find delete buttons
    const deleteButtons = screen.getAllByRole('button', { name: /^Delete$/i });
    expect(deleteButtons.length).toBeGreaterThan(0);

    // Mock confirm
    vi.spyOn(window, 'confirm').mockImplementation(() => true);

    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/events/evt-100/guests/g-1'),
        expect.objectContaining({ method: 'DELETE' })
      );
    });
  });
});
