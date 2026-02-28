const state = {
  token: localStorage.getItem("hr_ai_token") || "",
  user: null,
  lastPolicyResponseId: null,
};

const statusBar = document.getElementById("statusBar");
const sessionBadge = document.getElementById("sessionBadge");

function setStatus(message, isError = false) {
  statusBar.textContent = message;
  statusBar.style.borderColor = isError ? "#d3a798" : "#bdd7ca";
  statusBar.style.background = isError ? "#fff3ef" : "#f3faf4";
}

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function renderOutput(elId, content) {
  const el = document.getElementById(elId);
  el.textContent = typeof content === "string" ? content : pretty(content);
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

async function apiRequest(path, options = {}, withAuth = true) {
  const headers = { ...(options.headers || {}) };

  if (withAuth && state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const response = await fetch(path, { ...options, headers });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json().catch(() => ({}))
    : await response.text().catch(() => "");

  if (!response.ok) {
    const detail = payload?.detail || payload || `Request failed (${response.status})`;
    throw new Error(typeof detail === "string" ? detail : pretty(detail));
  }

  return payload;
}

function applyRoleVisibility() {
  const role = state.user?.role || "";
  document.querySelectorAll("[data-roles]").forEach((el) => {
    const allowed = (el.getAttribute("data-roles") || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const visible = role && allowed.includes(role);
    el.classList.toggle("hidden-by-role", !visible);
  });
}

function setAuthenticatedUi(isAuth) {
  const authText = isAuth
    ? `Session: ${state.user?.username || "authenticated"} (${state.user?.role || "-"})`
    : "Session: Signed out";
  sessionBadge.textContent = authText;

  document.getElementById("accountName").textContent = isAuth
    ? state.user.full_name
    : "Not authenticated";
  document.getElementById("accountRole").textContent = `Role: ${isAuth ? state.user.role : "-"}`;
  document.getElementById("accountId").textContent = `ID: ${isAuth ? state.user.user_id : "-"}`;

  applyRoleVisibility();
}

async function refreshProfile() {
  if (!state.token) {
    state.user = null;
    setAuthenticatedUi(false);
    return;
  }

  try {
    const me = await apiRequest("/auth/me");
    state.user = me;
    setAuthenticatedUi(true);
    setStatus(`Signed in as ${me.username} (${me.role}).`);
  } catch (error) {
    localStorage.removeItem("hr_ai_token");
    state.token = "";
    state.user = null;
    setAuthenticatedUi(false);
    setStatus(error.message, true);
  }
}

function initTabs() {
  const tabs = document.querySelectorAll(".tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(`tab-${tab.dataset.tab}`).classList.add("active");
    });
  });
}

function initDefaults() {
  document.getElementById("leaveStart").value = todayIso();
  document.getElementById("leaveEnd").value = todayIso();
  document.getElementById("onboardingStart").value = todayIso();
}

function registerAuthHandlers() {
  document.getElementById("loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    try {
      const tokenPayload = await apiRequest(
        "/auth/token",
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ username, password }),
        },
        false,
      );

      state.token = tokenPayload.access_token;
      localStorage.setItem("hr_ai_token", state.token);
      await refreshProfile();
      await refreshKpis();
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  document.getElementById("logoutBtn").addEventListener("click", () => {
    localStorage.removeItem("hr_ai_token");
    state.token = "";
    state.user = null;
    state.lastPolicyResponseId = null;
    document.getElementById("feedbackAccurate").disabled = true;
    document.getElementById("feedbackInaccurate").disabled = true;
    setAuthenticatedUi(false);
    setStatus("Signed out.");
  });
}

function registerPolicyHandlers() {
  document.getElementById("policyQueryForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const question = document.getElementById("policyQuestion").value;
      const result = await apiRequest("/policy/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      state.lastPolicyResponseId = result.response_id;
      renderOutput("policyResult", result);
      document.getElementById("feedbackAccurate").disabled = false;
      document.getElementById("feedbackInaccurate").disabled = false;
      setStatus("Policy guidance generated.");
      await refreshKpis();
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  async function submitFeedback(accurate) {
    if (!state.lastPolicyResponseId) {
      setStatus("No policy response available for feedback.", true);
      return;
    }

    try {
      const comment = document.getElementById("feedbackComment").value;
      const result = await apiRequest("/policy/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          response_id: state.lastPolicyResponseId,
          accurate,
          comment,
        }),
      });

      renderOutput("feedbackResult", result);
      setStatus("Feedback submitted.");
      await refreshKpis();
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  document.getElementById("feedbackAccurate").addEventListener("click", () => submitFeedback(true));
  document
    .getElementById("feedbackInaccurate")
    .addEventListener("click", () => submitFeedback(false));
}

async function refreshLeaveList() {
  const leave = await apiRequest("/workflows/leave");
  renderOutput("leaveList", leave.length ? leave : "No leave records found.");
}

async function refreshDocumentList() {
  const docs = await apiRequest("/workflows/documents");
  const wrapped = {
    requests: docs,
    instruction: state.user?.role === "HR" ? "Use request IDs below in the fulfill action buttons." : "",
  };
  renderOutput("docList", docs.length ? wrapped : "No document requests found.");
}

async function refreshOnboardingList() {
  const tasks = await apiRequest("/workflows/onboarding");
  renderOutput("onboardingList", tasks.length ? tasks : "No onboarding tasks found.");
}

function registerWorkflowHandlers() {
  document.getElementById("leaveCreateForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const payload = {
        start_date: document.getElementById("leaveStart").value,
        end_date: document.getElementById("leaveEnd").value,
        reason: document.getElementById("leaveReason").value,
      };
      const result = await apiRequest("/workflows/leave", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setStatus(`Leave request created (${result.request_id}).`);
      await refreshLeaveList();
      await refreshKpis();
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  document.getElementById("refreshLeave").addEventListener("click", async () => {
    try {
      await refreshLeaveList();
      setStatus("Leave list refreshed.");
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  document.getElementById("leaveDecisionForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const requestId = document.getElementById("decisionRequestId").value.trim();
      const approve = document.getElementById("decisionAction").value === "approve";
      const notes = document.getElementById("decisionNotes").value;
      await apiRequest(`/workflows/leave/${requestId}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approve, notes }),
      });
      setStatus(`Leave decision submitted for ${requestId}.`);
      await refreshLeaveList();
      await refreshKpis();
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  document.getElementById("docRequestForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const payload = {
        document_type: document.getElementById("docType").value,
        purpose: document.getElementById("docPurpose").value,
      };
      await apiRequest("/workflows/documents/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setStatus("Document request submitted.");
      await refreshDocumentList();
      await refreshKpis();
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  document.getElementById("refreshDocs").addEventListener("click", async () => {
    try {
      await refreshDocumentList();
      setStatus("Document requests refreshed.");
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  document.getElementById("onboardingForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const payload = {
        employee_id: document.getElementById("onboardingEmployeeId").value,
        start_date: document.getElementById("onboardingStart").value,
      };
      await apiRequest("/workflows/onboarding/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setStatus("Onboarding workflow triggered.");
      await refreshOnboardingList();
      await refreshKpis();
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  document.getElementById("refreshOnboarding").addEventListener("click", async () => {
    try {
      await refreshOnboardingList();
      setStatus("Onboarding tasks refreshed.");
    } catch (error) {
      setStatus(error.message, true);
    }
  });
}

function registerGovernanceHandlers() {
  document.getElementById("consentForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const targetUserId = document.getElementById("consentUserId").value.trim();
      const gdprConsent = document.getElementById("consentValue").checked;
      const result = await apiRequest(`/governance/consent/${targetUserId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gdpr_consent: gdprConsent }),
      });
      renderOutput("governanceOutput", result);
      setStatus("Consent updated.");
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  document.getElementById("sarForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const targetUserId = document.getElementById("sarUserId").value.trim();
      const result = await apiRequest(`/governance/subject-access/${targetUserId}`);
      renderOutput("governanceOutput", result);
      setStatus("Subject access data loaded.");
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  document.getElementById("erasureForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const targetUserId = document.getElementById("erasureUserId").value.trim();
      const result = await apiRequest(`/governance/erase/${targetUserId}`, {
        method: "POST",
      });
      renderOutput("governanceOutput", result);
      setStatus("Erasure/anonymization completed.");
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  document.getElementById("retentionForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const retentionDays = Number(document.getElementById("retentionDays").value);
      const result = await apiRequest(`/governance/retention/cleanup?retention_days=${retentionDays}`, {
        method: "POST",
      });
      renderOutput("governanceOutput", result);
      setStatus("Retention cleanup executed.");
    } catch (error) {
      setStatus(error.message, true);
    }
  });
}

async function refreshKpis() {
  const data = await apiRequest("/analytics/kpis");
  document.getElementById("kpiUsage").textContent = `${data.usage.total_policy_queries} queries | ${data.usage.unique_users} users`;
  document.getElementById("kpiAccuracy").textContent = `${(data.response_accuracy.accuracy_rate * 100).toFixed(1)}%`;
  document.getElementById("kpiAutomation").textContent = `${(data.automation.automation_rate * 100).toFixed(1)}%`;
}

async function refreshEvents() {
  const events = await apiRequest("/analytics/events?limit=80");
  renderOutput("eventsOutput", events.length ? events : "No events found.");
}

function registerAnalyticsHandlers() {
  document.getElementById("refreshKpi").addEventListener("click", async () => {
    try {
      await refreshKpis();
      setStatus("KPI dashboard refreshed.");
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  const refreshEventsBtn = document.getElementById("refreshEvents");
  refreshEventsBtn.addEventListener("click", async () => {
    try {
      await refreshEvents();
      setStatus("Event log loaded.");
    } catch (error) {
      setStatus(error.message, true);
    }
  });
}

async function tryInitialLoads() {
  if (!state.user) {
    return;
  }

  const actions = [refreshKpis, refreshLeaveList, refreshDocumentList, refreshOnboardingList];
  if (state.user.role === "HR") {
    actions.push(refreshEvents);
  }

  for (const action of actions) {
    try {
      await action();
    } catch {
      // Keep UI responsive even if individual widgets fail due to role restrictions or empty state.
    }
  }
}

async function bootstrap() {
  initTabs();
  initDefaults();
  registerAuthHandlers();
  registerPolicyHandlers();
  registerWorkflowHandlers();
  registerGovernanceHandlers();
  registerAnalyticsHandlers();

  await refreshProfile();
  await tryInitialLoads();
}

bootstrap();
