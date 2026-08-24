
document.addEventListener("DOMContentLoaded", () => {

  const toggle = document.getElementById("togglePassword");
  const password = document.getElementById("password");
  const form = document.getElementById("loginForm");
  const btn = document.getElementById("loginBtn");

  // Toggle password
  toggle.addEventListener("click", () => {
    const hidden = password.type === "password";
    password.type = hidden ? "text" : "password";
    toggle.classList.toggle("fa-eye");
    toggle.classList.toggle("fa-eye-slash");
  });

  // Prevent spam submit
  form.addEventListener("submit", () => {
    btn.innerHTML = "Signing in...";
    btn.disabled = true;
  });

});