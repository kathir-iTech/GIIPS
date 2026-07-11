import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';

const env = loadEnv('', process.cwd(), '');
if (!env.VITE_API_BASE_URL) {
    throw new Error("VITE_API_BASE_URL is required but not set. Define it in your .env file.");
}

export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': '/src',
            'framer-motion': '/node_modules/framer-motion/dist/cjs/index.js',
            'react-plotly.js': '/node_modules/react-plotly.js/dist/index.cjs'
        }
    }
});
