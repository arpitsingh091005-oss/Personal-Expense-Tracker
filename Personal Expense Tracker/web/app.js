// Personal Expense Tracker - Client-side Application Logic
// Built with Vanilla JS - connects to Core Python HTTP Server

let currentUser = {
  id: 1,
  username: "demo_user"
};

let currentFilter = "ALL";
let cachedTransactions = [];

const CATEGORY_EMOJIS = {
  food: "🍔",
  travel: "🚗",
  shopping: "🛍️",
  education: "📚",
  entertainment: "🎬",
  medical: "💊",
  bills: "💡",
  "gym & fitness": "🏋️",
  salary: "💼",
  freelancing: "💻",
  investment: "📈",
  other: "🏷️",
  others: "🏷️"
};

function getCategoryLabel(name) {
  if (!name) return "";
  const key = name.toLowerCase().trim();
  const emoji = CATEGORY_EMOJIS[key] || "🏷️";
  return `${emoji} ${name}`;
}

// Helper: Format paise to INR currency string
function formatCurrency(paise) {
  if (paise === null || paise === undefined) return "₹ 0.00";
  const isNegative = paise < 0;
  const absPaise = Math.abs(paise);
  const rupees = Math.floor(absPaise / 100);
  const rem = absPaise % 100;
  const remStr = rem < 10 ? "0" + rem : rem;
  const prefix = isNegative ? "-" : "";
  return `${prefix}₹ ${rupees.toLocaleString("en-IN")}.${remStr}`;
}

// Helper: Format ISO date string to DD-Mon-YYYY
function formatDate(dateStr) {
  if (!dateStr) return "-";
  try {
    const parts = dateStr.split(" ")[0].split("-");
    const d = new Date(parts[0], parts[1] - 1, parts[2]);
    return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  } catch (e) {
    return dateStr;
  }
}

// Dynamic Human Greeting
function updateGreeting() {
  const greetingEl = document.getElementById("welcome-greeting");
  if (!greetingEl) return;
  const hour = new Date().getHours();
  let timeGreeting = "Good evening";
  if (hour < 12) timeGreeting = "Good morning";
  else if (hour < 17) timeGreeting = "Good afternoon";

  greetingEl.textContent = `${timeGreeting}, ${currentUser.username} 👋`;
}

// Delightful Toast Notification Helper
function showToast(title, message, type = "success") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  const icon = type === "success" ? "✅" : (type === "error" ? "❌" : "⚠️");
  toast.innerHTML = `
    <span style="font-size: 1.15rem;">${icon}</span>
    <div>
      <strong>${escapeHtml(title)}</strong>
      <p style="font-size: 0.8rem; margin: 0; color: var(--text-muted);">${escapeHtml(message)}</p>
    </div>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(12px) scale(0.95)";
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

// Document Ready Initialization
document.addEventListener("DOMContentLoaded", () => {
  setupThemeToggle();
  setupTabs();
  setupModals();
  setupSearch();
  setDefaultDates();
  updateGreeting();
  loadAllData();
});

// Modern Dark & Light Mode Theme Controller
function setupThemeToggle() {
  const meta = document.querySelector('meta[name="color-scheme"]') || document.createElement('meta');
  const btn = document.getElementById("btn-theme-toggle");
  const label = document.getElementById("theme-label");
  const icon = document.getElementById("theme-icon");

  const getSystemTheme = () => window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";

  const updateButtonUI = () => {
    const currentMeta = meta.content;
    const isDark = currentMeta === "dark" || (currentMeta === "light dark" && getSystemTheme() === "dark");

    if (label && icon) {
      if (isDark) {
        label.textContent = "Light";
        icon.innerHTML = '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>';
      } else {
        label.textContent = "Dark";
        icon.innerHTML = '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>';
      }
    }
  };

  updateButtonUI();

  btn?.addEventListener("click", () => {
    const currentMeta = meta.content;
    const currentResolved = currentMeta === "dark" || (currentMeta === "light dark" && getSystemTheme() === "dark") ? "dark" : "light";
    const target = currentResolved === "dark" ? "light" : "dark";

    if (target === getSystemTheme()) {
      try { localStorage.removeItem("color-scheme"); } catch (e) {}
      meta.content = "light dark";
    } else {
      try { localStorage.setItem("color-scheme", target); } catch (e) {}
      meta.content = target;
    }

    updateButtonUI();
    showToast("Theme Updated", `Switched to ${target} mode`, "success");
  });

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (meta.content === "light dark") {
      updateButtonUI();
    }
  });

  window.addEventListener("storage", (e) => {
    if (e.key === "color-scheme") {
      meta.content = e.newValue || "light dark";
      updateButtonUI();
    }
  });
}

// Tab Navigation Logic
function setupTabs() {
  const tabs = document.querySelectorAll(".tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      const targetId = `tab-${tab.dataset.tab}`;
      document.querySelectorAll(".tab-content").forEach(content => {
        content.classList.remove("active");
      });
      const activeContent = document.getElementById(targetId);
      if (activeContent) activeContent.classList.add("active");

      if (tab.dataset.tab === "transactions") {
        loadTransactionsTable();
      } else if (tab.dataset.tab === "budget") {
        loadBudgetInfo();
      }
    });
  });

  // Filter Buttons on Transactions tab
  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.dataset.type;
      renderTransactionsTable();
    });
  });
}

// Search Handler
function setupSearch() {
  const searchInput = document.getElementById("input-search-tx");
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      renderTransactionsTable();
    });
  }
}

// Native Dialog Modal Open & Close Listeners
function setupModals() {
  const openIncome = () => {
    loadCategoryOptions("INCOME", "inc-category");
    document.getElementById("dialog-add-income").showModal();
  };

  const openExpense = () => {
    loadCategoryOptions("EXPENSE", "exp-category");
    document.getElementById("dialog-add-expense").showModal();
  };

  document.getElementById("btn-open-income")?.addEventListener("click", openIncome);
  document.getElementById("btn-open-income-2")?.addEventListener("click", openIncome);
  document.getElementById("btn-open-expense")?.addEventListener("click", openExpense);
  document.getElementById("btn-open-expense-2")?.addEventListener("click", openExpense);

  const openBudget = () => {
    const now = new Date();
    document.getElementById("bgt-month").value = now.getMonth() + 1;
    document.getElementById("bgt-year").value = now.getFullYear();
    document.getElementById("dialog-set-budget").showModal();
  };

  document.getElementById("btn-set-budget-modal")?.addEventListener("click", openBudget);
  document.getElementById("btn-quick-budget")?.addEventListener("click", openBudget);

  document.getElementById("btn-login-modal")?.addEventListener("click", () => {
    document.getElementById("dialog-login").showModal();
  });

  // Modal Close buttons
  document.querySelectorAll("[data-close]").forEach(btn => {
    btn.addEventListener("click", () => {
      const dialog = document.getElementById(btn.dataset.close);
      if (dialog) dialog.close();
    });
  });

  // Form Submissions
  document.getElementById("form-add-income")?.addEventListener("submit", handleAddIncome);
  document.getElementById("form-add-expense")?.addEventListener("submit", handleAddExpense);
  document.getElementById("form-set-budget")?.addEventListener("submit", handleSetBudget);
  document.getElementById("form-login")?.addEventListener("submit", handleLogin);

  // CSV Export Buttons
  const triggerCsv = () => {
    showToast("Generating CSV", "Your spreadsheet download is starting...", "success");
    window.location.href = `/api/export-csv?user_id=${currentUser.id}`;
  };
  document.getElementById("btn-export-csv-tab")?.addEventListener("click", triggerCsv);
  document.getElementById("btn-export-csv-reports")?.addEventListener("click", triggerCsv);
}

function setDefaultDates() {
  const today = new Date().toISOString().split("T")[0];
  const incDate = document.getElementById("inc-date");
  const expDate = document.getElementById("exp-date");
  if (incDate) incDate.value = today;
  if (expDate) expDate.value = today;
}

// Master Data Fetcher
async function loadAllData() {
  await Promise.all([
    loadDashboardSummary(),
    loadBudgetInfo(),
    loadTransactionsTable()
  ]);
}

// Fetch and Render Dashboard Metrics
async function loadDashboardSummary() {
  try {
    const res = await fetch(`/api/summary?user_id=${currentUser.id}`);
    const data = await res.json();
    if (!data.success) return;

    const s = data.data;
    document.getElementById("card-total-income").textContent = formatCurrency(s.total_income);
    document.getElementById("card-total-expense").textContent = formatCurrency(s.total_expenses);
    document.getElementById("card-balance").textContent = formatCurrency(s.balance);
    document.getElementById("card-monthly-savings").textContent = formatCurrency(s.monthly_savings);

    // Highest and lowest
    if (s.highest_expense) {
      document.getElementById("rep-highest-amt").textContent = formatCurrency(s.highest_expense.amount);
      document.getElementById("rep-highest-desc").textContent = `${getCategoryLabel(s.highest_expense.category_name)} - ${s.highest_expense.description || "No note"}`;
    } else {
      document.getElementById("rep-highest-amt").textContent = "₹ 0.00";
      document.getElementById("rep-highest-desc").textContent = "None recorded";
    }

    if (s.lowest_expense) {
      document.getElementById("rep-lowest-amt").textContent = formatCurrency(s.lowest_expense.amount);
      document.getElementById("rep-lowest-desc").textContent = `${getCategoryLabel(s.lowest_expense.category_name)} - ${s.lowest_expense.description || "No note"}`;
    } else {
      document.getElementById("rep-lowest-amt").textContent = "₹ 0.00";
      document.getElementById("rep-lowest-desc").textContent = "None recorded";
    }

    document.getElementById("rep-cat-count").textContent = s.category_breakdown.length;

    // Render Category Breakdown table in Reports tab
    const catTbody = document.getElementById("tbody-category-breakdown");
    if (catTbody) {
      catTbody.innerHTML = "";
      if (s.category_breakdown.length === 0) {
        catTbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No expense categories recorded yet.</td></tr>';
      } else {
        s.category_breakdown.forEach(c => {
          const row = document.createElement("tr");
          row.innerHTML = `
            <td><strong>${getCategoryLabel(c.category_name)}</strong></td>
            <td style="text-align: right; font-weight: 600;">${formatCurrency(c.amount)}</td>
            <td style="text-align: right;">${c.count}</td>
            <td style="text-align: right; font-weight: 600; color: var(--primary);">${c.percentage.toFixed(2)}%</td>
          `;
          catTbody.appendChild(row);
        });
      }
    }

  } catch (err) {
    console.error("Failed to load dashboard summary:", err);
  }
}

// Fetch Transactions
async function loadTransactionsTable() {
  try {
    const res = await fetch(`/api/transactions?user_id=${currentUser.id}`);
    const data = await res.json();
    if (!data.success) return;

    cachedTransactions = data.data;
    renderRecentTransactions();
    renderTransactionsTable();
  } catch (err) {
    console.error("Failed to load transactions:", err);
  }
}

// Render Recent 5 Transactions on Dashboard
function renderRecentTransactions() {
  const recentTbody = document.getElementById("tbody-recent-transactions");
  if (!recentTbody) return;

  recentTbody.innerHTML = "";
  const recentRows = cachedTransactions.slice(0, 5);

  if (recentRows.length === 0) {
    recentTbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No transactions recorded yet. Click "Add Income" or "Add Expense" to begin.</td></tr>';
    return;
  }

  recentRows.forEach(r => {
    const tr = document.createElement("tr");
    const isInc = r.transaction_type === "INCOME";
    const badgeClass = isInc ? "badge-income" : "badge-expense";
    tr.innerHTML = `
      <td>${formatDate(r.transaction_date)}</td>
      <td><span class="badge ${badgeClass}">${r.transaction_type}</span></td>
      <td><span class="badge badge-category">${getCategoryLabel(r.category_name)}</span></td>
      <td>${escapeHtml(r.description || "-")}</td>
      <td style="text-align: right; font-weight: 700; color: ${isInc ? "var(--success)" : "var(--danger)"};">
        ${isInc ? "+" : "-"}${formatCurrency(r.amount)}
      </td>
    `;
    recentTbody.appendChild(tr);
  });
}

// Render Transactions Table with live search and category pills
function renderTransactionsTable() {
  const allTbody = document.getElementById("tbody-all-transactions");
  if (!allTbody) return;

  const searchInput = document.getElementById("input-search-tx");
  const query = searchInput ? searchInput.value.toLowerCase().trim() : "";

  let filtered = cachedTransactions;
  if (currentFilter !== "ALL") {
    filtered = filtered.filter(t => t.transaction_type === currentFilter);
  }
  if (query) {
    filtered = filtered.filter(t => {
      const matchDesc = (t.description || "").toLowerCase().includes(query);
      const matchCat = (t.category_name || "").toLowerCase().includes(query);
      const matchDate = (t.transaction_date || "").includes(query);
      return matchDesc || matchCat || matchDate;
    });
  }

  allTbody.innerHTML = "";
  if (filtered.length === 0) {
    allTbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No matching records found.</td></tr>';
    return;
  }

  filtered.forEach(r => {
    const tr = document.createElement("tr");
    const isInc = r.transaction_type === "INCOME";
    const badgeClass = isInc ? "badge-income" : "badge-expense";
    tr.innerHTML = `
      <td style="color: var(--text-muted); font-size: 0.8rem;">#${r.transaction_id}</td>
      <td>${formatDate(r.transaction_date)}</td>
      <td><span class="badge ${badgeClass}">${r.transaction_type}</span></td>
      <td><span class="badge badge-category">${getCategoryLabel(r.category_name)}</span></td>
      <td>${escapeHtml(r.description || "-")}</td>
      <td style="text-align: right; font-weight: 700; color: ${isInc ? "var(--success)" : "var(--danger)"};">
        ${isInc ? "+" : "-"}${formatCurrency(r.amount)}
      </td>
      <td style="text-align: center;">
        <button type="button" class="btn btn-secondary" style="padding: 0.25rem 0.55rem; font-size: 0.75rem;" onclick="deleteTransaction(${r.transaction_id}, '${r.transaction_type}')">
          Delete
        </button>
      </td>
    `;
    allTbody.appendChild(tr);
  });
}

// Fetch and Render Budget Monitoring
async function loadBudgetInfo() {
  try {
    const now = new Date();
    const res = await fetch(`/api/budget?user_id=${currentUser.id}&month=${now.getMonth() + 1}&year=${now.getFullYear()}`);
    const data = await res.json();
    if (!data.success) return;

    const b = data.data;
    const alertBox = document.getElementById("dashboard-budget-alert");
    const alertTitle = document.getElementById("budget-alert-title");
    const alertDesc = document.getElementById("budget-alert-desc");
    const healthChip = document.getElementById("budget-health-chip");

    if (!b) {
      if (alertBox) alertBox.style.display = "none";
      document.getElementById("budget-spent-val").textContent = "₹ 0.00";
      document.getElementById("budget-total-val").textContent = "Not set";
      document.getElementById("budget-pct-text").textContent = "No budget configured for this month";
      document.getElementById("budget-remaining-text").textContent = "-";
      document.getElementById("budget-status-msg").textContent = "Set a budget cap to receive alerts as you approach 80% spending.";
      document.getElementById("budget-progress-bar").style.width = "0%";
      if (healthChip) {
        healthChip.textContent = "No Budget";
        healthChip.className = "badge badge-category";
      }
      return;
    }

    const pct = Math.min(b.percent_used, 100);
    const progressBar = document.getElementById("budget-progress-bar");
    progressBar.style.width = `${pct}%`;

    progressBar.className = "progress-bar";
    if (b.percent_used >= 100) {
      progressBar.classList.add("progress-danger");
      if (healthChip) { healthChip.textContent = "Over Budget"; healthChip.className = "badge badge-expense"; }
    } else if (b.percent_used >= 80) {
      progressBar.classList.add("progress-warning");
      if (healthChip) { healthChip.textContent = "80% Warning"; healthChip.className = "badge badge-category"; }
    } else {
      progressBar.classList.add("progress-normal");
      if (healthChip) { healthChip.textContent = "Healthy"; healthChip.className = "badge badge-income"; }
    }

    document.getElementById("budget-spent-val").textContent = formatCurrency(b.total_spent);
    document.getElementById("budget-total-val").textContent = formatCurrency(b.budget_amount);
    document.getElementById("budget-pct-text").textContent = `${b.percent_used.toFixed(1)}% utilized`;
    document.getElementById("budget-remaining-text").textContent = `Remaining: ${formatCurrency(b.remaining)}`;
    document.getElementById("budget-status-msg").textContent = b.status_message;

    // Dashboard Banner
    if (alertBox) {
      alertBox.style.display = "flex";
      if (b.status === "EXCEEDED") {
        alertBox.className = "budget-banner danger";
        alertTitle.textContent = "🚨 Budget Overdraft Alert:";
        alertDesc.textContent = b.status_message;
      } else if (b.status === "WARNING_80") {
        alertBox.className = "budget-banner warning";
        alertTitle.textContent = "⚠️ 80% Budget Threshold Reached:";
        alertDesc.textContent = b.status_message;
      } else {
        alertBox.className = "budget-banner normal";
        alertTitle.textContent = "🎉 Budget On Track:";
        alertDesc.textContent = `You have spent ${b.percent_used.toFixed(1)}% of your monthly cap. Remaining balance: ${formatCurrency(b.remaining)}.`;
      }
    }

    // Populate budget history list
    const historyTbody = document.getElementById("tbody-budget-history");
    if (historyTbody && data.history) {
      historyTbody.innerHTML = "";
      data.history.forEach(item => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${item.month.toString().padStart(2, "0")}/${item.year}</strong></td>
          <td style="text-align: right; font-weight: 600;">${formatCurrency(item.budget_amount)}</td>
          <td style="text-align: right;">${formatCurrency(item.total_spent)}</td>
          <td style="text-align: right;">${formatCurrency(item.remaining)}</td>
          <td style="text-align: right; font-weight: 600;">${item.percent_used.toFixed(1)}%</td>
          <td><span class="badge ${item.status === 'NORMAL' ? 'badge-income' : 'badge-expense'}">${item.status}</span></td>
        `;
        historyTbody.appendChild(tr);
      });
    }

  } catch (err) {
    console.error("Failed to load budget:", err);
  }
}

// Populate Category dropdowns in Modals
async function loadCategoryOptions(type, selectId) {
  try {
    const res = await fetch(`/api/categories?user_id=${currentUser.id}&type=${type}`);
    const data = await res.json();
    if (!data.success) return;

    const select = document.getElementById(selectId);
    if (!select) return;

    select.innerHTML = "";
    data.data.forEach(cat => {
      const opt = document.createElement("option");
      opt.value = cat.category_id;
      opt.textContent = `${getCategoryLabel(cat.category_name)} (${cat.ownership})`;
      select.appendChild(opt);
    });
  } catch (e) {
    console.error("Failed to fetch categories:", e);
  }
}

// Form Handlers
async function handleAddIncome(e) {
  e.preventDefault();
  const catId = parseInt(document.getElementById("inc-category").value);
  const amtStr = document.getElementById("inc-amount").value;
  const dateStr = document.getElementById("inc-date").value;
  const desc = document.getElementById("inc-desc").value;

  const res = await fetch("/api/income", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: currentUser.id,
      category_id: catId,
      amount: amtStr,
      date: dateStr,
      description: desc
    })
  });
  const data = await res.json();
  if (data.success) {
    document.getElementById("dialog-add-income").close();
    document.getElementById("form-add-income").reset();
    setDefaultDates();
    loadAllData();
    showToast("Income Recorded", `+₹ ${amtStr} recorded successfully!`, "success");
  } else {
    showToast("Error Recording Income", data.message, "error");
  }
}

async function handleAddExpense(e) {
  e.preventDefault();
  const catId = parseInt(document.getElementById("exp-category").value);
  const amtStr = document.getElementById("exp-amount").value;
  const dateStr = document.getElementById("exp-date").value;
  const desc = document.getElementById("exp-desc").value;

  const res = await fetch("/api/expense", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: currentUser.id,
      category_id: catId,
      amount: amtStr,
      date: dateStr,
      description: desc
    })
  });
  const data = await res.json();
  if (data.success) {
    document.getElementById("dialog-add-expense").close();
    document.getElementById("form-add-expense").reset();
    setDefaultDates();
    loadAllData();
    showToast("Expense Recorded", `-₹ ${amtStr} saved to your records`, "success");
    if (data.warning) {
      setTimeout(() => {
        showToast("Budget Notification", data.warning, "warning");
      }, 500);
    }
  } else {
    showToast("Error Recording Expense", data.message, "error");
  }
}

async function handleSetBudget(e) {
  e.preventDefault();
  const month = parseInt(document.getElementById("bgt-month").value);
  const year = parseInt(document.getElementById("bgt-year").value);
  const amtStr = document.getElementById("bgt-amount").value;

  const res = await fetch("/api/budget", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: currentUser.id,
      month: month,
      year: year,
      amount: amtStr
    })
  });
  const data = await res.json();
  if (data.success) {
    document.getElementById("dialog-set-budget").close();
    loadBudgetInfo();
    showToast("Budget Updated", `Monthly limit set to ₹ ${amtStr}`, "success");
  } else {
    showToast("Error Updating Budget", data.message, "error");
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById("login-username").value;
  const password = document.getElementById("login-password").value;

  const res = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: username,
      password: password
    })
  });
  const data = await res.json();
  if (data.success) {
    currentUser = {
      id: data.user.user_id,
      username: data.user.username
    };
    document.getElementById("user-name").textContent = currentUser.username;
    document.getElementById("user-avatar").textContent = currentUser.username[0].toUpperCase();
    document.getElementById("dialog-login").close();
    updateGreeting();
    loadAllData();
    showToast("Signed In", `Welcome back, ${currentUser.username}!`, "success");
  } else {
    showToast("Login Failed", data.message, "error");
  }
}

// Delete Transaction with Toast feedback
async function deleteTransaction(id, type) {
  if (!confirm(`Are you sure you want to delete ${type.toLowerCase()} record #${id}?`)) {
    return;
  }
  const res = await fetch(`/api/transaction?user_id=${currentUser.id}&id=${id}&type=${type}`, {
    method: "DELETE"
  });
  const data = await res.json();
  if (data.success) {
    loadAllData();
    showToast("Deleted", `Transaction #${id} deleted from your records`, "success");
  } else {
    showToast("Delete Failed", data.message, "error");
  }
}

function escapeHtml(text) {
  if (!text) return "";
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}
