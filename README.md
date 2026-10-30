# Jornada Leve

Jogo de hábitos para emagrecer, como app instalável (PWA): refeições do cardápio, água, jejum e exercício viram pontos, elos de Ferro a Desafiante, conquistas, refeição livre e ranking com amigos.

## Arquivos

| Arquivo | O que é |
|---|---|
| `index.src.html` | A página do jogo (mesma versão publicada no Claude). Edite aqui. |
| `build.py` | Gera `index.html` a partir de `index.src.html`, trocando o armazenamento do Claude pelo Firebase. Rode `python3 build.py` depois de editar. |
| `index.html` | O app. É ele que o GitHub Pages publica. |
| `config.js` | Dados do Firebase e endereço da avaliação de fotos. |
| `manifest.webmanifest`, `sw.js`, `icons/` | O que torna a página instalável e faz abrir sem internet. |
| `firestore.rules` | Regras de acesso do banco: cada pessoa só lê os próprios dados; o ranking é por liga. |
| `worker/` | Serviço que avalia a foto da refeição com a API do Claude (Cloudflare Workers). |

## Configurar o Firebase (login, nuvem e ranking)

1. Em https://console.firebase.google.com, clique em **Adicionar projeto**, dê o nome `jornada-leve` e pode desligar o Google Analytics.
2. **Criação > Authentication > Vamos começar**. Em **Método de login**, ative o **Google**.
3. Ainda em Authentication, na aba **Configurações > Domínios autorizados**, adicione `guibgf.github.io`.
4. **Criação > Firestore Database > Criar banco de dados**. Escolha o **modo de produção** e o local `southamerica-east1` (São Paulo).
5. Na aba **Regras** do Firestore, apague o que estiver lá, cole o conteúdo de `firestore.rules` e clique em **Publicar**.
6. Na engrenagem **Configurações do projeto > Seus apps**, clique no ícone **Web** (`</>`), dê um apelido e registre. Copie os valores `apiKey`, `authDomain`, `projectId` e `appId` para `config.js`.

Esses valores não são senhas: quem protege os dados são as regras do passo 5.

## Avaliação de fotos (opcional)

Precisa de uma chave da API do Claude (https://console.anthropic.com, cobrança por uso) e de uma conta grátis no Cloudflare.

```bash
cd worker
npm install
npx wrangler login
npx wrangler secret put ANTHROPIC_API_KEY
npx wrangler deploy --var FIREBASE_API_KEY:<apiKey do Firebase> --var ALLOWED_ORIGIN:https://guibgf.github.io --var ALLOWED_EMAILS:seu@email.com,amigo@email.com
```

Coloque o endereço que o deploy mostrar (`https://jornada-leve-foto.<sua-conta>.workers.dev`) em `photoApi`, no `config.js`. `ALLOWED_EMAILS` limita quem pode gastar com fotos; deixe vazio para liberar todo mundo que entrar com o Google.

## Instalar no celular

- **Android (Chrome):** abra o site, toque no menu ⋮ e em **Instalar app**.
- **iPhone (Safari):** abra o site, toque em Compartilhar e em **Adicionar à Tela de Início**.
