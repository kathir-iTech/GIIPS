import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';
import path from 'path';

const env = loadEnv('', process.cwd(), '');
if (!env.VITE_API_BASE_URL) {
    throw new Error("VITE_API_BASE_URL is required but not set. Define it in your .env file.");
}

// CJS fallbacks for packages with corrupted ESM builds on this machine
function cjsResolve(name) {
    try { return require.resolve(name); }
    catch { return null; }
}

const fmEntry = cjsResolve('framer-motion');
const rpEntry = cjsResolve('react-plotly.js');

export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': '/src',
            ...(fmEntry ? { 'framer-motion': fmEntry } : {}),
            ...(rpEntry ? { 'react-plotly.js': rpEntry } : {})
        }
    }
});
