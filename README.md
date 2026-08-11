# Liga dos Últimos — Classificação por Jornada

Web app estática que mostra a classificação da liga jornada a jornada, no
formato da folha de cálculo: equipas nas linhas, J1 a J34 nas colunas, total à
direita.

Tudo o que é preciso para o deploy está dentro desta pasta.

## Deploy no Vercel

```bash
cd external
vercel                # pré-visualização
vercel --prod         # produção
```

Ou liga o repositório no painel do Vercel e define **`external`** como *Root
Directory*. Não é preciso build — não há bundler, nem dependências, nem passo
de compilação.

## De onde vêm os dados

Os dados são da API pública da Fantasy Liga Portugal. **Não precisa de
autenticação** — nem cookie de sessão, nem token, nem sequer `User-Agent` de
browser neste endpoint (foi testado).

O URL que se vê no browser,
`fantasy.ligaportugal.pt/leagues/1406/standings/c`, **não serve para extrair
nada**: é uma aplicação React que devolve sempre a mesma casca de ~4 KB com um
`<div id="root">` vazio. Zero dados no HTML. Os dados vêm de um XHR por baixo:

```
/api/leagues-classic/1406/standings/?page_standings=1   # classificação
/api/entry/<id_equipa>/history/                         # pontos por jornada
/api/bootstrap-static/                                  # quantas jornadas tem a época
```

(o `/c` no fim do URL do browser é o tipo de pontuação, *classic*, não um
parâmetro do endpoint.)

São precisos os três: a classificação só traz o **total acumulado**, por isso
os pontos de cada jornada têm de vir do histórico individual de cada equipa —
um pedido por equipa.

## O problema do CORS, e como está resolvido

A API da Liga responde 200 a qualquer pedido, mas **não envia
`Access-Control-Allow-Origin`**. Isso significa que uma página alojada no
Vercel *não pode* chamar a API diretamente do browser — o browser bloqueia a
resposta. Verificado: sem esse cabeçalho, a tabela apareceria sempre vazia em
produção.

A app resolve isto por duas vias, e é de propósito que são duas:

1. **`data.json` embutido no deploy** — carregado da mesma origem, portanto
   sem CORS. É o que a página lê ao abrir. Funciona sempre, mesmo que a função
   serverless falhe ou nem exista.
2. **`api/standings.js`, função serverless do Vercel** — faz o pedido
   servidor-a-servidor, onde CORS não se aplica, e devolve o resultado já na
   mesma origem. É o botão **"Atualizar ao vivo"**.

Se o refresh ao vivo falhar, a página mantém o que já estava e mostra um aviso,
em vez de ficar em branco.

## Atualizar os dados

Os dados embutidos são de um momento fixo. Para os regenerar depois de cada
jornada:

```bash
cd external
python3 atualizar.py          # liga 1406 (por omissão)
python3 atualizar.py 1406     # ou outra liga qualquer
```

Escreve o `data.json` e depois é só fazer novo deploy. Só precisa do Python 3 —
sem dependências externas, usa `urllib` da biblioteca padrão.

Alternativa: não regenerar nada e usar o botão "Atualizar ao vivo", que vai
buscar dados frescos pela função serverless (com cache de 5 minutos no CDN,
para não martelar o servidor da Liga).

## O pote

Regra: **em cada jornada, os 4 piores classificados põem 1 € no pote.**

Na tabela, esses 4 ficam a **vermelho claro**. O pior de todos leva o vermelho
forte por cima (é sempre um dos 4 que paga), e o melhor da jornada leva verde.

Por baixo aparece o **Pote Acumulado** e um gráfico com a contribuição de cada
um, ordenado de quem mais pagou para quem menos pagou.

**Empates:** pagam sempre exatamente 4 por jornada. Se houver empate na
pontuação, desempata pelo total acumulado da época — quem tem menos total fica
mais abaixo e paga primeiro. Sem esta segunda chave, a ordem dependeria da
ordem de chegada dos dados e o pote mudava sozinho entre atualizações.

O gráfico está escalado ao **máximo possível** (1 € por jornada jogada), não ao
maior valor observado. É de propósito: enquanto só houver uma jornada está toda
a gente empatada a 1 €, e uma escala relativa mostraria quatro barras cheias a
dar a ideia errada de que alguém lidera. Assim, barra cheia significa "pagou em
todas as jornadas" — e as barras vão-se diferenciando à medida que a época
avança.

Para mudar as regras, edita as constantes no topo do `<script>` em
`index.html`:

```js
const QUANTOS_PAGAM = 4;        // quantos pagam por jornada
const EUROS_POR_JORNADA = 1;    // quanto paga cada um
```

## A interface

- **Pontos por jornada** / **Total acumulado** — alterna o que cada célula
  mostra: os pontos daquela jornada, ou o acumulado até ali.
- **Verde** é a melhor pontuação da jornada, **vermelho** a pior, **vermelho
  claro** os 4 que pagam.
- O gráfico tem um **"Ver como tabela"** para quem não distingue as cores.
- A tua equipa (id `22441`) fica destacada a amarelo. Para mudar, edita a
  constante `EU` no topo do `<script>` em `index.html`.
- A coluna das equipas fica fixa ao rolar na horizontal — necessário, porque 34
  jornadas não cabem no ecrã. A tabela rola dentro do painel; a página nunca
  rola na horizontal.
- Tema claro e escuro automáticos, conforme o sistema.
- Última linha soma todos os participantes por jornada.

## Ficheiros

```
external/
├── index.html          a app (HTML + CSS + JS, sem dependências)
├── data.json           dados embutidos, gerados por atualizar.py
├── atualizar.py        regenera o data.json a partir da API da Liga
├── api/
│   └── standings.js    função serverless: proxy para contornar o CORS
├── vercel.json         configuração da função
└── package.json        marca o projeto como ESM
```

## Estado atual dos dados

Época de 34 jornadas, **1 jogada** (J1). As colunas J2 a J34 aparecem vazias
por isso mesmo — vão-se preenchendo à medida que a época avança, sem ser
preciso mexer no código.

Nota: a API devolve `last_rank = 0` para toda a gente enquanto só houver uma
jornada; não é bug, é simplesmente não haver ainda posição anterior.
