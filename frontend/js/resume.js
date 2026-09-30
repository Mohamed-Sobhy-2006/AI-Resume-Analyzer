/* Resume upload page. */
if (requireAuth()) refresh();

$("uploadForm").addEventListener("submit", async e => {
  e.preventDefault();
  showAlert("alert", "");
  const file = $("file").files[0];
  if (!file) return showAlert("alert", "Please choose a file.");
  if (!/\.(pdf|docx)$/i.test(file.name)) return showAlert("alert", "Only PDF and DOCX files are supported.");
  setLoading($("uploadBtn"), true, "Uploading & analyzing...");
  try {
    const resume = await Api.uploadResume(file);
    setResumeId(resume.id);
    await Api.analyzeResume(resume.id);
    window.location = "analysis.html";
  } catch (err) { showAlert("alert", err.message); setLoading($("uploadBtn"), false); }
});

async function refresh() {
  try {
    const resumes = await Api.listResumes();
    if (!resumes.length) { $("list").innerHTML = `<p class="muted">No resumes uploaded yet.</p>`; return; }
    $("list").innerHTML = `<table><tr><th>File</th><th>Uploaded</th><th>Words</th><th></th></tr>${resumes.map(r => `
      <tr><td>${esc(r.filename)}</td><td>${formatDate(r.uploaded_at)}</td><td>${r.word_count}</td>
      <td><a class="btn small" href="analysis.html" data-use="${r.id}">View analysis</a>
      <button class="btn small danger" data-del="${r.id}">Delete</button></td></tr>`).join("")}</table>`;
    document.querySelectorAll("[data-use]").forEach(a => a.addEventListener("click", () => setResumeId(a.dataset.use)));
    document.querySelectorAll("[data-del]").forEach(b => b.addEventListener("click", async () => {
      if (!confirm("Delete this resume and its analysis?")) return;
      try { await Api.deleteResume(b.dataset.del); refresh(); } catch (err) { showAlert("alert", err.message); }
    }));
  } catch (err) { showAlert("alert", err.message); }
}
