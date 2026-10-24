/**
 * Authentication and event ownership token utilities for Utsav AI.
 * Handles persistence and attachment of X-Event-Owner-Token for mutating operations.
 */

const STORAGE_PREFIX = 'utsav_owner_token_';
const ACTIVE_EVENT_KEY = 'utsav_last_active_event_id';
const ACTIVE_TOKEN_KEY = 'utsav_last_active_owner_token';

/**
 * Stores the owner token for a specific event into localStorage.
 * Also tracks the most recent active event ID and active token.
 */
export function setEventOwnerToken(eventId: string, token: string): void {
  if (typeof window === 'undefined' || !eventId || !token) return;
  try {
    localStorage.setItem(`${STORAGE_PREFIX}${eventId}`, token);
    localStorage.setItem(ACTIVE_EVENT_KEY, eventId);
    localStorage.setItem(ACTIVE_TOKEN_KEY, token);
  } catch (e) {
    console.warn('Unable to persist owner token to localStorage:', e);
  }
}

/**
 * Retrieves the owner token for a specific event from localStorage.
 * Falls back to the last active owner token if event-specific match is missing.
 */
export function getEventOwnerToken(eventId?: string): string | null {
  if (typeof window === 'undefined') return null;
  try {
    if (eventId) {
      const token = localStorage.getItem(`${STORAGE_PREFIX}${eventId}`);
      if (token) return token;
    }
    return localStorage.getItem(ACTIVE_TOKEN_KEY);
  } catch (e) {
    console.warn('Unable to read owner token from localStorage:', e);
    return null;
  }
}

/**
 * Returns an authorization header object containing X-Event-Owner-Token if present.
 */
export function getAuthHeaders(
  eventId?: string,
  additionalHeaders: Record<string, string> = {}
): Record<string, string> {
  const token = getEventOwnerToken(eventId);
  const headers: Record<string, string> = { ...additionalHeaders };
  if (token) {
    headers['X-Event-Owner-Token'] = token;
  }
  return headers;
}
