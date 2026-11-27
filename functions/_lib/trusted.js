// TRUSTED_HELPERS secret: "Name:key,Name2:key2". Returns the helper's name for a matching key.
export async function trustedHelper(env, key) {
  if (!env.TRUSTED_HELPERS || !key) return null;
  const enc = new TextEncoder();
  const want = new Uint8Array(await crypto.subtle.digest("SHA-256", enc.encode(key)));
  for (const pair of String(env.TRUSTED_HELPERS).split(",")) {
    const i = pair.indexOf(":");
    if (i < 1) continue;
    const who = pair.slice(0, i).trim(), k = pair.slice(i + 1).trim();
    if (!k) continue;
    const have = new Uint8Array(await crypto.subtle.digest("SHA-256", enc.encode(k)));
    let diff = 0;
    for (let j = 0; j < have.length; j++) diff |= have[j] ^ want[j];
    if (diff === 0) return who.slice(0, 60);
  }
  return null;
}

