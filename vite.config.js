import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';
import path from 'path';

const env = loadEnv('', process.cwd(), '');
if (!env.VITE_API_BASE_URL) {
    throw new Error("VITE_API_BASE_URL is required but not set. Define it in your .env file.");
}

// CJS fallback – react-plotly.js ESM dist/import path doesn't resolve
function cjsResolve(name) {
    try { return require.resolve(name); }
    catch { return null; }
}

const rpEntry = cjsResolve('react-plotly.js');

export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': '/src',
            ...(rpEntry ? { 'react-plotly.js': rpEntry } : {})
        }
    }
});
