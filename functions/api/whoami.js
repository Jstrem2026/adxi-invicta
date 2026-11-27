// ADXI: Invicta: is this browser recognised as Jordan or a trusted helper? GET /api/whoami
import { trustedFrom } from "../_lib/trusted.js";

export async function onRequestGet({ request, env }) {
  const name = await trustedFrom(env, request);
  return new Response(JSON.stringify({ name: name || null }), {
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}
