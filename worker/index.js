// Avalia a foto da refeição com o Claude. Roda no Cloudflare Workers.
// Variáveis (Settings > Variables): ANTHROPIC_API_KEY (secreta), FIREBASE_API_KEY, ALLOWED_ORIGIN, ALLOWED_EMAILS (opcional, separados por vírgula).
import Anthropic from "@anthropic-ai/sdk";

const json = (body, status, origin) => new Response(JSON.stringify(body), {
  status, headers: {"Content-Type": "application/json", "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Headers": "Content-Type, Authorization", "Access-Control-Allow-Methods": "POST, OPTIONS"}});

async function firebaseUser(idToken, apiKey){
  const r = await fetch(`https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=${apiKey}`, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({idToken})});
  if (!r.ok) return null;
  return (await r.json()).users?.[0] || null;
}

function parseAnswer(text){
  const m = text.match(/\{[\s\S]*\}/);
  if (!m) throw new Error("sem JSON");
  const o = JSON.parse(m[0]);
  return {nota: Math.max(0, Math.min(10, Math.round(+o.nota || 0))), no_plano: !!o.no_plano, porcao: String(o.porcao || "").slice(0, 10),
    vistos: (Array.isArray(o.vistos) ? o.vistos : []).slice(0, 5).map(String), comentario: String(o.comentario || "").slice(0, 280)};
}

export default {
  async fetch(req, env){
    const origin = env.ALLOWED_ORIGIN || "*";
    if (req.method === "OPTIONS") return json({}, 204, origin);
    if (req.method !== "POST") return json({error:"use POST"}, 405, origin);

    const token = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/, "");
    const user = token && await firebaseUser(token, env.FIREBASE_API_KEY);
    if (!user) return json({error:"login necessário"}, 401, origin);
    const allowed = (env.ALLOWED_EMAILS || "").split(",").map(s => s.trim().toLowerCase()).filter(Boolean);
    if (allowed.length && !allowed.includes((user.email || "").toLowerCase())) return json({error:"conta não autorizada"}, 403, origin);

    let body; try { body = await req.json(); } catch { return json({error:"corpo inválido"}, 400, origin); }
    const prompt = String(body.prompt || "").slice(0, 3000), image = String(body.image || "");
    if (!prompt || !image || image.length > 2_000_000) return json({error:"foto ou instrução faltando"}, 400, origin);

    const client = new Anthropic({apiKey: env.ANTHROPIC_API_KEY});
    try {
      const msg = await client.beta.messages.create({
        model: "claude-opus-5-5",
        max_tokens: 4000,
        output_config: {effort: "low"},
        betas: ["server-side-fallback-2026-07-01"],
        fallbacks: "default",
        messages: [{role: "user", content: [
          {type: "image", source: {type: "base64", media_type: "image/jpeg", data: image}},
          {type: "text", text: prompt},
        ]}],
      });
      if (msg.stop_reason === "refusal") return json({nota:0, no_plano:false, porcao:"", vistos:[], comentario:"Não consegui avaliar essa foto."}, 200, origin);
      const text = msg.content.filter(b => b.type === "text").map(b => b.text).join("");
      return json(parseAnswer(text), 200, origin);
    } catch (e) {
      if (e instanceof Anthropic.RateLimitError) return json({error:"muitas fotos seguidas"}, 429, origin);
      console.error(e);
      return json({error:"falha ao avaliar"}, 502, origin);
    }
  }
};
