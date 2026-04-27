import path from 'path';
import fs from 'fs';
// Load .env from repo root explicitly (fallback for environments where dotenv may not load)
try {
  // __dirname is payments/circle_nanopay/src -> repo root is two levels up
  const envPath = path.resolve(__dirname, '../../.env');
  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf8');
    content.split(/\r?\n/).forEach(line => {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) return;
      const idx = trimmed.indexOf('=');
      if (idx === -1) return;
      const key = trimmed.slice(0, idx).trim();
      let val = trimmed.slice(idx + 1).trim();
      // Remove surrounding quotes if present
      if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
        val = val.slice(1, -1);
      }
      if (!process.env[key]) process.env[key] = val;
    });
    console.log(`◇ injected env (from ${path.relative(__dirname, '../../.env')})`);
  }
} catch (err) {
  console.warn('Failed to parse repo .env:', err);
}
import dotenv from 'dotenv';
dotenv.config({ path: path.resolve(__dirname, '../../.env') });
import express from 'express';
import bodyParser from 'body-parser';
import routes from './routes';

const app = express();
app.use(bodyParser.json());
app.use('/api', routes);

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Nanopay wrapper service listening on http://localhost:${PORT}`);
});
