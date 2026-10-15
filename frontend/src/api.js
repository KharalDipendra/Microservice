// Small fetch wrapper used by every component. All calls go through the gateway (/api).
export async function api(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
    body: options.body && JSON.stringify(options.body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    // 502/504 come from the gateway (HTML, no JSON) when a service is down
    const down = res.status === 502 || res.status === 504
    throw new Error(data.error || (down ? 'That service is unavailable right now, please try again shortly' : `Request failed (${res.status})`))
  }
  return data
}
