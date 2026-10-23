import assert from 'node:assert/strict';
import test from 'node:test';
import { request, ApiError } from './api.ts';

process.env.EXPO_PUBLIC_API_URL = 'http://localhost:8000';
const unavailable = () => new Response(JSON.stringify({ detail: 'Serviço indisponível.' }), { status: 503 });

test('GET repeats a transient failure once and returns the successful result', async t => {
  let count = 0;
  t.mock.method(globalThis, 'fetch', async () => ++count === 1 ? unavailable() : Response.json({ ok: true }));
  assert.deepEqual(await request('/projection'), { ok: true });
  assert.equal(count, 2);
});

test('repeated 503 stops after two reads and preserves server status', async t => {
  let count = 0;
  t.mock.method(globalThis, 'fetch', async () => { count++; return unavailable(); });
  await assert.rejects(request('/projection'), e => e instanceof ApiError && e.status === 503);
  assert.equal(count, 2);
});

test('financial writes and login are never retried', async t => {
  let count = 0;
  t.mock.method(globalThis, 'fetch', async () => { count++; return unavailable(); });
  for (const method of ['POST', 'PATCH', 'DELETE']) {
    const previous = count;
    await assert.rejects(request('/operation', undefined, method, { amount_cents: 100 }));
    assert.equal(count, previous + 1);
  }
});

test('expired access is surfaced immediately without retrying', async t => {
  let count = 0;
  t.mock.method(globalThis, 'fetch', async () => { count++; return new Response('{}', { status: 401 }); });
  await assert.rejects(request('/auth/me'), e => e.status === 401);
  assert.equal(count, 1);
});

test('HTML gateway responses keep HTTP status instead of claiming a network error', async t => {
  let count = 0;
  t.mock.method(globalThis, 'fetch', async () => { count++; return new Response('<html>Unavailable</html>', { status: 502 }); });
  await assert.rejects(request('/accounts'), e => e.status === 502 && /Servidor/.test(e.message));
  assert.equal(count, 2);
});

test('a network interruption retries only a read', async t => {
  let count = 0;
  t.mock.method(globalThis, 'fetch', async () => { if (++count === 1) throw new TypeError('network'); return Response.json([]); });
  assert.deepEqual(await request('/accounts'), []);
  assert.equal(count, 2);
});


test('timeout while reading the response body is reported as timeout and retried once', async t => {
  let count = 0;
  t.mock.method(globalThis, 'fetch', async () => {
    count++;
    return { ok: true, status: 200, json: async () => { throw new DOMException('aborted', 'AbortError'); } };
  });
  await assert.rejects(request('/projection'), e => e.status === 0 && /demorou/.test(e.message));
  assert.equal(count, 2);
});
