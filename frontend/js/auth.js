/* Login and registration pages. */
if (getToken()) window.location = "dashboard.html";

const loginForm = $("loginForm");
if (loginForm) loginForm.addEventListener("submit", async e => {
  e.preventDefault();
  showAlert("alert", "");
  setLoading($("submitBtn"), true, "Logging in...");
  try {
    await Api.login($("email").value, $("password").value);
    window.location = "dashboard.html";
  } catch (err) { showAlert("alert", err.message); }
  finally { setLoading($("submitBtn"), false); }
});

const registerForm = $("registerForm");
if (registerForm) registerForm.addEventListener("submit", async e => {
  e.preventDefault();
  showAlert("alert", "");
  if ($("password").value !== $("confirm").value) return showAlert("alert", "Passwords do not match.");
  setLoading($("submitBtn"), true, "Creating account...");
  try {
    await Api.register($("name").value, $("email").value, $("password").value, $("confirm").value);
    await Api.login($("email").value, $("password").value);
    window.location = "dashboard.html";
  } catch (err) { showAlert("alert", err.message); setLoading($("submitBtn"), false); }
});
