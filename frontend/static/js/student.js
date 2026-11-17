const uploadZone = document.getElementById("uploadZone");
const resumeInput = document.getElementById("resumeInput");
const fileList = document.getElementById("fileList");
const runButton = document.getElementById("runButton");
const statusArea = document.getElementById("statusArea");
const resultsArea = document.getElementById("resultsArea");

let selectedFile = null;

uploadZone.addEventListener("click", () => resumeInput.click());

resumeInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
        setFile(e.target.files[0]);
    }
    resumeInput.value = "";
});

uploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
});

uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length > 0) {
        setFile(e.dataTransfer.files[0]);
    }
});

function setFile(file) {
    const ext = file.name.split(".").pop().toLowerCase();
    if (ext !== "pdf" && ext !== "docx") {
        showError("Only PDF or DOCX files are supported.");
        return;
    }
    selectedFile = file;
    renderFileList();
}

function removeFile() {
    selectedFile = null;
    renderFileList();
}

function renderFileList() {
    fileList.innerHTML = "";
    if (selectedFile) {
        const chip = document.createElement("div");
        chip.className = "file-chip";
        chip.innerHTML = `
            <span>${selectedFile.name}</span>
            <button onclick="removeFile()">✕</button>
        `;
        fileList.appendChild(chip);
    }
}

runButton.addEventListener("click", async () => {
    const jobDescription = document.getElementById("jobDescription").value.trim();

    if (!jobDescription) {
        showError("Please enter a target job description.");
        return;
    }
    if (!selectedFile) {
        showError("Please upload your resume.");
        return;
    }

    clearMessages();
    runButton.disabled = true;
    runButton.textContent = "ANALYZING...";
    showStatus("Analyzing your resume against the job description — this may take a minute on local hardware...");

    const formData = new FormData();
    formData.append("job_description", jobDescription);
    formData.append("resume", selectedFile);

    try {
        const response = await fetch("/api/student/analyze", {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Analysis failed.");
        }

        const result = await response.json();
        clearMessages();
        renderResults(result);
    } catch (err) {
        clearMessages();
        showError(err.message || "Something went wrong. Please try again.");
    } finally {
        runButton.disabled = false;
        runButton.textContent = "ANALYZE MY RESUME";
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

function renderResults(result) {
    resultsArea.innerHTML = "";

    const sectionLabel = document.createElement("div");
    sectionLabel.className = "section-label";
    sectionLabel.textContent = `FEEDBACK ON YOUR RESUME — ${result.feedback.match_percentage}% MATCH`;
    resultsArea.appendChild(sectionLabel);

    if (result.feedback.missing_requirements.length > 0) {
        const card = document.createElement("div");
        card.className = "feedback-card gap";
        card.innerHTML = `
            <div class="feedback-title">SKILLS GAP</div>
            <p>Missing from your resume: ${result.feedback.missing_requirements.join(", ")}.</p>
        `;
        resultsArea.appendChild(card);
    }

    if (result.feedback.partial_requirements.length > 0) {
        const card = document.createElement("div");
        card.className = "feedback-card risk";
        card.innerHTML = `
            <div class="feedback-title">CONSISTENCY CHECK</div>
            <p>Listed but not backed by a specific example: ${result.feedback.partial_requirements.join(", ")}. Add a concrete bullet or consider removing them — recruiter tools may flag this as keyword-stuffing.</p>
        `;
        resultsArea.appendChild(card);
    }

    if (result.feedback.matched_requirements.length > 0) {
        const card = document.createElement("div");
        card.className = "feedback-card strength";
        card.innerHTML = `
            <div class="feedback-title">STRENGTHS</div>
            <p>Well matched: ${result.feedback.matched_requirements.join(", ")}.</p>
        `;
        resultsArea.appendChild(card);
    }

    result.feedback.suggestions.forEach(suggestion => {
        const card = document.createElement("div");
        card.className = "feedback-card";
        card.innerHTML = `
            <div class="feedback-title">SUGGESTION</div>
            <p>${suggestion}</p>
        `;
        resultsArea.appendChild(card);
    });

    const footer = document.createElement("div");
    footer.className = "footer-note";
    footer.textContent = "AI-GENERATED SUGGESTIONS — REVIEW BEFORE APPLYING";
    resultsArea.appendChild(footer);
}