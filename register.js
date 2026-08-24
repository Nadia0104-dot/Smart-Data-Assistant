document.addEventListener("DOMContentLoaded", () => {
    const usernameInput = document.getElementById("username");
    const usernameStatus = document.getElementById("usernameStatus");
    const password = document.getElementById("password");
    const confirm = document.getElementById("confirm_password");
    const strengthBar = document.getElementById("strengthBar");
    const strengthText = document.getElementById("strengthText");
    const confirmStatus = document.getElementById("confirmStatus");
    const form = document.getElementById("registerForm");
    const toggle = document.getElementById("togglePassword");

    // Toggle password visibility
    toggle.addEventListener("click", () => {
        const hidden = password.type === "password";
        password.type = hidden ? "text" : "password";
        toggle.textContent = hidden ? "🙈" : "👁️";
        toggle.classList.add('toggle-anim');
        setTimeout(() => toggle.classList.remove('toggle-anim'), 300);
    });

    // Username availability
    usernameInput.addEventListener("blur", () => {
        const username = usernameInput.value.trim();
        if(!username) return;
        fetch(`/check_username?username=${username}`)
            .then(res => res.json())
            .then(data => {
                usernameStatus.textContent = data.available ? "Username available" : "Username already taken";
                usernameStatus.style.color = data.available ? "#00ff88" : "#ff5d2d";
            });
    });

    // Password strength
    password.addEventListener("input", () => {
        const val = password.value;
        let strength = 0;
        if(val.length >= 8) strength++;
        if(/[A-Z]/.test(val)) strength++;
        if(/[a-z]/.test(val)) strength++;
        if(/\d/.test(val)) strength++;
        if(/[@$!%*?&]/.test(val)) strength++;

        switch(strength){
            case 0: strengthBar.style.width="0%"; strengthText.textContent=""; break;
            case 1: strengthBar.style.width="20%"; strengthBar.style.background="#ff5d2d"; strengthText.textContent="Very Weak"; break;
            case 2: strengthBar.style.width="40%"; strengthBar.style.background="#ff7f50"; strengthText.textContent="Weak"; break;
            case 3: strengthBar.style.width="60%"; strengthBar.style.background="#f3f700"; strengthText.textContent="Medium"; break;
            case 4: strengthBar.style.width="80%"; strengthBar.style.background="#9acd32"; strengthText.textContent="Strong"; break;
            case 5: strengthBar.style.width="100%"; strengthBar.style.background="#00ff88"; strengthText.textContent="Very Strong"; break;
        }
    });

    // Confirm password
    confirm.addEventListener("input", () => {
        if(confirm.value !== password.value){
            confirmStatus.textContent = "Passwords do not match!";
            confirmStatus.style.color = "#ff5d2d";
        } else {
            confirmStatus.textContent = "Passwords match!";
            confirmStatus.style.color = "#00ff88";
        }
    });

    // Form submit validation
    form.addEventListener("submit", e => {
        if(password.value !== confirm.value){
            e.preventDefault();
            confirmStatus.textContent = "Passwords must match!";
            confirmStatus.style.color = "#ff5d2d";
        }
    });
});