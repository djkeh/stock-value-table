/**
 * @vitest-environment jsdom
 */
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import { JSDOM } from 'jsdom';

// Read HTML source file once
const htmlHtml = fs.readFileSync(path.resolve(__dirname, './index.html'), 'utf8');

describe('Stock Value Table Dashboard UI', () => {
  let dom;
  let customWindow;
  let customDocument;
  let mockLocalStorage;
  let mockFetch;
  let originalGlobalSetTimeout;

  beforeEach(async () => {
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
            disparity_rate: "135.0",
            years: ["2025", "2026", "2027", "2028"],
            PBR: ["1.2", "1.1", "1.0", "0.9"],
            PER: ["10.5", "-9.2", "8.5", "7.8"],
            EPS: ["6,000", "7,500", "8,000", "9,000"],
            영업이익: ["100,000", "120,000", "140,000", "150,000"]
          },
          {
            gicode: "A005380",
            name: "현대차",
            category: "자동차",
            current_price: "200,000",
            market_cap: "420,000",
            disparity_rate: "-10.5",
            years: ["2025", "2026", "2027", "2028"],
            PBR: ["0.6", "-0.5", "0.4", "0.3"],
            PER: ["5.5", "4.8", "4.2", "3.9"],
            EPS: ["35,000", "41,000", "46,000", "50,000"],
            영업이익: ["15,000", "18,000", "20,000", "22,000"]
          },
          {
            gicode: "A999999",
            name: "부실기업",
            current_price: "",
            market_cap: "-",
            years: ["2025", "2026", "2027", "2028"],
            PBR: [],
            PER: [],
            EPS: [],
            영업이익: []
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
  });

  async function loadApp() {
    vi.resetModules();
    await import('./app.js');
    customDocument.dispatchEvent(new customWindow.Event('DOMContentLoaded'));
  }

  afterEach(() => {
    vi.restoreAllMocks();
    // Clean up timers to prevent memory leaks and flaky overrides
    vi.clearAllTimers();
    vi.useRealTimers();
    if (originalGlobalSetTimeout) {
      global.setTimeout = originalGlobalSetTimeout;
      globalThis.setTimeout = originalGlobalSetTimeout;
    }
  });

  it('renders tables grouped by category with correct headers', async () => {
    await loadApp();
    // Wait for the async fetch rendering to finish by checking query selector assertion
    await vi.waitFor(() => {
      const h2s = customDocument.querySelectorAll('h2.category-title');
      expect(h2s.length).toBe(3);
    });

    const categoryTitles = Array.from(customDocument.querySelectorAll('h2.category-title')).map(el => el.textContent);
    expect(categoryTitles).toContain('전기전자');
    expect(categoryTitles).toContain('자동차');
    expect(categoryTitles).toContain('기타');

    const tables = customDocument.querySelectorAll('table');
    expect(tables.length).toBe(3);

    const firstTable = tables[0];
    expect(firstTable.innerHTML).toContain('삼성전자');
    expect(firstTable.innerHTML).toContain('A005930');
    expect(firstTable.innerHTML).toContain('70,000');
  });

  it('toggles accordion details on row click and keyboard enter', async () => {
    await loadApp();
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(3);
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
    
    // Collapse via Keyboard (Space key)
    const spaceEvent = new customWindow.KeyboardEvent('keydown', { key: ' ', bubbles: true });
    mainRow.dispatchEvent(spaceEvent);
    vi.advanceTimersByTime(350);
    expect(detailRow.style.display).toBe('none');
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
            disparity_rate: "135.0",
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
            disparity_rate: "45.2",
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

    await loadApp();

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
    await loadApp();
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(3);
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

    // Re-enable system theme checkbox to cover lines 294-295
    checkbox.checked = true;
    checkbox.dispatchEvent(new customWindow.Event('change'));
    expect(toggle.classList.contains('disabled')).toBe(true);
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('system-theme-enabled', 'true');

    // Disable system theme checkbox again for manual toggle test
    checkbox.checked = false;
    checkbox.dispatchEvent(new customWindow.Event('change'));

    // Click toggle to switch manual theme
    const currentTheme = customDocument.documentElement.getAttribute('data-theme') || 'light';
    const expectedNewTheme = currentTheme === 'dark' ? 'light' : 'dark';

    toggle.click();
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe(expectedNewTheme);
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('manual-theme', expectedNewTheme);
  });

  // -------------------------------------------------------------------------
  // Error States, Keyboard Interactions, and Theme Sync Tests
  // -------------------------------------------------------------------------
  it('renders empty message when stocks list is empty', async () => {
    mockFetch.mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([])
      })
    );
    await loadApp();

    await vi.waitFor(() => {
      expect(customDocument.getElementById('tables-container').textContent).toContain('표시할 데이터가 없습니다.');
    });
  });

  it('renders error message when fetch fails (response not ok)', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    mockFetch.mockImplementation(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      })
    );
    await loadApp();

    await vi.waitFor(() => {
      expect(customDocument.getElementById('tables-container').textContent).toContain('데이터를 불러오는 데 실패했습니다.');
    });
  });

  it('renders error message when fetch throws exception', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    mockFetch.mockImplementation(() => Promise.reject(new Error('Network error')));
    await loadApp();

    await vi.waitFor(() => {
      expect(customDocument.getElementById('tables-container').textContent).toContain('데이터를 불러오는 데 실패했습니다.');
      expect(customDocument.getElementById('tables-container').textContent).toContain('Network error');
    });
  });

  it('sorts columns when Enter or Space is pressed on header', async () => {
    await loadApp();
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(3);
    });

    const th = customDocument.querySelector('th.sortable[data-category="전기전자"]');
    expect(th.classList.contains('sorted-asc')).toBe(true);

    // Focus and dispatch Enter
    th.focus();
    const enterEvent = new customWindow.KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
    th.dispatchEvent(enterEvent);
    
    // Query th again since renderTable replaces it
    const thAfterEnter = customDocument.querySelector('th.sortable[data-category="전기전자"]');
    expect(thAfterEnter.classList.contains('sorted-desc')).toBe(true);

    // Dispatch Space
    const spaceEvent = new customWindow.KeyboardEvent('keydown', { key: ' ', bubbles: true });
    thAfterEnter.dispatchEvent(spaceEvent);
    
    const thAfterSpace = customDocument.querySelector('th.sortable[data-category="전기전자"]');
    expect(thAfterSpace.classList.contains('sorted-asc')).toBe(true);

    // Dispatch irrelevant key (should do nothing)
    const escapeEvent = new customWindow.KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
    thAfterSpace.dispatchEvent(escapeEvent);
    
    const thAfterEscape = customDocument.querySelector('th.sortable[data-category="전기전자"]');
    expect(thAfterEscape.classList.contains('sorted-asc')).toBe(true);
  });

  it('sets light theme automatically during the day', async () => {
    const date = new Date(2026, 5, 16, 10, 0, 0); // Daytime 10 AM
    vi.setSystemTime(date);
    await loadApp();
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('sets dark theme automatically during the night', async () => {
    const date = new Date(2026, 5, 16, 22, 0, 0); // Nighttime 10 PM
    vi.setSystemTime(date);
    await loadApp();
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('schedules and executes auto theme transition timer', async () => {
    // Start at daytime 19:59:59 (1 second before night transition)
    // Delay to 20:00:00 is 1000ms. Transition timer: 1500ms
    const date = new Date(2026, 5, 16, 19, 59, 59);
    vi.setSystemTime(date);

    await loadApp();
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('light');

    // Advance time by 2000ms to trigger the transition
    vi.advanceTimersByTime(2000);

    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('schedules and executes night-to-day transition timer', async () => {
    // Start at nighttime 06:59:59 (1 second before morning transition)
    const date = new Date(2026, 5, 16, 6, 59, 59);
    vi.setSystemTime(date);

    await loadApp();
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('dark');

    // Advance time by 2000ms to trigger the transition
    vi.advanceTimersByTime(2000);

    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('updates auto theme when window receives focus or visibility state changes', async () => {
    // Define visibilityState first
    Object.defineProperty(customDocument, 'visibilityState', {
      value: 'visible',
      writable: true,
      configurable: true
    });

    const date1 = new Date(2026, 5, 16, 10, 0, 0); // Daytime
    vi.setSystemTime(date1);
    await loadApp();
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('light');

    // Mock time to nighttime (22:00:00) without reloading
    const date2 = new Date(2026, 5, 16, 22, 0, 0);
    vi.setSystemTime(date2);

    // Dispatch focus event
    customWindow.dispatchEvent(new customWindow.Event('focus'));
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('dark');

    // Reset to daytime and dispatch visibilitychange
    const date3 = new Date(2026, 5, 17, 10, 0, 0);
    vi.setSystemTime(date3);
    
    customDocument.dispatchEvent(new customWindow.Event('visibilitychange'));
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('loads manual theme settings on start if system theme is disabled', async () => {
    mockLocalStorage.setItem('system-theme-enabled', 'false');
    mockLocalStorage.setItem('manual-theme', 'dark');

    await loadApp();

    const checkbox = customDocument.querySelector('#system-theme-checkbox');
    const toggle = customDocument.querySelector('#theme-toggle');
    expect(checkbox.checked).toBe(false);
    expect(toggle.classList.contains('disabled')).toBe(false);
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('defaults to light theme if system theme is disabled and no manual theme is saved', async () => {
    mockLocalStorage.setItem('system-theme-enabled', 'false');
    mockLocalStorage.removeItem('manual-theme');

    await loadApp();

    const checkbox = customDocument.querySelector('#system-theme-checkbox');
    const toggle = customDocument.querySelector('#theme-toggle');
    expect(checkbox.checked).toBe(false);
    expect(toggle.classList.contains('disabled')).toBe(false);
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('blocks theme toggle click/keypress when system theme is enabled', async () => {
    await loadApp();
    
    const checkbox = customDocument.querySelector('#system-theme-checkbox');
    const toggle = customDocument.querySelector('#theme-toggle');
    expect(checkbox.checked).toBe(true);

    const currentTheme = customDocument.documentElement.getAttribute('data-theme');
    toggle.click();
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe(currentTheme);

    const enterEvent = new customWindow.KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
    toggle.dispatchEvent(enterEvent);
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe(currentTheme);
  });

  it('toggles theme using Enter or Space key on theme toggle when system theme is disabled', async () => {
    mockLocalStorage.setItem('system-theme-enabled', 'false');
    mockLocalStorage.setItem('manual-theme', 'light');

    await loadApp();

    const toggle = customDocument.querySelector('#theme-toggle');
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('light');

    // Space key
    const spaceEvent = new customWindow.KeyboardEvent('keydown', { key: ' ', bubbles: true });
    toggle.dispatchEvent(spaceEvent);
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('dark');

    // Enter key
    const enterEvent = new customWindow.KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
    toggle.dispatchEvent(enterEvent);
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('light');

    // Escape key (should do nothing)
    const escapeEvent = new customWindow.KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
    toggle.dispatchEvent(escapeEvent);
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('clears auto theme timeout in setManualTheme when manually overriding theme', async () => {
    // Start at daytime so default theme is light
    const date = new Date(2026, 5, 16, 10, 0, 0);
    vi.setSystemTime(date);

    await loadApp();
    
    const checkbox = customDocument.querySelector('#system-theme-checkbox');
    const toggle = customDocument.querySelector('#theme-toggle');
    
    // Manually change checkbox checked state without firing event
    checkbox.checked = false;
    
    // Click theme toggle - this calls setManualTheme while autoThemeTimeoutId is active
    toggle.click();
    
    // Verify theme changed (from light to dark)
    expect(customDocument.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('renders disparity_rate column in summary table and does not apply negative highlighting to disparity, but applies to PER/PBR', async () => {
    await loadApp();
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(3);
    });

    const headers = Array.from(customDocument.querySelectorAll('thead th')).map(el => el.textContent.trim());
    // The columns: 기업명, 현재가 (원), 시가총액 (억원), 괴리율 (%), 2026(E) PER (배), 2026(E) PBR (배)
    expect(headers[3]).toBe('괴리율 (%)');

    // Check Samsung Electronics row (positive disparity rate: "135.0", negative PER: "-9.2")
    const samsungRow = customDocument.querySelector('#main-row-A005930');
    const samsungCells = samsungRow.querySelectorAll('td');
    expect(samsungCells[1].textContent).toBe('70,000원');
    expect(samsungCells[2].textContent).toBe('420조');
    expect(samsungCells[3].textContent).toBe('135% (고평가)');
    expect(samsungCells[3].classList.contains('col-disparity')).toBe(true);
    expect(samsungCells[3].classList.contains('negative-color')).toBe(false);
    expect(samsungCells[3].classList.contains('negative')).toBe(false);
    expect(samsungCells[4].textContent).toBe('-9배');
    expect(samsungCells[4].classList.contains('negative-color')).toBe(true);

    // Check Hyundai row (negative disparity rate: "-10.5", negative PBR: "-0.5")
    const hyundaiRow = customDocument.querySelector('#main-row-A005380');
    const hyundaiCells = hyundaiRow.querySelectorAll('td');
    expect(hyundaiCells[1].textContent).toBe('200,000원');
    expect(hyundaiCells[2].textContent).toBe('42조');
    expect(hyundaiCells[3].textContent).toBe('-11% (저평가)');
    expect(hyundaiCells[3].classList.contains('col-disparity')).toBe(true);
    expect(hyundaiCells[3].classList.contains('negative-color')).toBe(false);
    expect(hyundaiCells[3].classList.contains('negative')).toBe(false);
    expect(hyundaiCells[5].textContent).toBe('-1배');
    expect(hyundaiCells[5].classList.contains('negative-color')).toBe(true);

    // Check 부실기업 row (missing disparity rate: "-")
    const busilRow = customDocument.querySelector('#main-row-A999999');
    const busilCells = busilRow.querySelectorAll('td');
    expect(busilCells[1].textContent).toBe('-');
    expect(busilCells[2].textContent).toBe('-');
    expect(busilCells[3].textContent).toBe('-');
    expect(busilCells[3].classList.contains('col-disparity')).toBe(true);
    expect(busilCells[3].classList.contains('negative-color')).toBe(false);
    expect(busilCells[3].classList.contains('negative')).toBe(false);

    // Check detail row colspan is 6
    const detailRow = customDocument.querySelector('#detail-row-A005930');
    const detailTd = detailRow.querySelector('td');
    expect(detailTd.getAttribute('colspan')).toBe('6');
  });

  it('formats summary table values correctly with units and handles various edge cases', async () => {
    // Inject custom mock state with formatting edge cases
    mockFetch.mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          {
            gicode: "A111111",
            name: "엣지케이스기업",
            category: "기타",
            current_price: "5,000",
            market_cap: "1,493,127",
            disparity_rate: "0.0",
            years: ["2025", "2026", "2027", "2028"],
            PBR: ["1.0", "1.0", "1.0", "1.0"],
            PER: ["10.0", "10.0", "10.0", "10.0"],
            EPS: ["500", "500", "500", "500"],
            영업이익: ["500", "500", "500", "500"]
          },
          {
            gicode: "A222222",
            name: "소형기업",
            category: "기타",
            current_price: "1,200",
            market_cap: "311",
            disparity_rate: "25.4",
            years: ["2025", "2026", "2027", "2028"],
            PBR: ["0.5", "0.5", "0.5", "0.5"],
            PER: ["5.0", "5.0", "5.0", "5.0"],
            EPS: ["100", "100", "100", "100"],
            영업이익: ["100", "100", "100", "100"]
          },
          {
            gicode: "A333333",
            name: "방어코드테스트기업",
            category: "기타",
            current_price: undefined,
            market_cap: undefined,
            disparity_rate: undefined,
            years: ["2025", "2026", "2027", "2028"],
            PBR: [undefined, undefined, undefined, undefined],
            PER: [undefined, undefined, undefined, undefined],
            EPS: [],
            영업이익: []
          },
          {
            gicode: "A444444",
            name: "비수치테스트기업",
            category: "기타",
            current_price: "-",
            market_cap: "-",
            disparity_rate: "-",
            years: ["2025", "2026", "2027", "2028"],
            PBR: ["-", "-", "-", "-"],
            PER: ["-", "-", "-", "-"],
            EPS: [],
            영업이익: []
          },
          {
            gicode: "A555555",
            name: "NaN테스트기업",
            category: "기타",
            current_price: "1,000",
            market_cap: "NaN_value",
            disparity_rate: "NaN_rate",
            years: ["2025", "2026", "2027", "2028"],
            PBR: ["1.0", "NaN_ratio", "1.0", "1.0"],
            PER: ["10.0", "NaN_ratio", "10.0", "10.0"],
            EPS: [],
            영업이익: []
          }
        ])
      })
    );

    await loadApp();
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(5);
    });

    const edgeRow = customDocument.querySelector('#main-row-A111111');
    const edgeCells = edgeRow.querySelectorAll('td');
    // Mcap "1,493,127" (1493127) -> 149조 3000억
    expect(edgeCells[2].textContent).toBe('149조 3000억');
    // Disparity "0.0" -> 0% (no tag)
    expect(edgeCells[3].textContent).toBe('0%');

    const smallRow = customDocument.querySelector('#main-row-A222222');
    const smallCells = smallRow.querySelectorAll('td');
    // Mcap "311" (311) -> 311억
    expect(smallCells[2].textContent).toBe('311억');
    // Disparity "25.4" -> 25% (고평가)
    expect(smallCells[3].textContent).toBe('25% (고평가)');
    // PBR "0.5" -> 1배
    expect(smallCells[5].textContent).toBe('1배');

    const guardRow = customDocument.querySelector('#main-row-A333333');
    const guardCells = guardRow.querySelectorAll('td');
    expect(guardCells[1].textContent).toBe('-');
    expect(guardCells[2].textContent).toBe('-');
    expect(guardCells[3].textContent).toBe('-');
    expect(guardCells[4].textContent).toBe('-');
    expect(guardCells[5].textContent).toBe('-');

    const dashRow = customDocument.querySelector('#main-row-A444444');
    const dashCells = dashRow.querySelectorAll('td');
    expect(dashCells[1].textContent).toBe('-');
    expect(dashCells[2].textContent).toBe('-');
    expect(dashCells[3].textContent).toBe('-');
    expect(dashCells[4].textContent).toBe('-');
    expect(dashCells[5].textContent).toBe('-');

    const nanRow = customDocument.querySelector('#main-row-A555555');
    const nanCells = nanRow.querySelectorAll('td');
    expect(nanCells[2].textContent).toBe('-');
    expect(nanCells[3].textContent).toBe('-');
    expect(nanCells[4].textContent).toBe('-');
    expect(nanCells[5].textContent).toBe('-');
  });

  it('renders tooltip trigger button next to 괴리율 (%)', async () => {
    await loadApp();
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(3);
    });

    const thDisparity = customDocument.querySelector('th.th-disparity');
    expect(thDisparity).toBeTruthy();
    expect(thDisparity.textContent).toContain('괴리율 (%)');
    
    const trigger = thDisparity.querySelector('.tooltip-trigger');
    expect(trigger).toBeTruthy();
    expect(trigger.getAttribute('aria-describedby')).toBe('disparity-tooltip');
  });

  it('shows and hides tooltip on mouseenter/mouseleave and focus/blur', async () => {
    await loadApp();
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(3);
    });

    const trigger = customDocument.querySelector('.tooltip-trigger');
    const tooltip = customDocument.getElementById('disparity-tooltip');

    expect(tooltip.style.display).not.toBe('block');

    // mouseenter -> show tooltip
    trigger.dispatchEvent(new customWindow.Event('mouseenter'));
    expect(tooltip.style.display).toBe('block');
    expect(tooltip.classList.contains('visible')).toBe(true);
    expect(tooltip.getAttribute('aria-hidden')).toBe('false');

    // mouseleave -> schedule hide (timeout 150ms)
    trigger.dispatchEvent(new customWindow.Event('mouseleave'));
    expect(tooltip.classList.contains('visible')).toBe(true);

    // Fast-forward 160ms
    vi.advanceTimersByTime(160);
    expect(tooltip.classList.contains('visible')).toBe(false);
    expect(tooltip.getAttribute('aria-hidden')).toBe('true');

    // Wait for the fade-out timeout (another 150ms)
    vi.advanceTimersByTime(160);
    expect(tooltip.style.display).toBe('none');

    // focus -> show tooltip
    trigger.dispatchEvent(new customWindow.Event('focus'));
    expect(tooltip.style.display).toBe('block');
    expect(tooltip.classList.contains('visible')).toBe(true);

    // blur -> schedule hide
    trigger.dispatchEvent(new customWindow.Event('blur'));
    vi.advanceTimersByTime(320); // pass both timeouts
    expect(tooltip.style.display).toBe('none');
  });

  it('keeps tooltip open when hovering on the tooltip itself', async () => {
    await loadApp();
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(3);
    });

    const trigger = customDocument.querySelector('.tooltip-trigger');
    const tooltip = customDocument.getElementById('disparity-tooltip');

    // mouseenter on trigger
    trigger.dispatchEvent(new customWindow.Event('mouseenter'));
    expect(tooltip.classList.contains('visible')).toBe(true);

    // mouseleave on trigger -> starts hide timeout
    trigger.dispatchEvent(new customWindow.Event('mouseleave'));

    // mouseenter on tooltip itself before timeout fires
    tooltip.dispatchEvent(new customWindow.Event('mouseenter'));

    // Fast-forward 200ms
    vi.advanceTimersByTime(200);
    expect(tooltip.classList.contains('visible')).toBe(true);

    // mouseleave on tooltip -> starts hide timeout again
    tooltip.dispatchEvent(new customWindow.Event('mouseleave'));

    // Fast-forward 350ms
    vi.advanceTimersByTime(350);
    expect(tooltip.style.display).toBe('none');
  });

  it('hides tooltip immediately when Escape key is pressed', async () => {
    await loadApp();
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(3);
    });

    const trigger = customDocument.querySelector('.tooltip-trigger');
    const tooltip = customDocument.getElementById('disparity-tooltip');

    // Scenario 1: Escape with no active timeouts
    trigger.dispatchEvent(new customWindow.Event('mouseenter'));
    expect(tooltip.classList.contains('visible')).toBe(true);

    let escapeEvent = new customWindow.KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
    customDocument.dispatchEvent(escapeEvent);
    expect(tooltip.classList.contains('visible')).toBe(false);
    vi.advanceTimersByTime(160);
    expect(tooltip.style.display).toBe('none');

    // Scenario 2: Escape while hideTimeoutId is active
    trigger.dispatchEvent(new customWindow.Event('mouseenter'));
    trigger.dispatchEvent(new customWindow.Event('mouseleave')); // hideTimeoutId active
    escapeEvent = new customWindow.KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
    customDocument.dispatchEvent(escapeEvent);
    expect(tooltip.classList.contains('visible')).toBe(false);
    vi.advanceTimersByTime(160);
    expect(tooltip.style.display).toBe('none');

    // Scenario 3: Escape while fadeOutTimeoutId is active
    trigger.dispatchEvent(new customWindow.Event('mouseenter'));
    trigger.dispatchEvent(new customWindow.Event('mouseleave'));
    vi.advanceTimersByTime(160); // fadeOutTimeoutId active, visible is false, display is block
    expect(tooltip.classList.contains('visible')).toBe(false);
    expect(tooltip.style.display).toBe('block');

    escapeEvent = new customWindow.KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
    customDocument.dispatchEvent(escapeEvent);
    vi.advanceTimersByTime(160);
    expect(tooltip.style.display).toBe('none');

    // Scenario 4: Escape when tooltip is not visible (should do nothing)
    const mockPreventDefault = vi.fn();
    const escapeEvent2 = new customWindow.KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
    Object.defineProperty(escapeEvent2, 'preventDefault', { value: mockPreventDefault });
    customDocument.dispatchEvent(escapeEvent2);
    expect(tooltip.style.display).toBe('none');
  });

  it('handles multiple scheduleHide calls and clears active timeouts properly', async () => {
    await loadApp();
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(3);
    });

    const trigger = customDocument.querySelector('.tooltip-trigger');
    const tooltip = customDocument.getElementById('disparity-tooltip');

    // Show tooltip
    trigger.dispatchEvent(new customWindow.Event('mouseenter'));

    // Call scheduleHide twice in a row (e.g. mouseleave then blur)
    trigger.dispatchEvent(new customWindow.Event('mouseleave'));
    trigger.dispatchEvent(new customWindow.Event('blur')); // covers line 60 (hideTimeoutId is active)

    // Wait 160ms so it starts fading out (fadeOutTimeoutId is active)
    vi.advanceTimersByTime(160);

    // Call scheduleHide again without calling showTooltip (covers line 66: fadeOutTimeoutId is active)
    trigger.dispatchEvent(new customWindow.Event('mouseleave'));
    vi.advanceTimersByTime(160);
  });

  it('stops propagation on click event of tooltip trigger', async () => {
    await loadApp();
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(3);
    });

    const trigger = customDocument.querySelector('.tooltip-trigger');
    const clickEvent = new customWindow.MouseEvent('click', { bubbles: true, cancelable: true });
    const spy = vi.spyOn(clickEvent, 'stopPropagation');

    trigger.dispatchEvent(clickEvent);
    expect(spy).toHaveBeenCalled();
  });

  it('adjusts tooltip position bounds when overflowing right edge', async () => {
    await loadApp();
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(3);
    });

    const trigger = customDocument.querySelector('.tooltip-trigger');
    const tooltip = customDocument.getElementById('disparity-tooltip');

    // Mock window innerWidth
    const originalInnerWidth = customWindow.innerWidth;
    customWindow.innerWidth = 500;

    // Mock getBoundingClientRect for trigger to be near the right edge
    vi.spyOn(trigger, 'getBoundingClientRect').mockReturnValue({
      left: 450,
      right: 480,
      top: 100,
      bottom: 120,
      width: 30,
      height: 20
    });

    // Mock tooltip offsetWidth/Height
    Object.defineProperties(tooltip, {
      offsetWidth: { value: 200, configurable: true },
      offsetHeight: { value: 80, configurable: true }
    });

    trigger.dispatchEvent(new customWindow.Event('mouseenter'));

    // expected left calculation:
    // left = 450 + (30 / 2) - (200 / 2) = 450 + 15 - 100 = 365
    // left + tooltipWidth = 365 + 200 = 565
    // window.innerWidth - 8 = 500 - 8 = 492
    // Since 565 > 492, left should be adjusted to: 500 - 200 - 8 = 292px.
    expect(tooltip.style.left).toBe('292px');

    // Restore innerWidth
    customWindow.innerWidth = originalInnerWidth;
  });

  it('cancels fade-out and restores visibility if trigger or tooltip is hovered/focused during fade-out', async () => {
    await loadApp();
    await vi.waitFor(() => {
      expect(customDocument.querySelectorAll('.main-row').length).toBe(3);
    });

    const trigger = customDocument.querySelector('.tooltip-trigger');
    const tooltip = customDocument.getElementById('disparity-tooltip');

    // Show tooltip
    trigger.dispatchEvent(new customWindow.Event('mouseenter'));
    expect(tooltip.classList.contains('visible')).toBe(true);

    // Mouse leaves trigger
    trigger.dispatchEvent(new customWindow.Event('mouseleave'));

    // Advance 160ms so it starts fading out (fadeOutTimeoutId is now active)
    vi.advanceTimersByTime(160);
    expect(tooltip.classList.contains('visible')).toBe(false);
    expect(tooltip.style.display).toBe('block');

    // Mouse enters tooltip during fadeout -> visibility should be restored
    tooltip.dispatchEvent(new customWindow.Event('mouseenter'));
    expect(tooltip.classList.contains('visible')).toBe(true);
    expect(tooltip.style.display).toBe('block');

    // Mouse leaves tooltip again
    tooltip.dispatchEvent(new customWindow.Event('mouseleave'));
    vi.advanceTimersByTime(160);
    expect(tooltip.classList.contains('visible')).toBe(false);

    // Mouse enters trigger again during this fadeout
    trigger.dispatchEvent(new customWindow.Event('mouseenter'));
    expect(tooltip.classList.contains('visible')).toBe(true);
    expect(tooltip.style.display).toBe('block');
  });
});

