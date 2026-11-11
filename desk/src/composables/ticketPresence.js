// One controller per mounted ticket view. No ticket contents are transmitted.
export function createTicketPresence(socket, userId, onChange, timers = globalThis) {
  let active = null;
  let timer = null;
  let disposed = false;
  let heartbeat = null;
  const clearTimer = () => {
    if (timer !== null) timers.clearTimeout(timer);
    timer = null;
  };
  const publish = (status, viewers = []) => onChange({ status, viewers });
  const join = () => {
    clearTimer();
    if (!active || disposed) return;
    publish(socket.connected ? 'connecting' : 'unavailable');
    if (!socket.connected) return;
    timer = timers.setTimeout(() => { timer = null; publish('unavailable'); }, 8000);
    socket.emit('view_ticket', active);
  };
  const refresh = () => {
    if (!active || !socket.connected || disposed || timer !== null) return;
    timer = timers.setTimeout(() => { timer = null; publish('unavailable'); }, 8000);
    socket.emit('ticket_get_viewers', active);
  };
  const onViewers = (data) => {
    if (!active || String(data?.ticket_id) !== active || disposed) return;
    let users;
    try { users = typeof data.users === 'string' ? JSON.parse(data.users) : data.users; }
    catch { return; }
    if (!Array.isArray(users) || !users.every(user => typeof user === 'string')) return;
    clearTimer();
    publish('ready', [...new Set(users)].filter(user => user !== userId && user !== 'Guest'));
  };
  const onDisconnect = () => {
    clearTimer();
    if (active) publish('unavailable');
  };
  socket.on('connect', join);
  socket.on('disconnect', onDisconnect);
  socket.on('connect_error', onDisconnect);
  socket.on('ticket_viewers', onViewers);
  const stopViewing = (id) => {
    if (!active || String(id) !== active) return;
    if (socket.connected) socket.emit('stop_view_ticket', active);
    active = null;
    clearTimer();
    if (heartbeat !== null) timers.clearInterval(heartbeat);
    heartbeat = null;
    publish('connecting');
  };
  return {
    startViewing(id) {
      if (disposed || id === null || id === undefined || String(id) === '') return;
      if (active) stopViewing(active);
      active = String(id);
      heartbeat = timers.setInterval(refresh, 20000);
      join();
    },
    stopViewing,
    cleanup() {
      if (disposed) return;
      if (active) stopViewing(active);
      disposed = true;
      socket.off('connect', join);
      socket.off('disconnect', onDisconnect);
      socket.off('connect_error', onDisconnect);
      socket.off('ticket_viewers', onViewers);
    },
  };
}
