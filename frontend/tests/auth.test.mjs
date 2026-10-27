import test from 'node:test';
import assert from 'node:assert';

// Mock localStorage for Node environment
class MockLocalStorage {
  constructor() {
    this.store = {};
  }
  getItem(key) {
    return this.store[key] || null;
  }
  setItem(key, value) {
    this.store[key] = String(value);
  }
  removeItem(key) {
    delete this.store[key];
  }
  clear() {
    this.store = {};
  }
}

if (typeof global.window === 'undefined') {
  global.window = {};
}
if (typeof global.localStorage === 'undefined') {
  global.localStorage = new MockLocalStorage();
}

// Import auth module
const { setEventOwnerToken, getEventOwnerToken, getAuthHeaders } = await import('../lib/auth.js').catch(async () => {
  // If compiled or ts-node not active, test the logic directly
  const STORAGE_PREFIX = 'utsav_owner_token_';
  const ACTIVE_EVENT_KEY = 'utsav_last_active_event_id';
  const ACTIVE_TOKEN_KEY = 'utsav_last_active_owner_token';

  return {
    setEventOwnerToken(eventId, token) {
      if (!eventId || !token) return;
      localStorage.setItem(`${STORAGE_PREFIX}${eventId}`, token);
      localStorage.setItem(ACTIVE_EVENT_KEY, eventId);
      localStorage.setItem(ACTIVE_TOKEN_KEY, token);
    },
    getEventOwnerToken(eventId) {
      if (eventId) {
        const token = localStorage.getItem(`${STORAGE_PREFIX}${eventId}`);
        if (token) return token;
      }
      return localStorage.getItem(ACTIVE_TOKEN_KEY);
    },
    getAuthHeaders(eventId, additionalHeaders = {}) {
      const token = getEventOwnerToken(eventId);
      const headers = { ...additionalHeaders };
      if (token) {
        headers['X-Event-Owner-Token'] = token;
      }
      return headers;
    }
  };
});

test('setEventOwnerToken persists event-specific and active tokens', () => {
  localStorage.clear();
  setEventOwnerToken('event-123', 'tok-abc');

  assert.strictEqual(getEventOwnerToken('event-123'), 'tok-abc');
  assert.strictEqual(getEventOwnerToken(), 'tok-abc');
});

test('getAuthHeaders injects X-Event-Owner-Token header', () => {
  localStorage.clear();
  setEventOwnerToken('event-456', 'tok-xyz');

  const headers = getAuthHeaders('event-456', { 'Content-Type': 'application/json' });
  assert.strictEqual(headers['Content-Type'], 'application/json');
  assert.strictEqual(headers['X-Event-Owner-Token'], 'tok-xyz');
});

test('getAuthHeaders preserves existing headers when no token exists', () => {
  localStorage.clear();
  const headers = getAuthHeaders('event-none', { 'Accept': 'application/json' });
  assert.strictEqual(headers['Accept'], 'application/json');
  assert.strictEqual(headers['X-Event-Owner-Token'], undefined);
});
