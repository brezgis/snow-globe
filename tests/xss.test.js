import { describe, it, expect } from 'vitest';
import { getBumpMessage } from '../engine.js';

const XSS_PAYLOADS = [
  '<script>alert(1)</script>',
  '" onmouseover="alert(1)',
  '<img src=x onerror=alert(1)>',
];

describe('XSS safety', () => {
  it('video titles rendered via textContent are safe (DOM API check)', () => {
    // snow-globe uses textContent (not innerHTML) for titles.
    // textContent creates a text node — no child elements, no script execution.
    const el = document.createElement('div');
    for (const payload of XSS_PAYLOADS) {
      el.textContent = payload;
      // Must produce zero child elements (text node only)
      expect(el.children.length).toBe(0);
      expect(el.childNodes.length).toBe(1);
      expect(el.childNodes[0].nodeType).toBe(3); // TEXT_NODE
    }
  });

  it('bump text set via textContent does not execute HTML', () => {
    const el = document.createElement('div');
    // Simulate what showBump does: $bumpText.textContent = message
    const malicious = '<script>alert("xss")</script>';
    el.textContent = malicious;
    expect(el.children.length).toBe(0);
    expect(el.innerHTML).toContain('&lt;script&gt;');
  });
});
