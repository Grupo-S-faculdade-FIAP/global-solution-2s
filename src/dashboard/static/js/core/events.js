/** Pub/sub leve para desacoplar maps, sections e theme. */

const listeners = new Map();

export function on(event, handler) {
  if (!listeners.has(event)) listeners.set(event, new Set());
  listeners.get(event).add(handler);
  return () => listeners.get(event)?.delete(handler);
}

export async function emit(event, detail) {
  const handlers = listeners.get(event);
  if (!handlers?.size) return;
  await Promise.all([...handlers].map((handler) => handler(detail)));
}
