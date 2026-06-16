document.addEventListener("DOMContentLoaded", () => {
  const state = {
    stocks: [],
    sortDirections: {} // { "전기전자": "asc", "자동차": "asc", ... }
  };

  const tablesContainer = document.getElementById("tables-container");
  const themeToggle = document.getElementById("theme-toggle");

  // Helper: check if a value string is negative
  const isNegative = (valStr) => {
    if (!valStr) return false;
    const clean = valStr.trim();
    return clean.startsWith("-") && clean !== "-";
  };

  // Render Dashboard
  const renderTable = () => {
    if (state.stocks.length === 0) {
      tablesContainer.innerHTML = `
        <div style="text-align: center; color: var(--text-secondary); padding: 3rem; background: var(--container-bg); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid var(--container-border); border-radius: 1rem;">
          표시할 데이터가 없습니다.
        </div>
      `;
      return;
    }

    // Extract categories in order of appearance (preserving CSV/JSON order)
    const categories = [];
    state.stocks.forEach((stock) => {
      const cat = stock.category || "기타";
      if (!categories.includes(cat)) {
        categories.push(cat);
      }
    });

    // Clear container
    tablesContainer.innerHTML = "";

    categories.forEach((category) => {
      // Get sorted stocks for this category
      const categoryStocks = state.stocks.filter((s) => (s.category || "기타") === category);
      const direction = state.sortDirections[category] || "asc";
      
      categoryStocks.sort((a, b) => {
        const compareResult = a.name.localeCompare(b.name, "ko");
        return direction === "asc" ? compareResult : -compareResult;
      });

      // Create Category Header (h2)
      const titleEl = document.createElement("h2");
      titleEl.className = "category-title";
      titleEl.textContent = category;
      tablesContainer.appendChild(titleEl);

      // Create Table Card
      const cardEl = document.createElement("div");
      cardEl.className = "table-card";

      const wrapperEl = document.createElement("div");
      wrapperEl.className = "table-wrapper";

      const tableEl = document.createElement("table");
      
      // Table Header (using '기업명' instead of '종목명')
      const thClass = `sortable ${direction === "asc" ? "sorted-asc" : "sorted-desc"}`;
      const sortIconText = direction === "asc" ? "▼" : "▲";
      
      tableEl.innerHTML = `
        <thead>
          <tr>
            <th scope="col" class="${thClass}" data-category="${category}" title="기업명을 기준으로 정렬합니다" tabindex="0">
              기업명 <span class="sort-icon">${sortIconText}</span>
            </th>
            <th scope="col">현재가 (원)</th>
            <th scope="col">시가총액 (억원)</th>
            <th scope="col">2026(E) PER (배)</th>
            <th scope="col">2026(E) PBR (배)</th>
          </tr>
        </thead>
      `;

      const tbodyEl = document.createElement("tbody");

      categoryStocks.forEach((stock) => {
        const mainRowId = `main-row-${stock.gicode}`;
        const detailRowId = `detail-row-${stock.gicode}`;
        const accordionId = `accordion-${stock.gicode}`;

        // Create main row
        const mainRow = document.createElement("tr");
        mainRow.className = "main-row";
        mainRow.id = mainRowId;
        mainRow.setAttribute("tabindex", "0");
        mainRow.setAttribute("role", "button");
        mainRow.setAttribute("aria-expanded", "false");
        mainRow.setAttribute("aria-controls", detailRowId);

        // We display 2026(E) PER and PBR on the summary row (index 1 of years list ["2025", "2026", "2027", "2028"])
        const summaryPer = stock.PER[1] || "-";
        const summaryPbr = stock.PBR[1] || "-";

        mainRow.innerHTML = `
          <td class="col-name">
            <svg class="chevron-icon" viewBox="0 0 24 24">
              <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>
            </svg>
            <span>${stock.name}</span>
            <span class="col-gicode">${stock.gicode}</span>
          </td>
          <td class="col-price">${stock.current_price}</td>
          <td class="col-mcap">${stock.market_cap}</td>
          <td class="col-summary-per ${isNegative(summaryPer) ? "negative" : ""}">${summaryPer}</td>
          <td class="col-summary-pbr ${isNegative(summaryPbr) ? "negative" : ""}">${summaryPbr}</td>
        `;

        // Create detail row
        const detailRow = document.createElement("tr");
        detailRow.className = "detail-row";
        detailRow.id = detailRowId;
        detailRow.style.display = "none"; // Hide initially

        // Generate HTML for metric cards (PER, PBR, EPS, 영업이익)
        const renderMetricCard = (title, dataList) => {
          let gridHeaders = "";
          let gridValues = "";

          stock.years.forEach((year, idx) => {
            const val = dataList[idx] || "-";
            const isEst = year === "2026" || year === "2027" || year === "2028";
            const displayYear = isEst ? `${year}(E)` : year;
            
            gridHeaders += `<div class="grid-header">${displayYear}</div>`;
            gridValues += `<div class="grid-value ${isNegative(val) ? "negative" : ""}">${val}</div>`;
          });

          return `
            <div class="metric-card">
              <div class="metric-title">${title}</div>
              <div class="metric-grid">
                ${gridHeaders}
                ${gridValues}
              </div>
            </div>
          `;
        };

        detailRow.innerHTML = `
          <td colspan="5">
            <div class="accordion-wrapper" id="${accordionId}">
              <div class="accordion-inner">
                <div class="detail-content">
                  ${renderMetricCard("영업이익 (억원)", stock.영업이익)}
                  ${renderMetricCard("EPS (원)", stock.EPS)}
                  ${renderMetricCard("PER (배)", stock.PER)}
                  ${renderMetricCard("PBR (배)", stock.PBR)}
                </div>
              </div>
            </div>
          </td>
        `;

        tbodyEl.appendChild(mainRow);
        tbodyEl.appendChild(detailRow);

        // Event listener for expanding/collapsing
        const toggleAccordion = () => {
          const isActive = mainRow.classList.contains("active");
          const accordion = document.getElementById(accordionId);

          if (isActive) {
            // Collapse
            mainRow.classList.remove("active");
            mainRow.setAttribute("aria-expanded", "false");
            accordion.classList.remove("expanded");
            
            // Wait for CSS grid transition to complete before hiding container
            setTimeout(() => {
              if (!mainRow.classList.contains("active")) {
                detailRow.style.display = "none";
              }
            }, 300); // matches CSS transition time
          } else {
            // Expand
            detailRow.style.display = "table-row";
            mainRow.classList.add("active");
            mainRow.setAttribute("aria-expanded", "true");
            
            // Force layout reflow so transition runs properly
            void accordion.offsetHeight;
            
            accordion.classList.add("expanded");
          }
        };

        mainRow.addEventListener("click", toggleAccordion);
        mainRow.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggleAccordion();
          }
        });
      });

      tableEl.appendChild(tbodyEl);
      wrapperEl.appendChild(tableEl);
      cardEl.appendChild(wrapperEl);
      tablesContainer.appendChild(cardEl);
    });
  };

  // Event delegation for table sorting (click on sortable header)
  tablesContainer.addEventListener("click", (e) => {
    const th = e.target.closest("th.sortable");
    if (th) {
      const category = th.dataset.category;
      const currentDir = state.sortDirections[category] || "asc";
      state.sortDirections[category] = currentDir === "asc" ? "desc" : "asc";
      renderTable();
    }
  });

  // Support Keyboard interaction (Enter/Space) on the sortable header
  tablesContainer.addEventListener("keydown", (e) => {
    const th = e.target.closest("th.sortable");
    if (th && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      th.click();
    }
  });

  // Theme Toggler logic
  const systemThemeCheckbox = document.getElementById("system-theme-checkbox");
  let autoThemeTimeoutId = null;

  const updateTheme = (theme) => {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    if (currentTheme !== theme) {
      document.documentElement.setAttribute("data-theme", theme);
    }
  };

  const updateAutoTheme = () => {
    const now = new Date();
    const currentHour = now.getHours();
    
    // 밤 시간: 20시 ~ 다음날 07시 (오후 8시 ~ 오전 7시)
    const isNight = currentHour >= 20 || currentHour < 7;
    const targetTheme = isNight ? "dark" : "light";
    updateTheme(targetTheme);

    // 다음 전환 시간 계산
    let nextTransition = new Date(now);
    if (currentHour >= 7 && currentHour < 20) {
      // 낮 시간대 -> 다음 전환은 오늘 오후 8시
      nextTransition.setHours(20, 0, 0, 0);
    } else {
      // 밤 시간대 -> 다음 전환은 오전 7시
      if (currentHour >= 20) {
        // 이미 오늘 오후 8시를 넘었으므로 다음 오전 7시는 내일
        nextTransition.setDate(now.getDate() + 1);
      }
      nextTransition.setHours(7, 0, 0, 0);
    }

    const msUntilTransition = nextTransition.getTime() - now.getTime();

    // 기존 타이머 취소 후 재등록
    if (autoThemeTimeoutId) {
      clearTimeout(autoThemeTimeoutId);
    }

    // 500ms 여유를 두어 정확한 시점 전환 보장
    autoThemeTimeoutId = setTimeout(() => {
      updateAutoTheme();
    }, msUntilTransition + 500);
  };

  const setManualTheme = (theme) => {
    // 수동 제어 시 자동 전환 타이머는 완전히 제거
    if (autoThemeTimeoutId) {
      clearTimeout(autoThemeTimeoutId);
      autoThemeTimeoutId = null;
    }
    updateTheme(theme);
    localStorage.setItem("manual-theme", theme);
  };

  const handleSystemThemeCheckboxChange = () => {
    const isChecked = systemThemeCheckbox.checked;
    localStorage.setItem("system-theme-enabled", isChecked ? "true" : "false");

    if (isChecked) {
      themeToggle.classList.add("disabled");
      updateAutoTheme();
    } else {
      themeToggle.classList.remove("disabled");
      if (autoThemeTimeoutId) {
        clearTimeout(autoThemeTimeoutId);
        autoThemeTimeoutId = null;
      }
      // 체크를 해제할 때 현재 테마 상태를 수동 테마로 고정
      const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
      localStorage.setItem("manual-theme", currentTheme);
    }
  };

  // 탭 재진입/포커스 또는 절전모드 해제 시 시간 동기화
  const handleVisibilityOrFocus = () => {
    const isChecked = systemThemeCheckbox.checked;
    if (isChecked && document.visibilityState === "visible") {
      updateAutoTheme();
    }
  };

  // 초기 상태 로드
  const initTheme = () => {
    const systemThemeEnabled = localStorage.getItem("system-theme-enabled") !== "false";
    systemThemeCheckbox.checked = systemThemeEnabled;

    if (systemThemeEnabled) {
      themeToggle.classList.add("disabled");
      updateAutoTheme();
    } else {
      themeToggle.classList.remove("disabled");
      const savedManualTheme = localStorage.getItem("manual-theme") || "light";
      setManualTheme(savedManualTheme);
    }
  };

  // Event Listeners
  systemThemeCheckbox.addEventListener("change", handleSystemThemeCheckboxChange);

  themeToggle.addEventListener("click", () => {
    // System Auto가 켜져 있으면 토글 클릭 무반응
    if (systemThemeCheckbox.checked) return;

    const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    setManualTheme(newTheme);
  });

  themeToggle.addEventListener("keydown", (e) => {
    if (systemThemeCheckbox.checked) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      themeToggle.click();
    }
  });

  document.addEventListener("visibilitychange", handleVisibilityOrFocus);
  window.addEventListener("focus", handleVisibilityOrFocus);

  // Initialize Theme Settings
  initTheme();

  // Load Data
  fetch("data/stocks.json")
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      state.stocks = data;
      // Initialize sort directions for all unique categories
      data.forEach((stock) => {
        const cat = stock.category || "기타";
        if (!state.sortDirections[cat]) {
          state.sortDirections[cat] = "asc"; // Default sort direction
        }
      });
      renderTable();
    })
    .catch((error) => {
      console.error("Failed to load stocks data:", error);
      tablesContainer.innerHTML = `
        <div style="text-align: center; color: #ef4444; padding: 3rem; font-weight: 600; background: var(--container-bg); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid var(--container-border); border-radius: 1rem;">
          데이터를 불러오는 데 실패했습니다.<br>
          <span style="font-size: 0.85rem; font-weight: 400; color: var(--text-secondary);">${error.message}</span>
        </div>
      `;
    });
});
