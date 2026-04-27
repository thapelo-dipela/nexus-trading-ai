"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
// Load .env from repo root explicitly (fallback for environments where dotenv may not load)
try {
    // __dirname is payments/circle_nanopay/src -> repo root is two levels up
    const envPath = path_1.default.resolve(__dirname, '../../.env');
    if (fs_1.default.existsSync(envPath)) {
        const content = fs_1.default.readFileSync(envPath, 'utf8');
        content.split(/\r?\n/).forEach(line => {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#'))
                return;
            const idx = trimmed.indexOf('=');
            if (idx === -1)
                return;
            const key = trimmed.slice(0, idx).trim();
            let val = trimmed.slice(idx + 1).trim();
            // Remove surrounding quotes if present
            if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
                val = val.slice(1, -1);
            }
            if (!process.env[key])
                process.env[key] = val;
        });
        console.log(`◇ injected env (from ${path_1.default.relative(__dirname, '../../.env')})`);
    }
}
catch (err) {
    console.warn('Failed to parse repo .env:', err);
}
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config({ path: path_1.default.resolve(__dirname, '../../.env') });
const express_1 = __importDefault(require("express"));
const body_parser_1 = __importDefault(require("body-parser"));
const routes_1 = __importDefault(require("./routes"));
const app = (0, express_1.default)();
app.use(body_parser_1.default.json());
app.use('/api', routes_1.default);
const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
    console.log(`Nanopay wrapper service listening on http://localhost:${PORT}`);
});
