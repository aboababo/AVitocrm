/**
 * Simple build script using esbuild
 * Bundles ES6 modules into a single file for browser compatibility
 */

import * as esbuild from 'esbuild';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const isWatch = process.argv.includes('--watch');

const buildOptions = {
    entryPoints: ['backend/static/js/chats/main.js'],
    bundle: true,
    outfile: 'backend/static/js/chats/chats.bundle.js',
    format: 'iife',
    target: ['es2015'],
    sourcemap: true,
    minify: false, // Set to true for production
    define: {
        'process.env.NODE_ENV': '"production"'
    },
    loader: {
        '.js': 'jsx'
    },
    banner: {
        js: '/* Built with esbuild */'
    }
};

async function build() {
    try {
        if (isWatch) {
            const ctx = await esbuild.context(buildOptions);
            await ctx.watch();
            console.log('👀 Watching for changes...');
        } else {
            await esbuild.build(buildOptions);
            console.log('✅ Build completed successfully!');
        }
    } catch (error) {
        console.error('❌ Build failed:', error);
        process.exit(1);
    }
}

build();

