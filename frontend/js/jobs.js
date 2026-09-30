/* Jobs page: recommendations, search and management (CRUD). */

let allJobs = [];

if (requireAuth()) init();

/* ---------- score helpers ---------- */

function scoreClass(score) {
  score = Number(score) || 0;

  if (score >= 80) return "good";
  if (score >= 60) return "medium";
  return "bad";
}

function scoreColorClass(score) {
  const status = scoreClass(score);

  if (status === "good") return "success";
  if (status === "medium") return "warning";
  return "danger";
}

function scoreLabel(score) {
  const status = scoreClass(score);

  if (status === "good") return "Strong Match";
  if (status === "medium") return "Moderate Match";
  return "Low Match";
}

function scoreCircle(score, label = "Match") {
  score = Math.max(
    0,
    Math.min(100, Number(score) || 0)
  );

  const status = scoreClass(score);

  return `
    <div
      class="circular-score ${status}"
      style="--score: ${score};"
      title="${score}% ${label}"
      aria-label="${score}% ${label}"
    >
      <div class="score-content">
        <span class="score-number">${score}%</span>
        <span class="score-label">${label}</span>
      </div>
    </div>
  `;
}

/* ---------- init ---------- */

function init() {

  document
    .querySelectorAll(".tab")
    .forEach(t =>
      t.addEventListener(
        "click",
        () => showTab(t.dataset.tab)
      )
    );

  $("recResume").addEventListener(
    "change",
    () => {
      setResumeId($("recResume").value);
      loadRecommendations(false);
    }
  );

  $("recRefresh").addEventListener(
    "click",
    () => loadRecommendations(true)
  );

  $("searchForm").addEventListener(
    "submit",
    e => {
      e.preventDefault();
      runSearch();
    }
  );

  $("searchReset").addEventListener(
    "click",
    () => {
      $("searchForm").reset();
      runSearch();
    }
  );

  $("jobForm").addEventListener(
    "submit",
    saveJob
  );

  $("jobCancel").addEventListener(
    "click",
    resetForm
  );

  setupRecommendations();
  runSearch();
  loadManage();
}

/* ---------- tabs ---------- */

function showTab(name) {

  document
    .querySelectorAll(".tab")
    .forEach(t =>
      t.classList.toggle(
        "active",
        t.dataset.tab === name
      )
    );

  ["rec", "search", "manage"].forEach(n =>
    $("tab-" + n).classList.toggle(
      "hidden",
      n !== name
    )
  );

  showAlert("alert", "");
}

/* ---------- recommendations ---------- */

async function setupRecommendations() {

  try {

    const resumes =
      await Api.listResumes();

    if (!resumes.length) {

      $("recList").innerHTML = `
        <div class="card empty-state">

          <div class="icon-box warning">
            📄
          </div>

          <h3>No resume found</h3>

          <p class="muted">
            Upload your resume first to receive
            personalized job recommendations.
          </p>

          <a class="btn" href="resume.html">
            📤 Upload Resume
          </a>

        </div>
      `;

      $("recRefresh").disabled = true;

      return;
    }

    const saved = getResumeId();

    $("recResume").innerHTML =
      resumes
        .map(r => `
          <option
            value="${r.id}"
            ${
              String(r.id) === String(saved)
                ? "selected"
                : ""
            }
          >
            ${esc(r.filename)}
          </option>
        `)
        .join("");

    setResumeId(
      $("recResume").value
    );

    loadRecommendations(false);

  } catch (err) {

    showAlert(
      "alert",
      err.message
    );
  }
}

async function loadRecommendations(refresh) {

  $("recList").innerHTML =
    loadingHtml(
      "Matching your resume with available jobs..."
    );

  setLoading(
    $("recRefresh"),
    refresh,
    "Calculating..."
  );

  try {

    const matches =
      await Api.getRecommendations(
        $("recResume").value,
        refresh
      );

    if (!matches.length) {

      $("recList").innerHTML = `
        <div class="card empty-state">

          <div class="icon-box warning">
            🔎
          </div>

          <h3>No jobs available</h3>

          <p class="muted">
            Add jobs from the Manage Jobs tab
            to generate recommendations.
          </p>

        </div>
      `;

      return;
    }

    $("recList").innerHTML =
      matches
        .map(m => {

          const score =
            Math.max(
              0,
              Math.min(
                100,
                Number(m.match_score) || 0
              )
            );

          const status =
            scoreClass(score);

          const iconStatus =
            scoreColorClass(score);

          const label =
            scoreLabel(score);

          const matchedCount =
            m.matched_skills?.length || 0;

          const missingCount =
            m.missing_skills?.length || 0;

          const totalRequired =
            matchedCount + missingCount;

          const coverage =
            totalRequired > 0
              ? Math.round(
                  (matchedCount / totalRequired) * 100
                )
              : 0;

          return `
            <div class="card job-card">

              <!-- Job header -->
              <div
                class="row"
                style="
                  align-items:center;
                  gap:25px;
                "
              >

                <div style="flex:1">

                  <div
                    style="
                      display:flex;
                      align-items:center;
                      gap:12px;
                      margin-bottom:10px;
                    "
                  >

                    <div
                      class="icon-box ${iconStatus}"
                      title="Job"
                    >
                      💼
                    </div>

                    <div>

                      <h3 style="margin:0;">
                        ${esc(m.job_title)}
                      </h3>

                      <div class="muted">
                        ${esc(m.company)}
                        &middot;
                        ${esc(m.location)}
                      </div>

                    </div>

                  </div>

                  <div class="muted">

                    🎓
                    ${esc(m.experience_level)}

                    <span style="margin:0 6px;">
                      •
                    </span>

                    💼
                    ${esc(m.job_type)}

                  </div>

                </div>

                <!-- Circular match score -->
                <div
                  style="
                    display:flex;
                    flex-direction:column;
                    align-items:center;
                    justify-content:center;
                    gap:8px;
                    min-width:135px;
                  "
                >

                  ${scoreCircle(score, "Match")}

                  <span
                    class="${status}"
                    style="
                      font-weight:800;
                      font-size:.82rem;
                    "
                  >
                    ${label}
                  </span>

                </div>

              </div>

              <!-- Job Description -->
              <div
                style="
                  margin-top:18px;
                  padding:16px;
                  border-radius:12px;
                  background:#faf5ff;
                  border:1px solid var(--border);
                "
              >

                <strong>
                  📄 Job Description
                </strong>

                <p
                  class="muted"
                  style="
                    margin:8px 0 0;
                    line-height:1.7;
                  "
                >
                  ${esc(
                    m.description ||
                    "No job description provided."
                  )}
                </p>

              </div>

              <!-- Divider -->
              <hr
                style="
                  border:0;
                  border-top:1px solid var(--border);
                  margin:20px 0;
                "
              >

              <!-- Matched skills -->
              <div>

                <strong>
                  <span class="good">✓</span>
                  Matched skills
                </strong>

                <div style="margin-top:8px;">
                  ${
                    chips(
                      m.matched_skills,
                      "ok"
                    )
                  }
                </div>

              </div>

              <!-- Missing skills -->
              <div style="margin-top:15px;">

                <strong>
                  <span class="bad">✕</span>
                  Missing skills
                </strong>

                <div style="margin-top:8px;">
                  ${
                    chips(
                      m.missing_skills,
                      "miss"
                    )
                  }
                </div>

              </div>

              <!-- Match Breakdown -->
              <div
                style="
                  margin-top:18px;
                  padding:16px;
                  border-radius:12px;
                  background:var(--primary-light);
                  border:1px solid var(--border);
                "
              >

                <strong>
                  🎯 Match Breakdown
                </strong>

                <div
                  style="
                    display:flex;
                    gap:12px;
                    flex-wrap:wrap;
                    margin-top:10px;
                  "
                >

                  <span class="chip ok">
                    ✓
                    ${matchedCount}
                    matched
                  </span>

                  <span class="chip miss">
                    ✕
                    ${missingCount}
                    missing
                  </span>

                  <span class="chip">
                    📊
                    ${coverage}% coverage
                  </span>

                </div>

                <p
                  class="muted"
                  style="
                    margin:10px 0 0;
                  "
                >
                  ${matchedCount}
                  /
                  ${totalRequired}
                  required skills matched
                </p>

              </div>

              <!-- Why this match -->
              <div
                class="alert info"
                style="margin-top:18px;"
              >

                <strong>
                  💡 Why this match?
                </strong>

                <div style="margin-top:7px;">
                  ${esc(m.explanation)}
                </div>

              </div>

            </div>
          `;
        })
        .join("");

  } catch (err) {

    $("recList").innerHTML = "";

    showAlert(
      "alert",
      err.message
    );

  } finally {

    setLoading(
      $("recRefresh"),
      false
    );
  }
}

/* ---------- search ---------- */

function jobsTable(jobs) {

  if (!jobs.length) {

    return `
      <div class="card empty-state">

        <div class="icon-box warning">
          🔎
        </div>

        <p class="muted">
          No jobs found.
        </p>

      </div>
    `;
  }

  return `
    <div class="card">

      <div class="table-wrapper">

        <table>

          <thead>

            <tr>
              <th>💼 Title</th>
              <th>🏢 Company</th>
              <th>📍 Location</th>
              <th>🎓 Level</th>
              <th>⏱ Type</th>
              <th>🛠 Required Skills</th>
            </tr>

          </thead>

          <tbody>

            ${jobs
              .map(j => `
                <tr>

                  <td>
                    <strong>
                      ${esc(j.title)}
                    </strong>
                  </td>

                  <td>
                    ${esc(j.company)}
                  </td>

                  <td>
                    ${esc(j.location)}
                  </td>

                  <td>
                    ${esc(j.experience_level)}
                  </td>

                  <td>
                    ${esc(j.job_type)}
                  </td>

                  <td>
                    ${chips(j.required_skills)}
                  </td>

                </tr>
              `)
              .join("")}

          </tbody>

        </table>

      </div>

    </div>
  `;
}

async function runSearch() {

  $("searchList").innerHTML =
    loadingHtml("Searching jobs...");

  try {

    const jobs =
      await Api.searchJobs({

        title:
          $("s_title").value,

        company:
          $("s_company").value,

        location:
          $("s_location").value,

        skill:
          $("s_skill").value,

        experience_level:
          $("s_level").value,

        job_type:
          $("s_type").value

      });

    $("searchList").innerHTML = `

      <div
        style="
          display:flex;
          align-items:center;
          gap:8px;
          margin-bottom:10px;
        "
      >

        <span
          class="icon-box cyan"
          style="
            width:34px;
            height:34px;
            font-size:16px;
          "
        >
          🔎
        </span>

        <span class="muted">
          ${jobs.length} job(s) found
        </span>

      </div>

      ${jobsTable(jobs)}

    `;

  } catch (err) {

    $("searchList").innerHTML = "";

    showAlert(
      "alert",
      err.message
    );
  }
}

/* ---------- management ---------- */

async function loadManage() {

  try {

    allJobs =
      await Api.getJobs();

    $("manageList").innerHTML =
      allJobs.length

        ? `
          <div class="table-wrapper">

            <table>

              <thead>

                <tr>
                  <th>💼 Title</th>
                  <th>🏢 Company</th>
                  <th>📍 Location</th>
                  <th>🛠 Skills</th>
                  <th>⚙ Actions</th>
                </tr>

              </thead>

              <tbody>

                ${allJobs
                  .map(j => `
                    <tr>

                      <td>
                        <strong>
                          ${esc(j.title)}
                        </strong>
                      </td>

                      <td>
                        ${esc(j.company)}
                      </td>

                      <td>
                        ${esc(j.location)}
                      </td>

                      <td>
                        ${chips(
                          j.required_skills
                        )}
                      </td>

                      <td
                        style="
                          white-space:nowrap;
                        "
                      >

                        <button
                          class="btn small secondary"
                          data-edit="${j.id}"
                        >
                          ✏️ Edit
                        </button>

                        <button
                          class="btn small danger"
                          data-del="${j.id}"
                        >
                          🗑 Delete
                        </button>

                      </td>

                    </tr>
                  `)
                  .join("")}

              </tbody>

            </table>

          </div>
        `

        : `
          <div class="card empty-state">

            <div class="icon-box warning">
              💼
            </div>

            <p class="muted">
              No jobs yet.
            </p>

          </div>
        `;

    document
      .querySelectorAll("[data-edit]")
      .forEach(b =>
        b.addEventListener(
          "click",
          () =>
            editJob(
              Number(b.dataset.edit)
            )
        )
      );

    document
      .querySelectorAll("[data-del]")
      .forEach(b =>
        b.addEventListener(
          "click",
          () =>
            removeJob(
              Number(b.dataset.del)
            )
        )
      );

  } catch (err) {

    showAlert(
      "alert",
      err.message
    );
  }
}

/* ---------- job form ---------- */

function resetForm() {

  $("jobForm").reset();

  $("j_id").value = "";

  $("formTitle").textContent =
    "Add a job";

  $("jobCancel")
    .classList
    .add("hidden");
}

function editJob(id) {

  const j =
    allJobs.find(
      x => x.id === id
    );

  if (!j) return;

  $("j_id").value =
    j.id;

  $("j_title").value =
    j.title;

  $("j_company").value =
    j.company;

  $("j_location").value =
    j.location;

  $("j_level").value =
    j.experience_level;

  $("j_type").value =
    j.job_type;

  $("j_skills").value =
    (j.required_skills || [])
      .join(", ");

  $("j_desc").value =
    j.description;

  $("formTitle").textContent =
    "Edit job #" + j.id;

  $("jobCancel")
    .classList
    .remove("hidden");

  window.scrollTo({
    top: 0,
    behavior: "smooth"
  });
}

async function saveJob(e) {

  e.preventDefault();

  showAlert(
    "alert",
    ""
  );

  const job = {

    title:
      $("j_title").value,

    company:
      $("j_company").value,

    location:
      $("j_location").value,

    experience_level:
      $("j_level").value,

    job_type:
      $("j_type").value,

    description:
      $("j_desc").value,

    required_skills:
      $("j_skills")
        .value
        .split(",")
        .map(
          s => s.trim()
        )
        .filter(Boolean)

  };

  setLoading(
    $("jobSave"),
    true,
    "Saving..."
  );

  try {

    const id =
      $("j_id").value;

    if (id) {

      await Api.updateJob(
        id,
        job
      );

    } else {

      await Api.createJob(
        job
      );
    }

    showAlert(
      "alert",
      id
        ? "Job updated successfully."
        : "Job added successfully.",
      "success"
    );

    resetForm();

    await loadManage();

    runSearch();

  } catch (err) {

    showAlert(
      "alert",
      err.message
    );

  } finally {

    setLoading(
      $("jobSave"),
      false
    );
  }
}

/* ---------- delete ---------- */

async function removeJob(id) {

  if (
    !confirm(
      "Delete this job?"
    )
  ) {
    return;
  }

  try {

    await Api.deleteJob(id);

    showAlert(
      "alert",
      "Job deleted successfully.",
      "success"
    );

    await loadManage();

    runSearch();

  } catch (err) {

    showAlert(
      "alert",
      err.message
    );
  }
}