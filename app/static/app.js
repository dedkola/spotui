const jobsList = document.getElementById("jobs-list");
const jobDetail = document.getElementById("job-detail");
const form = document.getElementById("job-form");
const formMessage = document.getElementById("form-message");
const initialJobsData = document.getElementById("initial-jobs-data");
const lastUpdated = document.getElementById("last-updated");
const selectedTitle = document.getElementById("selected-title");
const selectedStatus = document.getElementById("selected-status");
const historyCount = document.getElementById("history-count");
const queuePillLabel = document.getElementById("queue-pill-label");
const queuePillCopy = document.getElementById("queue-pill-copy");
const copyPathButton = document.getElementById("copyPathButton");
const pathValue = document.getElementById("pathValue");
const pathMirror = document.getElementById("pathMirror");

const statTotal = document.getElementById("stat-total");
const statActive = document.getElementById("stat-active");
const statCompleted = document.getElementById("stat-completed");
const statFailed = document.getElementById("stat-failed");

const queryField = document.getElementById("query");
const formatField = document.getElementById("format");
const bitrateField = document.getElementById("bitrate");
const overwriteField = document.getElementById("overwrite");
const threadsField = document.getElementById("threads");
const subdirField = document.getElementById("subdir");

let jobs = JSON.parse(initialJobsData?.textContent || "[]");
let selectedJobId = jobs[0]?.id ?? null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatCount(value) {
  return String(value).padStart(2, "0");
}

function formatDateTime(value) {
  if (!value) {
    return "Not yet";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }

  return parsed.toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function formatStatus(status) {
  return String(status || "queued").replaceAll("_", " ");
}

function statusClass(status) {
  const normalized = String(status || "queued");
  if (normalized === "running") {
    return "badge badge--running";
  }
  if (normalized === "completed") {
    return "badge badge--completed";
  }
  if (normalized === "failed") {
    return "badge badge--failed";
  }
  if (normalized === "cancelled") {
    return "badge badge--cancelled";
  }
  return "badge badge--queued";
}

function setFormMessage(message = "", tone = "") {
  formMessage.textContent = message;
  if (tone) {
    formMessage.dataset.tone = tone;
  } else {
    delete formMessage.dataset.tone;
  }
}

function jobSummaryText(job) {
  if (job.error) {
    return job.error;
  }

  const logTail = job.log_tail || [];
  const lastLine = logTail[logTail.length - 1];
  if (lastLine) {
    return lastLine;
  }

  if (job.output_directory) {
    return `Saving into ${job.output_directory}`;
  }

  return "Ready to start.";
}

function updateQueuePill(total, active, completed, failed) {
  if (!total) {
    queuePillLabel.textContent = "Ready";
    queuePillCopy.textContent = "Queue idle";
    return;
  }

  if (active) {
    queuePillLabel.textContent = `${active} active`;
    queuePillCopy.textContent = `${total} ${total === 1 ? "job" : "jobs"} in the queue`;
    return;
  }

  if (failed) {
    queuePillLabel.textContent = "Attention";
    queuePillCopy.textContent = `${failed} ${failed === 1 ? "job needs review" : "jobs need review"}`;
    return;
  }

  queuePillLabel.textContent = "Caught up";
  queuePillCopy.textContent = `${completed} completed ${completed === 1 ? "job" : "jobs"}`;
}

function updateOverview() {
  const active = jobs.filter((job) => ["queued", "running"].includes(job.status)).length;
  const completed = jobs.filter((job) => job.status === "completed").length;
  const failed = jobs.filter((job) => ["failed", "cancelled"].includes(job.status)).length;

  statTotal.textContent = jobs.length;
  statActive.textContent = active;
  statCompleted.textContent = completed;
  statFailed.textContent = failed;
  historyCount.textContent = formatCount(jobs.length);
  updateQueuePill(jobs.length, active, completed, failed);
}

function renderEmptyDetail(message) {
  selectedTitle.textContent = "Selected job";
  selectedStatus.textContent = "No selection";
  selectedStatus.className = "badge badge--empty";
  jobDetail.innerHTML = `<p class="empty-state">${escapeHtml(message)}</p>`;
}

function renderJobs() {
  updateOverview();

  if (!jobs.length) {
    selectedJobId = null;
    jobsList.innerHTML =
      '<p class="empty-state">No jobs yet. Paste a Spotify URL or search to add the first item to the queue.</p>';
    renderEmptyDetail("Pick a job from the history list to inspect its live output.");
    return;
  }

  if (!selectedJobId || !jobs.some((job) => job.id === selectedJobId)) {
    selectedJobId = jobs[0].id;
  }

  jobsList.innerHTML = jobs
    .map(
      (job) => `
        <article
          class="history-item ${job.id === selectedJobId ? "is-active" : ""}"
          data-job-id="${escapeHtml(job.id)}"
          tabindex="0"
        >
          <div class="item-copy">
            <div class="item-title">${escapeHtml(job.query)}</div>
            <div class="item-meta">${escapeHtml(jobSummaryText(job))}</div>
            <div class="item-tags">
              <span class="item-tag">${escapeHtml(job.format)}</span>
              <span class="item-tag">${escapeHtml(job.bitrate)}</span>
              <span class="item-tag">${escapeHtml(job.subdir || "root folder")}</span>
            </div>
          </div>
          <div class="${statusClass(job.status)}">${escapeHtml(formatStatus(job.status))}</div>
          <div class="time">${escapeHtml(formatDateTime(job.created_at))}</div>
        </article>
      `,
    )
    .join("");

  jobsList.querySelectorAll("[data-job-id]").forEach((element) => {
    const activate = () => {
      selectedJobId = element.dataset.jobId;
      renderJobs();
      loadJobDetail(selectedJobId);
    };

    element.addEventListener("click", activate);
    element.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activate();
      }
    });
  });
}

function renderJobDetail(job) {
  const logText = (job.log_lines || []).join("\n");
  const canCancel = job.status === "queued" || job.status === "running";

  selectedTitle.textContent = job.query;
  selectedStatus.textContent = formatStatus(job.status);
  selectedStatus.className = statusClass(job.status);

  jobDetail.innerHTML = `
    <section class="inspector-hero">
      <div class="inspector-copy">
        <span class="detail-label">Request</span>
        <strong>${escapeHtml(job.query)}</strong>
        <p class="detail-copy">${escapeHtml(job.error || jobSummaryText(job))}</p>
      </div>
      <div class="detail-actions">
        ${canCancel ? '<button id="cancel-job" class="ghost-button" type="button">Cancel job</button>' : ""}
      </div>
    </section>

    <div class="detail-grid">
      <section class="detail-card">
        <span>Created</span>
        <strong>${escapeHtml(formatDateTime(job.created_at))}</strong>
      </section>
      <section class="detail-card">
        <span>Threads</span>
        <strong>${escapeHtml(`${job.threads} threads`)}</strong>
      </section>
      <section class="detail-card">
        <span>Started</span>
        <strong>${escapeHtml(formatDateTime(job.started_at))}</strong>
      </section>
      <section class="detail-card">
        <span>Finished</span>
        <strong>${escapeHtml(formatDateTime(job.finished_at))}</strong>
      </section>
      <section class="detail-card">
        <span>Format</span>
        <strong>${escapeHtml(`${job.format} • ${job.bitrate}`)}</strong>
      </section>
      <section class="detail-card">
        <span>Target subfolder</span>
        <strong>${escapeHtml(job.subdir || "root folder")}</strong>
      </section>
      <section class="detail-card detail-card--wide">
        <span>Output directory</span>
        <strong>${escapeHtml(job.output_directory || "Waiting to resolve output path")}</strong>
      </section>
      <section class="detail-card detail-card--wide">
        <span>Command</span>
        <pre><code>${escapeHtml((job.command || []).join(" ") || "Command not built yet.")}</code></pre>
      </section>
      <section class="detail-card detail-card--wide">
        <span>Live log</span>
        <pre class="log-block">${escapeHtml(logText || "No log output yet.")}</pre>
      </section>
    </div>
  `;

  const cancelButton = document.getElementById("cancel-job");
  if (cancelButton) {
    cancelButton.addEventListener("click", async () => {
      cancelButton.disabled = true;
      try {
        const response = await fetch(`/api/jobs/${job.id}/cancel`, { method: "POST" });
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || "Unable to cancel job.");
        }

        await refreshJobs();
        await loadJobDetail(job.id);
      } catch (error) {
        setFormMessage(error instanceof Error ? error.message : "Unable to cancel job.", "error");
      } finally {
        cancelButton.disabled = false;
      }
    });
  }
}

async function loadJobDetail(jobId) {
  if (!jobId) {
    renderEmptyDetail("Pick a job from the history list to inspect its live output.");
    return;
  }

  const response = await fetch(`/api/jobs/${jobId}`);
  if (!response.ok) {
    renderEmptyDetail("Unable to load job details.");
    return;
  }

  const job = await response.json();
  renderJobDetail(job);
}

async function refreshJobs() {
  const response = await fetch("/api/jobs");
  if (!response.ok) {
    return;
  }

  const payload = await response.json();
  jobs = payload.jobs || [];
  renderJobs();

  lastUpdated.textContent = `Last refreshed ${new Date().toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  })}`;

  if (selectedJobId) {
    await loadJobDetail(selectedJobId);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setFormMessage("Queueing download...", "pending");

  const payload = {
    query: queryField.value,
    format: formatField.value,
    bitrate: bitrateField.value,
    subdir: subdirField.value,
    overwrite: overwriteField.value,
    threads: Number(threadsField.value),
  };

  try {
    const response = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await response.json();
      const detail = error.detail?.[0]?.msg || error.detail || "Unable to create job.";
      throw new Error(detail);
    }

    const job = await response.json();
    selectedJobId = job.id;
    form.reset();
    threadsField.value = "4";
    setFormMessage("Download added to the queue.", "success");
    await refreshJobs();
  } catch (error) {
    setFormMessage(error instanceof Error ? error.message : "Unable to create job.", "error");
  }
});

copyPathButton.addEventListener("click", async () => {
  const text = pathValue.textContent || "";

  if (!navigator.clipboard?.writeText) {
    setFormMessage("Clipboard access is unavailable here.", "error");
    return;
  }

  try {
    await navigator.clipboard.writeText(text);
    copyPathButton.textContent = "Copied";
    setFormMessage("Output folder copied to clipboard.", "success");
    window.setTimeout(() => {
      copyPathButton.textContent = "Copy path";
    }, 1200);
  } catch (error) {
    setFormMessage("Clipboard access is unavailable here.", "error");
  }
});

pathMirror.textContent = pathValue.textContent || "";
renderJobs();

if (selectedJobId) {
  loadJobDetail(selectedJobId);
}

lastUpdated.textContent = jobs.length ? "Queue loaded from local state." : "Waiting for queue activity.";

setInterval(refreshJobs, 4000);
