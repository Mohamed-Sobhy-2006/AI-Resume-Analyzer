/* Dashboard: numbers and summaries from /api/recommendations/dashboard. */

if (requireAuth()) load();

function scoreClass(score) {

  score = Number(score) || 0;

  if (score >= 80) return "good";

  if (score >= 60) return "medium";

  return "bad";
}

function scoreCircle(score, label = "Match") {

  score = Math.max(
    0,
    Math.min(100, Number(score) || 0)
  );

  const status =
    scoreClass(score);

  return `
    <div
      class="circular-score ${status}"
      style="--score:${score};"
      title="${score}% ${label}"
    >

      <div class="score-content">

        <span class="score-number">
          ${score}%
        </span>

        <span class="score-label">
          ${label}
        </span>

      </div>

    </div>
  `;
}

function statCard(icon, label, value, type = "") {

  return `
    <div class="stat-card">

      <div
        class="icon-box ${type}"
        style="margin-bottom:12px;"
      >
        ${icon}
      </div>

      <div class="muted">
        ${label}
      </div>

      <div class="stat">
        ${value}
      </div>

    </div>
  `;
}

async function load() {

  try {

    const d =
      await Api.getDashboard();

    if (!d.ai_configured) {

      showAlert(
        "alert",
        "AI service is not configured. The app is running in fallback mode (keyword analysis and knowledge-base answers).",
        "warn"
      );
    }

    /* ---------- no resume ---------- */

    if (!d.resume_count) {

      $("content").innerHTML = `

        <div class="card hero">

          <div class="hero .big-ico">
            📄
          </div>

          <div class="icon-box">
            📄
          </div>

          <h2>
            Welcome to AI Resume Analyzer!
          </h2>

          <p class="muted">
            Upload your resume to analyze your skills,
            discover matching jobs and get career advice.
          </p>

          <a
            class="btn"
            href="resume.html"
          >
            📤 Upload Your Resume
          </a>

        </div>

      `;

      return;
    }

    const a =
      d.latest_analysis;

    const highestScore =
      Number(d.highest_match_score) || 0;

    const highestStatus =
      scoreClass(highestScore);

    $("content").innerHTML = `

      <!-- =========================
           STATISTICS
      ========================== -->

      <div class="grid cols-4">

        ${statCard(
          "📄",
          "Uploaded resumes",
          d.resume_count,
          "cyan"
        )}

        <div class="stat-card"
             style="
               display:flex;
               align-items:center;
               justify-content:space-between;
               gap:15px;
             ">

          <div>

            <div class="muted">
              Highest match
            </div>

            <div
              class="${highestStatus}"
              style="
                font-size:.85rem;
                font-weight:800;
                margin-top:6px;
              "
            >
              ${
                highestStatus === "good"
                  ? "Strong Match"
                  : highestStatus === "medium"
                  ? "Moderate Match"
                  : "Low Match"
              }
            </div>

          </div>

          ${scoreCircle(
            highestScore,
            "Match"
          )}

        </div>

        ${statCard(
          "🛠️",
          "Skills detected",
          a
            ? a.technical_skills.length
            : 0,
          "success"
        )}

        <div class="stat-card">

          <div
            class="icon-box warning"
            style="margin-bottom:12px;"
          >
            📅
          </div>

          <div class="muted">
            Latest resume
          </div>

          <div style="
            margin-top:7px;
            font-weight:700;
          ">
            ${esc(
              d.latest_resume.filename
            )}
          </div>

          <span class="muted">
            ${formatDate(
              d.latest_resume.uploaded_at
            )}
          </span>

        </div>

      </div>


      <!-- =========================
           MAIN CONTENT
      ========================== -->

      <div
        class="grid cols-2"
        style="margin-top:20px;"
      >

        <!-- Latest Analysis -->

        <div class="card">

          <div style="
            display:flex;
            align-items:center;
            gap:12px;
            margin-bottom:15px;
          ">

            <div class="icon-box success">
              🧠
            </div>

            <h2 style="margin:0;">
              Latest Analysis
            </h2>

          </div>

          ${
            a

            ? `

              <p>
                ${esc(a.summary)}
              </p>

              <div style="margin-top:18px;">

                <h3>
                  💪 Strengths
                </h3>

                ${bullets(a.strengths)}

              </div>

              <div style="margin-top:18px;">

                <h3>
                  ⚠️ Weaknesses
                </h3>

                ${bullets(a.weaknesses)}

              </div>

              <a
                class="btn small"
                href="analysis.html"
              >
                🔍 View Full Analysis
              </a>

            `

            : `

              <div class="alert warn">
                ⚠️ Resume has not been analyzed yet.
              </div>

              <a
                class="btn small"
                href="analysis.html"
              >
                🧠 Analyze Resume
              </a>

            `
          }

        </div>


        <!-- Top Matching Jobs -->

        <div class="card">

          <div style="
            display:flex;
            align-items:center;
            gap:12px;
            margin-bottom:15px;
          ">

            <div class="icon-box">
              💼
            </div>

            <h2 style="margin:0;">
              Top Matching Jobs
            </h2>

          </div>

          ${
            d.top_matches.length

            ? `

              <div class="table-wrapper">

                <table>

                  <thead>

                    <tr>
                      <th>Job</th>
                      <th>Score</th>
                    </tr>

                  </thead>

                  <tbody>

                    ${d.top_matches.map(m => {

                      const score =
                        Number(m.match_score) || 0;

                      const status =
                        scoreClass(score);

                      return `

                        <tr>

                          <td>

                            <strong>
                              ${esc(m.job_title)}
                            </strong>

                            <br>

                            <span class="muted">
                              ${esc(m.company)}
                            </span>

                          </td>

                          <td>

                            <div style="
                              display:flex;
                              align-items:center;
                              gap:12px;
                            ">

                              ${scoreCircle(
                                score,
                                "Match"
                              )}

                            </div>

                          </td>

                        </tr>

                      `;

                    }).join("")}

                  </tbody>

                </table>

              </div>

              <p style="margin-top:18px;">

                <a
                  class="btn small"
                  href="jobs.html"
                >
                  💼 View All Jobs
                </a>

              </p>

            `

            : `

              <div class="alert info">
                💡 Analyze a resume to see matching jobs.
              </div>

            `
          }

        </div>


        <!-- Missing Skills -->

        <div class="card">

          <div style="
            display:flex;
            align-items:center;
            gap:12px;
            margin-bottom:15px;
          ">

            <div class="icon-box danger">
              🎯
            </div>

            <h2 style="margin:0;">
              Missing Skills
            </h2>

          </div>

          ${
            d.missing_skills &&
            d.missing_skills.length

            ? chips(
                d.missing_skills,
                "miss"
              )

            : `
              <div class="alert success">
                🎉 No major missing skills detected.
              </div>
            `
          }

        </div>


        <!-- Career Recommendations -->

        <div class="card">

          <div style="
            display:flex;
            align-items:center;
            gap:12px;
            margin-bottom:15px;
          ">

            <div class="icon-box warning">
              🚀
            </div>

            <h2 style="margin:0;">
              Career Recommendations
            </h2>

          </div>

          ${bullets(
            d.career_recommendations
          )}

          <a
            class="btn small"
            href="career.html"
          >
            🤖 Ask Career Advisor
          </a>

        </div>

      </div>

    `;

  } catch (err) {

    showAlert(
      "alert",
      err.message
    );

    $("content").innerHTML = "";
  }
}