const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8795;
const BASE = __dirname;

const MIME = {'.html':'text/html','.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.js':'application/javascript','.css':'text/css'};

const srv = http.createServer((req, res) => {
  let fp = path.join(BASE, decodeURIComponent(req.url));
  if (!fs.existsSync(fp)) { res.writeHead(404); res.end('Not found'); return; }
  const ext = path.extname(fp).toLowerCase();
  res.writeHead(200, {'Content-Type': MIME[ext] || 'application/octet-stream'});
  fs.createReadStream(fp).pipe(res);
});

srv.listen(PORT, () => console.log('Server on ' + PORT));
setTimeout(() => { srv.close(); process.exit(0); }, 300000);
