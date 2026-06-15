document.addEventListener("DOMContentLoaded", () => {
  const state = {
    stocks: [],
    sortDirection: "asc" // 'asc' or 'desc'
  };

  const tbody = document.getElementById("stocks-tbody");
  const thName = document.getElementById("th-name");
  const sortIcon = document.getElementById("sort-icon-name");
  const themeToggle = document.getElementById("theme-toggle");

  // Helper: check if a value string is negative
  const isNegative = (valStr) => {
    if (!valStr) return false;
    const clean = valStr.trim();
    return clean.startsWith("-") && clean !== "-";
  };

  // Render Table
  const renderTable = () => {
    if (state.stocks.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: var(--text-secondary); padding: 3rem;">
            표시할 데이터가 없습니다.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = "";

    state.stocks.forEach((stock, index) => {
      const mainRowId = `main-row-${index}`;
      const detailRowId = `detail-row-${index}`;
      const accordionId = `accordion-${index}`;

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

      tbody.appendChild(mainRow);
      tbody.appendChild(detailRow);

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
  };

  // Sorting logic (Stock Name only)
  const sortStocks = () => {
    state.stocks.sort((a, b) => {
      // localeCompare with 'ko' correctly handles Korean alphabetical ordering
      const compareResult = a.name.localeCompare(b.name, "ko");
      return state.sortDirection === "asc" ? compareResult : -compareResult;
    });

    renderTable();
  };

  thName.addEventListener("click", () => {
    // Toggle sort direction
    if (state.sortDirection === "asc") {
      state.sortDirection = "desc";
      thName.className = "sortable sorted-desc";
      sortIcon.textContent = "▲";
    } else {
      state.sortDirection = "asc";
      thName.className = "sortable sorted-asc";
      sortIcon.textContent = "▼";
    }
    sortStocks();
  });

  // Theme Toggler logic
  const setTheme = (theme) => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("color-scheme", theme);
  };

  themeToggle.addEventListener("click", () => {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    setTheme(newTheme);
  });

  themeToggle.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      themeToggle.click();
    }
  });

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
      // Sort initially
      sortStocks();
    })
    .catch((error) => {
      console.error("Failed to load stocks data:", error);
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: #ef4444; padding: 3rem; font-weight: 600;">
            데이터를 불러오는 데 실패했습니다.<br>
            <span style="font-size: 0.85rem; font-weight: 400; color: var(--text-secondary);">${error.message}</span>
          </td>
        </tr>
      `;
    });
});
