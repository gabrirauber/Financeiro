import http from 'node:http';

const upstream = new URL(process.env.DEV_API_URL || 'https://financeiro-production-51f2.up.railway.app');
const allowedOrigins = new Set(['http://localhost:8081', 'http://127.0.0.1:8081']);

http.createServer(async (request, response) => {
  if (!request.url?.startsWith('/') || request.url.startsWith('//')) {
    response.writeHead(400).end();
    return;
  }
  const origin = request.headers.origin;
  if (origin && !allowedOrigins.has(origin)) {
    response.writeHead(403).end();
    return;
  }
  if (origin) response.setHeader('Access-Control-Allow-Origin', origin);
  response.setHeader('Vary', 'Origin');
  response.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS');
  response.setHeader('Access-Control-Allow-Headers', 'Accept, Content-Type, Authorization');
  if (request.method === 'OPTIONS') {
    response.writeHead(204).end();
    return;
  }

  try {
    const body = ['GET', 'HEAD'].includes(request.method) ? undefined : await new Promise((resolve, reject) => {
      const chunks = [];
      request.on('data', chunk => chunks.push(chunk));
      request.on('end', () => resolve(Buffer.concat(chunks)));
      request.on('error', reject);
    });
    const target = new URL(request.url, upstream);
    const remote = await fetch(target, {
      method: request.method,
      headers: {
        ...(request.headers.accept ? { Accept: request.headers.accept } : {}),
        ...(request.headers['content-type'] ? { 'Content-Type': request.headers['content-type'] } : {}),
        ...(request.headers.authorization ? { Authorization: request.headers.authorization } : {}),
      },
      body,
    });
    for (const name of ['content-type', 'content-disposition']) {
      const value = remote.headers.get(name);
      if (value) response.setHeader(name, value);
    }
    response.writeHead(remote.status).end(Buffer.from(await remote.arrayBuffer()));
  } catch {
    response.writeHead(502, { 'Content-Type': 'application/json' })
      .end(JSON.stringify({ detail: 'Servidor indisponível. Tente novamente.' }));
  }
}).listen(8000, '127.0.0.1', () => {
  process.stdout.write('API local disponível em http://localhost:8000\n');
});
