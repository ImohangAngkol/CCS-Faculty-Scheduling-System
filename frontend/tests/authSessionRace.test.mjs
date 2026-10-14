import {test} from 'node:test';
import assert from 'node:assert/strict';
import axios from 'axios';
import {apiClient, apiFetch, setSessionSecurity} from '../src/services/apiSession.ts';

for (const transport of ['fetch', 'axios']) {
  for (const changedSession of [true, false]) {
    test(`${transport}: ${changedSession ? 'late prior-session 401 preserves a new login' : 'current-session 401 still expires authentication'}`, async () => {
      const originalWindow = global.window, originalFetch = global.fetch;
      const events = [];
      global.window = new EventTarget();
      global.window.addEventListener('ccs-session-expired', () => events.push('expired'));
      let deliver;
      setSessionSecurity('test-session-before');
      try {
        let request;
        if (transport === 'fetch') {
          global.fetch = async () => new Promise(resolve => {deliver = () => resolve(Response.json({detail:'Session expired'}, {status:401}));});
          request = apiFetch('http://localhost:8000/api/auth/me');
        } else {
          request = apiClient.get('/api/auth/me', {adapter: config => new Promise((_resolve, reject) => {
            deliver = () => reject(new axios.AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null,
              {status:401, statusText:'Unauthorized', headers:{}, config, data:{detail:'Session expired'}}));
          })}).catch(() => null);
          await new Promise(resolve => setImmediate(resolve));
        }
        assert.equal(typeof deliver, 'function');
        if (changedSession) setSessionSecurity('test-session-after');
        deliver(); await request;
        assert.equal(events.length, changedSession ? 0 : 1);
      } finally {
        setSessionSecurity(null); global.fetch = originalFetch;
        if (originalWindow === undefined) delete global.window; else global.window = originalWindow;
      }
    });
  }
}
