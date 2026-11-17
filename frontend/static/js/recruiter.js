const uploadZone = document.getElementById("uploadZone");
const resumeInput = document.getElementById("resumeInput");
const fileList = document.getElementById("fileList");
const runButton = document.getElementById("runButton");
const statusArea = document.getElementById("statusArea");
const resultsArea = document.getElementById("resultsArea");

let selectedFiles = [];

uploadZone.addEventListener("click", () => resumeInput.click());

resumeInput.addEventListener("change", (e) => {
    addFiles(Array.from(e.target.files));
    resumeInput.value = "";
});

uploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
});

uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    addFiles(Array.from(e.dataTransfer.files));
});

function addFiles(files) {
    const validFiles = files.filter(f => {
        const ext = f.name.split(".").pop().toLowerCase();
        return ext === "pdf" || ext === "docx";
    });
    selectedFiles = selectedFiles.concat(validFiles);
    renderFileList();
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
}

function renderFileList() {
    fileList.innerHTML = "";
    selectedFiles.forEach((file, index) => {
        const chip = document.createElement("div");
        chip.className = "file-chip";
        chip.innerHTML = `
            <span>${file.name}</span>
            <button onclick="removeFile(${index})">✕</button>
        `;
        fileList.appendChild(chip);
    });
}

runButton.addEventListener("click", async () => {
    const jobDescription = document.getElementById("jobDescription").value.trim();

    if (!jobDescription) {
        showError("Please enter a job description.");
        return;
    }
    if (selectedFiles.length === 0) {
        showError("Please upload at least one resume.");
        return;
    }

    clearMessages();
    runButton.disabled = true;
    runButton.textContent = "SCREENING...";
    showStatus(`Processing ${selectedFiles.length} candidate(s) — this may take a few minutes on local hardware...`);

    const formData = new FormData();
    formData.append("job_description", jobDescription);
    selectedFiles.forEach(file => formData.append("resumes", file));

    try {
        const response = await fetch("/api/recruiter/screen", {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Screening failed.");
        }

        const result = await response.json();
        clearMessages();
        renderResults(result);
    } catch (err) {
        clearMessages();
        showError(err.message || "Something went wrong. Please try again.");
    } finally {
        runButton.disabled = false;
        runButton.textContent = "RUN BATCH SCREENING";
    }
});

function showStatus(message) {
    statusArea.innerHTML = `<div class="loading-status">${message}</div>`;
}

function showError(message) {
    statusArea.innerHTML = `<div class="error-message">${message}</div>`;
}

function clearMessages() {
    statusArea.innerHTML = "";
}

function fitBadgeClass(fitLabel) {
    if (fitLabel === "Strong Fit") return "strong-fit";
    if (fitLabel === "Partial Fit") return "partial-fit";
    return "no-fit";
}

function renderResults(result) {
    resultsArea.innerHTML = "";

    const sectionLabel = document.createElement("div");
    sectionLabel.className = "section-label";
    sectionLabel.textContent = "RANKED SHORTLIST";
    resultsArea.appendChild(sectionLabel);

    result.candidates.forEach((candidate, index) => {
        const card = document.createElement("div");
        card.className = "candidate-card";
        card.style.cursor = "pointer";
        card.innerHTML = `
            <span class="candidate-rank">${String(index + 1).padStart(2, "0")}</span>
            <span class="candidate-name">${candidate.candidate_name || candidate.filename}</span>
            <span class="candidate-score">${candidate.final_score}<span class="max">/100</span></span>
            <span class="badge ${fitBadgeClass(candidate.fit_label)}">${candidate.fit_label}</span>
        `;

        const details = document.createElement("div");
        details.className = "candidate-details";
        details.innerHTML = `
            <div class="detail-row"><strong>Priority:</strong> ${candidate.priority_label}</div>
            <div class="detail-row"><strong>Summary:</strong> ${candidate.summary}</div>
            <div class="detail-row"><strong>Matched Skills:</strong> ${candidate.skills.matched_required.join(", ") || "none"}</div>
            <div class="detail-row"><strong>Missing Skills:</strong> ${candidate.skills.missing_required.join(", ") || "none"}</div>
            <div class="detail-row"><strong>Supporting Evidence:</strong> ${candidate.evidence.supporting_bullets.join(" • ") || "none"}</div>
        `;

        card.addEventListener("click", () => {
            details.classList.toggle("open");
        });

        resultsArea.appendChild(card);
        resultsArea.appendChild(details);
    });

    const footer = document.createElement("div");
    footer.className = "footer-note";
    footer.textContent = "SKILLS · EXPERIENCE · EVIDENCE — SYNTHESIZED BY JUDGE AGENT";
    resultsArea.appendChild(footer);
}