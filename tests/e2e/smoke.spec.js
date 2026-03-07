import { test, expect } from '@playwright/test';
import { spawn } from 'child_process';
import net from 'net';
import path from 'path';
import { fileURLToPath } from 'url';

function getRandomPort() {
  return new Promise((resolve) => {
    const srv = net.createServer();
    srv.listen(0, () => {
      const port = srv.address().port;
      srv.close(() => resolve(port));
    });
  });
}

const PROJECT_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

const EXPECTED_ERROR_PATTERNS = [
  /youtube/i,
  /YT/,
  /googleapis/i,
  /iframe/i,
  /www-widgetapi/i,
  /yt-player/i,
  /Failed to load resource/i,
  /ERR_NAME_NOT_RESOLVED/i,
  /ERR_CONNECTION_REFUSED/i,
];

function isExpectedError(msg) {
  return EXPECTED_ERROR_PATTERNS.some(p => p.test(msg));
}

test('snow-globe loads without JS errors', async ({ page }) => {
  const port = await getRandomPort();
  const server = spawn('python3', ['-m', 'http.server', String(port)], {
    cwd: PROJECT_DIR,
    stdio: 'ignore',
  });

  try {
    // Wait for server to start
    await new Promise(r => setTimeout(r, 1000));

    const errors = [];
    const warnings = [];

    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
      if (msg.type() === 'warning') warnings.push(msg.text());
    });
    page.on('pageerror', err => {
      errors.push(err.message);
    });

    await page.goto(`http://localhost:${port}/`, { waitUntil: 'domcontentloaded' });
    // Give app time to initialize
    await page.waitForTimeout(2000);

    // Key elements exist
    await expect(page.locator('#bump')).toBeAttached();
    await expect(page.locator('#block-label')).toBeAttached();
    await expect(page.locator('#clock')).toBeAttached();

    // Clock should have content (time)
    const clockText = await page.locator('#clock').textContent();
    expect(clockText.trim().length).toBeGreaterThan(0);

    // Filter out YouTube/network errors (expected in headless)
    const realErrors = errors.filter(e => !isExpectedError(e));

    if (warnings.length > 0) {
      console.log('Warnings:', warnings);
    }

    expect(realErrors).toEqual([]);
  } finally {
    server.kill();
  }
});
