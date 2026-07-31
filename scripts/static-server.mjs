import { createReadStream, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, resolve } from "node:path";
import { createGzip } from "node:zlib";

const port = Number.parseInt(process.argv[2] || "4173", 10);
const root = resolve(".");
const types = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};
const compressible = new Set([".css", ".html", ".js", ".json", ".svg"]);

createServer((request, response) => {
  const pathname = new URL(request.url, `http://${request.headers.host}`).pathname;
  const requested = pathname === "/" ? "/index.html" : pathname;
  const path = resolve(root, `.${requested}`);
  if (!path.startsWith(`${root}/`)) {
    response.writeHead(403).end();
    return;
  }

  try {
    const size = statSync(path).size;
    const extension = extname(path);
    const headers = {
      "Content-Type": types[extension] || "application/octet-stream",
      "Cache-Control": "no-store",
      Vary: "Accept-Encoding",
    };
    const shouldGzip =
      size > 1024 &&
      compressible.has(extension) &&
      request.headers["accept-encoding"]?.includes("gzip");
    if (shouldGzip) headers["Content-Encoding"] = "gzip";
    response.writeHead(200, headers);
    const stream = createReadStream(path);
    if (shouldGzip) stream.pipe(createGzip()).pipe(response);
    else stream.pipe(response);
  } catch {
    response.writeHead(404).end();
  }
}).listen(port, "127.0.0.1");
