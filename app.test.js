/**
 * @vitest-environment jsdom
 */
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import { JSDOM } from 'jsdom';

// Read HTML and JS source files once
const htmlHtml = fs.readFileSync(path.resolve(__dirname, './index.html'), 'utf8');
const scriptJs = fs.readFileSync(path.resolve(__dirname, './app.js'), 'utf8');

describe('Stock Value Table Dashboard UI', () => {
  let dom;
  let customWindow;
  let customDocument;
  let mockLocalStorage;
  let mockFetch;
  let originalGlobalSetTimeout;

  beforeEach(() => {
    // 1. Enable fake timers to block unmanaged background setTimeouts
    vi.useFakeTimers();

    // 2. Instantiate a fresh JSDOM for perfect test isolation
    dom = new JSDOM(htmlHtml, { url: "http://localhost" });
    customWindow = dom.window;
    customDocument = dom.window.document;

    // Remove the auto-loading script tag from JSDOM to prevent double execution
    const autoScript = customDocument.querySelector('script[src="app.js"]');
    if (autoScript) {
      autoScript.remove();
    }

    // Intercept global setTimeout to block huge background theme timers (> 10s)
    originalGlobalSetTimeout = global.setTimeout;
    const mockSetTimeout = vi.fn().mockImplementation((callback, delay, ...args) => {
      if (delay > 10000) {
        return 999999; // Return dummy timer ID for theme transitions
      }
      return originalGlobalSetTimeout(callback, delay, ...args);
    });
    global.setTimeout = mockSetTimeout;
    globalThis.setTimeout = mockSetTimeout;

    // Propagate variables to global scope so that libraries find them
    global.window = customWindow;
    global.document = customDocument;

    // 3. Setup Fetch Mock
    mockFetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          {
            gicode: "A005930",
            name: "삼성전자",
            category: "전기전자",
            current_price: "70,000",
            market_cap: "4,200,000",
            years: ["2025", "2026", "2027", "2028"],
            PBR: ["1.2", "1.1", "1.0", "0.9"],
            PER: ["10.5", "9.2", "8.5", "7.8"],
            EPS: ["6,000", "7,500", "8,000", "9,000"],
            영업이익: ["100,000", "120,000", "140,000", "150,000"]
          },
          {
            gicode: "A005380",
            name: "현대차",
            category: "자동차",
            current_price: "200,000",
            market_cap: "420,000",
            years: ["2025", "2026", "2027", "2028"],
            PBR: ["0.6", "0.5", "0.4", "0.3"],
            PER: ["5.5", "4.8", "4.2", "3.9"],
            EPS: ["35,000", "41,000", "46,000", "50,000"],
            영업이익: ["15,000", "18,000", "20,000", "22,000"]
          }
        ])
      })
    );
    global.fetch = mockFetch;
    customWindow.fetch = mockFetch;
    globalThis.fetch = mockFetch;

    // 4. Setup LocalStorage Mock
    const store = {};
    mockLocalStorage = {
      getItem: vi.fn((key) => store[key] || null),
      setItem: vi.fn((key, value) => { store[key] = String(value); }),
      removeItem: vi.fn((key) => { delete store[key]; }),
      clear: vi.fn(() => { for (const key in store) delete store[key]; })
    };
    Object.defineProperty(customWindow, 'localStorage', {
      value: mockLocalStorage,
      writable: true,
      configurable: true
    });
    global.localStorage = mockLocalStorage;
    globalThis.localStorage = mockLocalStorage;

    // 5. Execute app.js code
    const runScript = new Function('window', 'document', scriptJs);
    runScript(customWindow, customDocument);

    // We do not manually dispatch DOMContentLoaded here, JSDOM will fire it once parsed.
  });

  afterEach(() => {
    // Clean up timers to prevent memory leaks and flaky overrides
    vi.clearAllTimers();
    vi.useRealTimers();
    if (originalGlobalSetTimeout) {
      global.setTimeout = originalGlobalSetTimeout;
      globalThis.setTimeout = originalGlobalSetTimeout;
    }
  });

  it('renders tables grouped by category with correct headers', async () => {
    // Wait for the async fetch rendering to finish by checking query selector assertion
    await vi.waitFor(() => {
      const h2s = customDocument.querySelectorAll('h2.category-title');
      expect(h2s.length).toBe(2);
    });

    const categoryTitles = Array.from(customDocument.querySelectorAll('h2.category-title')).map(el => el.textContent);
    expect(categoryTitles).toContain('전기전자');
    expect(categoryTitles).toContain('자동차');

    const tables = customDocument.querySelectorAll('table');
    expect(tables.length).toBe(2);

    const firstTable = tables[0];
    expect(firstTable.innerHTML).toContain('삼성전자');
    expect(firstTable.innerHTML).toContain('A005930');
    expect(firstTable.innerHTML).toContain('70,000');
  });

  it('toggles accordion details on row click and keyboard enter', async () => {
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(2);
    });

    const mainRow = customDocument.querySelector('#main-row-A005930');
    const detailRow = customDocument.querySelector('#detail-row-A005930');
    const accordion = customDocument.querySelector('#accordion-A005930');

    expect(detailRow.style.display).toBe('none');
    expect(mainRow.getAttribute('aria-expanded')).toBe('false');

    // Expand
    mainRow.click();
    expect(detailRow.style.display).toBe('table-row');
    expect(mainRow.getAttribute('aria-expanded')).toBe('true');
    expect(accordion.classList.contains('expanded')).toBe(true);

    // Collapse (triggers 300ms setTimeout transition)
    mainRow.click();
    
    // Fast-forward fake timers by 350ms to trigger the transition cleanup
    vi.advanceTimersByTime(350);

    expect(detailRow.style.display).toBe('none');
    expect(mainRow.getAttribute('aria-expanded')).toBe('false');

    // Expand via Keyboard (Enter key)
    const enterEvent = new customWindow.KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
    mainRow.dispatchEvent(enterEvent);
    expect(detailRow.style.display).toBe('table-row');
    expect(mainRow.getAttribute('aria-expanded')).toBe('true');
  });

  it('sorts columns when header is clicked', async () => {
    // Re-mock fetch to return two stocks under the same category to test sorting
    const mockSortedFetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          {
            gicode: "A005930",
            name: "삼성전자",
            category: "전기전자",
            current_price: "70,000",
            market_cap: "4,200,000",
            years: ["2025", "2026", "2027", "2028"],
            PBR: ["1.2", "1.1", "1.0", "0.9"],
            PER: ["10.5", "9.2", "8.5", "7.8"],
            EPS: ["6000", "7500", "8000", "9000"],
            영업이익: ["100000", "120000", "140000", "150000"]
          },
          {
            gicode: "A000660",
            name: "SK하이닉스",
            category: "전기전자",
            current_price: "150,000",
            market_cap: "1,000,000",
            years: ["2025", "2026", "2027", "2028"],
            PBR: ["1.5", "1.4", "1.3", "1.2"],
            PER: ["12.5", "11.2", "10.5", "9.8"],
            EPS: ["12000", "14500", "16000", "18000"],
            영업이익: ["30000", "35000", "40000", "45000"]
          }
        ])
      })
    );
    global.fetch = mockSortedFetch;
    customWindow.fetch = mockSortedFetch;
    globalThis.fetch = mockSortedFetch;

    // Reload script via DOMContentLoaded event
    customDocument.dispatchEvent(new customWindow.Event('DOMContentLoaded'));

    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(2);
    });

    let rows = customDocument.querySelectorAll('.main-row');
    expect(rows[0].querySelector('span').textContent).toBe('삼성전자');
    expect(rows[1].querySelector('span').textContent).toBe('SK하이닉스');

    const th = customDocument.querySelector('th.sortable[data-category="전기전자"]');
    th.click();

    rows = customDocument.querySelectorAll('.main-row');
    expect(rows[0].querySelector('span').textContent).toBe('SK하이닉스');
    expect(rows[1].querySelector('span').textContent).toBe('삼성전자');
  });

  it('updates theme using toggle button and system theme option', async () => {
    // Initially, fetch loading starts
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(2);
    });

    const checkbox = customDocument.querySelector('#system-theme-checkbox');
    const toggle = customDocument.querySelector('#theme-toggle');

    // System theme enabled by default
    expect(checkbox.checked).toBe(true);
    expect(toggle.classList.contains('disabled')).toBe(true);

    // Disable system theme checkbox
    checkbox.checked = false;
    checkbox.dispatchEvent(new customWindow.Event('change'));

    expect(toggle.classList.contains('disabled')).toBe(false);
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('system-theme-enabled', 'false');

    // Click toggle to switch manual theme
    const currentTheme = customDocument.documentElement.getAttribute('data-theme') || 'light';
    const expectedNewTheme = currentTheme === 'dark' ? 'light' : 'dark';

    toggle.click();
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe(expectedNewTheme);
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('manual-theme', expectedNewTheme);
  });
});
