// Funcao serverless do Vercel: proxy para a API da Liga Portugal.
//
// So existe por causa de CORS. A API da Liga responde 200 a qualquer pedido
// sem autenticacao, mas nao envia Access-Control-Allow-Origin, por isso o
// browser recusa a resposta quando o pedido parte do dominio do Vercel. Aqui o
// pedido e feito servidor-a-servidor, onde CORS nao se aplica, e a resposta e
// devolvida a app ja na mesma origem.
//
// A app funciona sem isto -- cai no data.json embutido no deploy. Esta funcao
// serve apenas para ver os dados ao vivo sem gerar novo deploy.

const BASE = "https://fantasy.ligaportugal.pt/api";
const UA =
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) " +
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36";

async function obter(url) {
    const resposta = await fetch(url, {
        headers: { "User-Agent": UA, Accept: "application/json" },
    });
    if (!resposta.ok) {
        throw new Error(`${url} devolveu HTTP ${resposta.status}`);
    }
    return resposta.json();
}

export default async function handler(req, res) {
    const idLiga = Number(req.query.liga) || 1406;

    try {
        // Classificacao (pagina a pagina, 50 equipas por pagina).
        const equipas = [];
        let liga = {};
        let pagina = 1;
        for (;;) {
            const dados = await obter(
                `${BASE}/leagues-classic/${idLiga}/standings/?page_standings=${pagina}`
            );
            liga = liga.id ? liga : dados.league || {};
            const bloco = dados.standings || {};
            equipas.push(...(bloco.results || []));
            if (!bloco.has_next) break;
            pagina += 1;
        }

        const bootstrap = await obter(`${BASE}/bootstrap-static/`);
        const eventos = bootstrap.events || [];

        // Historico de cada equipa, em paralelo: e daqui que vem o ponto a
        // ponto por jornada, que a classificacao sozinha nao da.
        const linhas = await Promise.all(
            equipas.map(async (equipa) => {
                const historico = await obter(`${BASE}/entry/${equipa.entry}/history/`);
                const jornadas = {};
                for (const g of historico.current || []) {
                    jornadas[g.event] = { pontos: g.points || 0, total: g.total_points || 0 };
                }
                return {
                    id_equipa: equipa.entry,
                    equipa: equipa.entry_name,
                    jogador: equipa.player_name,
                    posicao: equipa.rank,
                    total: equipa.total,
                    jornadas,
                };
            })
        );

        // Cache no CDN do Vercel: 5 min frescos, e ate 1h a servir o valor
        // antigo enquanto revalida. Evita martelar a API da Liga.
        res.setHeader("Cache-Control", "s-maxage=300, stale-while-revalidate=3600");
        res.status(200).json({
            id_liga: liga.id || idLiga,
            nome_liga: liga.name || "",
            atualizado_em: new Date().toISOString(),
            total_jornadas: eventos.length,
            jornadas_terminadas: eventos.filter((e) => e.finished).map((e) => e.id),
            equipas: linhas,
        });
    } catch (erro) {
        res.status(502).json({ erro: String(erro.message || erro) });
    }
}
