/** Cliente HTTP do dashboard com timeout e retry em 502/503/504. */

export const FETCH_TIMEOUT_MS = 15000;

export async function fetchApi(url, options = {}, retries = 2) {
  const baseOpts = {
    cache: "no-store",
    headers: { Accept: "application/json", ...(options.headers || {}) },
    ...options,
  };

  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    try {
      const response = await fetch(url, { ...baseOpts, signal: controller.signal });
      if (response.ok || ![502, 503, 504].includes(response.status) || attempt === retries) {
        return response;
      }
    } catch (err) {
      if (attempt === retries) throw err;
    } finally {
      clearTimeout(timer);
    }
    await new Promise((resolve) => setTimeout(resolve, 1500 * (attempt + 1)));
  }
  throw new Error(`fetchApi timeout: ${url}`);
}
