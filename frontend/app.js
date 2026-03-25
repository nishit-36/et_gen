// app.js
// Connects frontend to FastAPI backend
// Handles all user interactions

// ── Config ──
const API_URL = "http://localhost:8000";
// This is where your FastAPI server runs

// ── State ──
// These variables remember current app state
let currentUser    = null;
let currentArticle = null;
let currentCategory = "all";

// ── On Page Load ──
window.onload = function() {
    // Generate or get user ID
    // localStorage keeps data even after browser closes
    let userId = localStorage.getItem("et_user_id");
    if (!userId) {
        // First time visitor - create unique ID
        userId = "user_" + Date.now();
        localStorage.setItem("et_user_id", userId);
    }
    currentUser = userId;

    // Check if user has completed onboarding before
    const hasProfile = localStorage.getItem("et_has_profile");
    if (!hasProfile) {
        // New user - show onboarding
        showScreen("onboarding-screen");
    } else {
        // Returning user - show main app
        showScreen("main-screen");
        updateUserLabel();
        loadFeed();
    }
};

// ── Screen Management ──
function showScreen(screenId) {
    document.querySelectorAll(".screen").forEach(s => s.classList.add("hidden"));
    document.getElementById(screenId).classList.remove("hidden");
}

function showFeed() {
    document.getElementById("arc-panel").classList.add("hidden");
    document.getElementById("briefing-panel").classList.add("hidden");
    document.getElementById("feed-panel").classList.remove("hidden");
}

function showOnboarding() {
    showScreen("onboarding-screen");
}

// ── Chip Selection ──
// For profession chips - only one can be selected
document.addEventListener("click", function(e) {
    if (e.target.classList.contains("chip")) {
        const group = e.target.closest(".chip-group");
        const groupId = group.id;

        if (groupId === "profession-chips" || groupId === "language-chips") {
            // Single select
            group.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
            e.target.classList.add("active");
        } else if (groupId === "interest-chips") {
            // Multi select
            e.target.classList.toggle("active");
        }
    }
});

// ── Save Profile ──
function saveProfile() {
    const profession = document.querySelector("#profession-chips .chip.active")?.dataset.value || "general";
    const language   = document.querySelector("#language-chips .chip.active")?.dataset.value || "english";
    const interests  = [...document.querySelectorAll("#interest-chips .chip.active")]
                        .map(c => c.dataset.value);

    // Save to localStorage
    localStorage.setItem("et_has_profile", "true");
    localStorage.setItem("et_profession", profession);
    localStorage.setItem("et_language", language);
    localStorage.setItem("et_interests", JSON.stringify(interests));

    // Save to backend database
    fetch(`${API_URL}/api/save-user`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_id:    currentUser,
            profession: profession,
            interests:  interests,
            language:   language
        })
    });

    // Go to main app
    showScreen("main-screen");
    updateUserLabel();
    loadFeed();
}

function skipOnboarding() {
    localStorage.setItem("et_has_profile", "true");
    showScreen("main-screen");
    loadFeed();
}

function updateUserLabel() {
    const profession = localStorage.getItem("et_profession") || "";
    const language   = localStorage.getItem("et_language") || "english";
    const label      = document.getElementById("user-label");
    if (profession) {
        label.textContent = profession.charAt(0).toUpperCase() +
                           profession.slice(1).replace("_", " ") +
                           " · " + language.charAt(0).toUpperCase() + language.slice(1);
    }
}

// ── Load Feed ──
async function loadFeed() {
    showLoading(true);
    showFeed();
    currentCategory = "all";

    // Set active tab
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelector(".tab").classList.add("active");

    const language = localStorage.getItem("et_language") || "english";

    try {
        const response = await fetch(`${API_URL}/api/feed`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id:  currentUser,
                language: language
            })
        });

        const data = await response.json();
        showLoading(false);

        if (data.status === "success") {
            document.getElementById("feed-title") &&
                (document.querySelector(".feed-title").textContent = "Your Personalized Feed");
            document.getElementById("feed-sub").textContent =
                `${data.total} articles • Personalized for you`;
            renderArticles(data.feed);
        } else {
            showError("Could not load feed. Please try again.");
        }
    } catch (err) {
        showLoading(false);
        showError("Backend not connected. Make sure server is running.");
        console.error(err);
    }
}

// ── Load Category ──
async function loadCategory(category, tabEl) {
    // Update active tab
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    tabEl.classList.add("active");
    currentCategory = category;

    if (category === "all") {
        loadFeed();
        return;
    }

    showLoading(true);
    showFeed();

    const language = localStorage.getItem("et_language") || "english";

    try {
        const response = await fetch(`${API_URL}/api/category`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id:  currentUser,
                category: category,
                language: language
            })
        });

        const data = await response.json();
        showLoading(false);

        if (data.status === "success") {
            document.querySelector(".feed-title").textContent =
                category.charAt(0).toUpperCase() + category.slice(1) + " News";
            document.getElementById("feed-sub").textContent =
                `${data.total} articles`;
            renderArticles(data.feed);
        }
    } catch (err) {
        showLoading(false);
        showError("Could not load category.");
    }
}

// ── Search ──
function handleSearchKey(event) {
    if (event.key === "Enter") searchNews();
}

async function searchNews() {
    const query = document.getElementById("search-input").value.trim();
    if (!query) return;

    showLoading(true);
    showFeed();

    try {
        const response = await fetch(`${API_URL}/api/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id:  currentUser,
                query:    query,
                language: localStorage.getItem("et_language") || "english"
            })
        });

        const data = await response.json();
        showLoading(false);

        if (data.status === "success") {
            document.querySelector(".feed-title").textContent = `Results for "${query}"`;
            document.getElementById("feed-sub").textContent = `${data.total} articles found`;
            renderArticles(data.feed);
        }
    } catch (err) {
        showLoading(false);
        showError("Search failed. Please try again.");
    }
}

// ── Render Articles ──
function renderArticles(articles) {
    const grid = document.getElementById("news-grid");
    grid.innerHTML = "";

    if (!articles || articles.length === 0) {
        grid.innerHTML = `<div style="padding:40px;color:#888;text-align:center;">
            No articles found.</div>`;
        return;
    }

    articles.forEach((article, index) => {
        const card = createNewsCard(article, index);
        grid.appendChild(card);
    });
}

function createNewsCard(article, index) {
    const card = document.createElement("div");
    card.className = "news-card";

    const category  = article.category || "general";
    const tagClass  = `tag-${category}`;
    const tagLabel  = category.charAt(0).toUpperCase() + category.slice(1);
    const score     = article.relevance_score || 0.5;
    const timeAgo   = getTimeAgo(article.published_at);

    // Check if translated
    const isTranslated = article.translated_title;
    const displayTitle   = isTranslated ? article.translated_title : article.title;
    const displaySummary = isTranslated ? article.translated_summary : article.summary;

    card.innerHTML = `
        ${isTranslated ? `<div class="translated-badge">Translated</div>` : ""}
        <div class="card-tag ${tagClass}">${tagLabel}</div>
        <div class="card-title" onclick="openArticle('${encodeURIComponent(article.url)}', '${encodeURIComponent(article.title)}')">
            ${displayTitle}
        </div>
        <div class="card-summary">${displaySummary}</div>
        <div class="card-meta">
            ${timeAgo} · ${article.source}
            <span class="card-score">AI Score: ${score}</span>
        </div>
        <div class="card-actions">
            <button class="btn-action btn-briefing"
                onclick="loadBriefing('${encodeURIComponent(article.title)}', '${encodeURIComponent(article.summary)}')">
                Deep Briefing
            </button>
            <button class="btn-action btn-arc"
                onclick="loadStoryArc('${encodeURIComponent(article.title)}')">
                Story Arc
            </button>
            <button class="btn-action btn-translate"
                onclick="openTranslateModal(${index})">
                Translate
            </button>
            <a href="${article.url}" target="_blank">
                <button class="btn-action btn-read">Read →</button>
            </a>
        </div>
    `;

    // Store article data on card for translate
    card.dataset.index   = index;
    card.dataset.title   = article.title;
    card.dataset.summary = article.summary;

    // Track reading when title is clicked
    card.querySelector(".card-title").addEventListener("click", () => {
        trackRead(article.title, article.category);
    });

    return card;
}

// ── Story Arc ──
async function loadStoryArc(encodedTopic) {
    const topic = decodeURIComponent(encodedTopic);

    document.getElementById("feed-panel").classList.add("hidden");
    document.getElementById("arc-panel").classList.remove("hidden");
    document.getElementById("arc-title").textContent = "Loading story...";
    document.getElementById("arc-content").innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <div class="loading-text">Building story arc with AI...</div>
        </div>`;

    try {
        const response = await fetch(`${API_URL}/api/story-arc`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id: currentUser,
                topic:   topic
            })
        });

        const data = await response.json();

        if (data.status === "success" && data.story_arc) {
            renderStoryArc(data.story_arc, topic);
        } else {
            document.getElementById("arc-content").innerHTML =
                `<p style="color:#888;">Could not build story arc. Try again.</p>`;
        }
    } catch (err) {
        document.getElementById("arc-content").innerHTML =
            `<p style="color:#888;">Connection error.</p>`;
    }
}

function renderStoryArc(arc, topic) {
    document.getElementById("arc-title").textContent = topic;

    const sentiment = arc.sentiment || {};
    const timeline  = arc.timeline  || [];
    const players   = arc.key_players || [];

    let html = `
        <div class="arc-summary">${arc.summary || "No summary available."}</div>

        <div class="arc-section-title">Sentiment Analysis</div>
        <div class="sentiment-row">
            <div class="sent-box sent-positive">Positive ${sentiment.positive || 0}%</div>
            <div class="sent-box sent-neutral">Neutral ${sentiment.neutral || 0}%</div>
            <div class="sent-box sent-negative">Negative ${sentiment.negative || 0}%</div>
        </div>

        <div class="arc-section-title">Timeline of Events</div>
    `;

    timeline.forEach(event => {
        html += `
            <div class="timeline-item">
                <div class="tl-dot"></div>
                <div class="tl-body">
                    <div class="tl-date">${event.date || "Recent"}</div>
                    <div class="tl-event">${event.event || ""}</div>
                </div>
            </div>`;
    });

    if (players.length > 0) {
        html += `<div class="arc-section-title">Key Players</div>
                 <div class="players-grid">`;
        players.forEach(p => {
            html += `<div class="player-card">
                        <div class="player-name">${p.name || ""}</div>
                        <div class="player-role">${p.role || ""}</div>
                     </div>`;
        });
        html += `</div>`;
    }

    html += `
        <div class="arc-section-title">What to Watch Next</div>
        <div class="watch-box">${arc.what_to_watch || "Monitor for further developments."}</div>
    `;

    document.getElementById("arc-content").innerHTML = html;
}

// ── Deep Briefing ──
async function loadBriefing(encodedTitle, encodedSummary) {
    const title   = decodeURIComponent(encodedTitle);
    const summary = decodeURIComponent(encodedSummary);

    document.getElementById("feed-panel").classList.add("hidden");
    document.getElementById("briefing-panel").classList.remove("hidden");
    document.getElementById("briefing-content").innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <div class="loading-text">AI is writing your deep briefing...</div>
        </div>`;

    // Use Groq to generate a deep briefing from title + summary
    try {
        const response = await fetch(`${API_URL}/api/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id: currentUser,
                query:   title,
                language: localStorage.getItem("et_language") || "english"
            })
        });

        const data = await response.json();
        const articles = data.feed || [];

        // Build briefing from top articles
        let briefingText = `<strong>${title}</strong><br/><br/>`;
        briefingText += summary + "<br/><br/>";

        if (articles.length > 0) {
            briefingText += "<strong>Related Coverage:</strong><br/><br/>";
            articles.slice(0, 4).forEach(a => {
                briefingText += `<strong>${a.title}</strong><br/>`;
                briefingText += `${a.summary}<br/><br/>`;
            });
        }

        document.getElementById("briefing-content").innerHTML = `
            <div class="briefing-text">${briefingText}</div>`;

    } catch (err) {
        document.getElementById("briefing-content").innerHTML =
            `<div class="briefing-text">${summary}</div>`;
    }
}

// ── Translate ──
let translateArticleIndex = null;

function openTranslateModal(index) {
    translateArticleIndex = index;
    document.getElementById("translate-modal").classList.remove("hidden");
}

function closeTranslateModal() {
    document.getElementById("translate-modal").classList.add("hidden");
}

async function translateArticle(language) {
    closeTranslateModal();

    const cards = document.querySelectorAll(".news-card");
    const card  = cards[translateArticleIndex];
    if (!card) return;

    const title   = card.dataset.title;
    const summary = card.dataset.summary;

    try {
        const response = await fetch(`${API_URL}/api/translate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id:  currentUser,
                title:    title,
                summary:  summary,
                language: language
            })
        });

        const data = await response.json();

        if (data.status === "success") {
            // Update card with translated content
            const titleEl   = card.querySelector(".card-title");
            const summaryEl = card.querySelector(".card-summary");

            titleEl.textContent   = data.translated_title;
            summaryEl.textContent = data.translated_summary;

            // Add translated badge
            if (!card.querySelector(".translated-badge")) {
                const badge = document.createElement("div");
                badge.className   = "translated-badge";
                badge.textContent = "Translated to " + language;
                card.insertBefore(badge, card.firstChild);
            }
        }
    } catch (err) {
        alert("Translation failed. Please try again.");
    }
}

// ── Track Reading ──
function trackRead(title, category) {
    fetch(`${API_URL}/api/track-read`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_id:       currentUser,
            article_title: title,
            category:      category,
            time_spent:    0
        })
    }).catch(() => {});
    // .catch(() => {}) means silently ignore if it fails
}

function openArticle(encodedUrl, encodedTitle) {
    // Track the read
    const url = decodeURIComponent(encodedUrl);
    window.open(url, "_blank");
}

// ── Helpers ──
function showLoading(show) {
    const loading  = document.getElementById("loading");
    const grid     = document.getElementById("news-grid");
    if (show) {
        loading.classList.remove("hidden");
        grid.innerHTML = "";
    } else {
        loading.classList.add("hidden");
    }
}

function showError(message) {
    document.getElementById("news-grid").innerHTML = `
        <div style="padding:40px;color:#888;text-align:center;grid-column:1/-1;">
            ${message}
        </div>`;
}

function getTimeAgo(dateString) {
    if (!dateString) return "Recently";
    try {
        const date = new Date(dateString);
        const diff = (Date.now() - date.getTime()) / 1000;
        if (diff < 3600)  return Math.floor(diff / 60) + " min ago";
        if (diff < 86400) return Math.floor(diff / 3600) + " hrs ago";
        return Math.floor(diff / 86400) + " days ago";
    } catch {
        return "Recently";
    }
}