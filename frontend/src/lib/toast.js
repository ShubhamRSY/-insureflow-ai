let nextId = 1;
const listeners = new Set();

function emit(kind, message) {
  const item = { id: nextId++, kind, message: String(message ?? '') };
  listeners.forEach((fn) => fn(item));
  return item.id;
}

export const toast = {
  success(message) { return emit('success', message); },
  error(message) { return emit('error', message); },
  info(message) { return emit('info', message); },
  subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
};
