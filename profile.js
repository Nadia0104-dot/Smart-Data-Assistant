document.addEventListener("DOMContentLoaded", () => {
    // Edit profile modal
    const modal = document.getElementById("editProfileModal");
    const btn = document.getElementById("editProfile");
    const closeBtn = document.getElementById("closeModal");

    btn.onclick = () => { modal.style.display = "flex"; }
    closeBtn.onclick = () => { modal.style.display = "none"; }
    window.onclick = (e) => { if(e.target === modal) modal.style.display = "none"; }

    // Activity table row highlight
    const tableRows = document.querySelectorAll("#activityTable tbody tr");
    tableRows.forEach(row => {
        row.addEventListener("click", () => {
            tableRows.forEach(r => r.classList.remove("selected-row"));
            row.classList.add("selected-row");
        });
    });

    // Sort table by header
    const headers = document.querySelectorAll("#activityTable th");
    headers.forEach((header, idx) => {
        header.addEventListener("click", () => {
            const tbody = document.querySelector("#activityTable tbody");
            Array.from(tbody.rows)
                 .sort((a,b) => a.cells[idx].textContent.localeCompare(b.cells[idx].textContent))
                 .forEach(tr => tbody.appendChild(tr));
        });
    });
});