import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createTicketPresence } from '../src/composables/ticketPresence.js';
function fixture(connected = true) {
  const listeners = new Map(), emitted = [], states = [], timeouts = new Map(), intervals = new Map();
  let id = 0;
  const socket = { connected,
    on(event, handler) { if (!listeners.has(event)) listeners.set(event, new Set()); listeners.get(event).add(handler); },
    off(event, handler) { listeners.get(event)?.delete(handler); },
    emit(...args) { emitted.push(args); },
    receive(event, data) { for (const handler of listeners.get(event) || []) handler(data); },
  };
  const timers = {
    setTimeout(fn) { const key = ++id; timeouts.set(key, fn); return key; },
    clearTimeout(key) { timeouts.delete(key); },
    setInterval(fn) { const key = ++id; intervals.set(key, fn); return key; },
    clearInterval(key) { intervals.delete(key); },
  };
  const controller = createTicketPresence(socket, 'me@example.invalid', state => states.push(state), timers);
  return { socket, emitted, states, listeners, timeouts, intervals, controller,
    viewers(ticket, users) { socket.receive('ticket_viewers', {ticket_id: ticket, users: JSON.stringify(users)}); },
    last() { return states.at(-1); },
  };
}
test('joins, excludes self, deduplicates and accepts numeric ticket IDs', () => {
  const f = fixture(); f.controller.startViewing('1');
  assert.deepEqual(f.emitted, [['view_ticket','1']]);
  f.viewers(1, ['me@example.invalid','other@example.invalid','other@example.invalid','Guest']);
  assert.deepEqual(f.last(), {status:'ready', viewers:['other@example.invalid']});
  assert.equal(f.timeouts.size, 0);
});
test('disconnect clears stale viewers and reconnect rejoins current ticket', () => {
  const f = fixture(); f.controller.startViewing('1'); f.viewers('1',['other@example.invalid']);
  f.socket.connected = false; f.socket.receive('disconnect');
  assert.deepEqual(f.last(), {status:'unavailable',viewers:[]});
  f.socket.connected = true; f.socket.receive('connect');
  assert.deepEqual(f.emitted.at(-1), ['view_ticket','1']);
  f.viewers('1',[]); assert.deepEqual(f.last(), {status:'ready',viewers:[]});
});
test('navigation leaves old room and ignores delayed old-room payloads', () => {
  const f = fixture(); f.controller.startViewing('1'); f.controller.startViewing('2');
  assert.deepEqual(f.emitted.slice(-2), [['stop_view_ticket','1'],['view_ticket','2']]);
  const before = f.states.length; f.viewers('1',['old@example.invalid']); assert.equal(f.states.length,before);
  f.viewers('2',['current@example.invalid']); assert.deepEqual(f.last().viewers,['current@example.invalid']);
});
test('malformed payload cannot show an empty ready state', () => {
  const f = fixture(); f.controller.startViewing('1');
  for (const users of ('{', '{}', '[123]')) f.socket.receive('ticket_viewers',{ticket_id:'1',users});
  assert.equal(f.last().status,'connecting');
  for (const fn of [...f.timeouts.values()]) fn();
  assert.equal(f.last().status,'unavailable');
});
test('periodic snapshots refresh stale viewers without additional room joins', () => {
  const f = fixture(); f.controller.startViewing('1'); f.viewers('1',['other@example.invalid']);
  for (const fn of f.intervals.values()) fn();
  assert.deepEqual(f.emitted.at(-1), ['ticket_get_viewers','1']);
  f.viewers('1',[]); assert.deepEqual(f.last(), {status:'ready',viewers:[]});
});
test('initially disconnected socket waits for connect rather than buffering stale joins', () => {
  const f = fixture(false); f.controller.startViewing('1'); assert.equal(f.emitted.length,0);
  assert.equal(f.last().status,'unavailable'); f.socket.connected=true; f.socket.receive('connect');
  assert.deepEqual(f.emitted,[['view_ticket','1']]);
});
test('cleanup is idempotent and removes only owned listeners and all timers', () => {
  const f = fixture(); const unrelated=()=>{}; f.socket.on('ticket_viewers',unrelated);
  f.controller.startViewing('1'); f.controller.cleanup(); f.controller.cleanup();
  assert.equal(f.timeouts.size,0); assert.equal(f.intervals.size,0);
  assert.deepEqual([...f.listeners.get('ticket_viewers')],[unrelated]);
  assert.equal(f.listeners.get('connect').size,0);
  const before=f.emitted.length; f.socket.receive('connect');f.controller.startViewing('2');assert.equal(f.emitted.length,before);
});
