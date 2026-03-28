// app.js — ET News AI Frontend — Complete Fixed Version

const API = "http://localhost:8000";

// ── App State ──
let USER_ID       = null;
let CURRENT_CAT   = "all";
let QA_ARTICLE    = null;
let TRANSLATE_IDX = null;
let ALL_ARTICLES  = [];

// ── Init ──
window.onload = async function() {
    USER_ID = localStorage.getItem("et_uid");
    if (!USER_ID) {
        USER_ID = "user_" + Date.now();
        localStorage.setItem("et_uid", USER_ID);
    }

    // Event delegation on body — works even before grid is populated
    document.body.addEventListener("click", function(e) {
        const btn = e.target.closest("button[data-idx]");
        if (!btn) return;
        const idx = parseInt(btn.dataset.idx);
        if (isNaN(idx)) return;

        if (btn.classList.contains("btn-ask")) {
            openQA(idx);
        } else if (btn.classList.contains("btn-briefing")) {
            loadBriefing(idx);
        } else if (btn.classList.contains("btn-arc")) {
            loadStoryArc(ALL_ARTICLES[idx]?.title || "");
        } else if (btn.classList.contains("btn-translate")) {
            openTranslate(idx);
        }
    });
    await loadCategories();
    const hasProfile = localStorage.getItem("et_profile_done");
    if (!hasProfile) {
        showScreen("onboarding-screen");
    } else {
        showScreen("main-screen");
        updateNavUser();
        loadFeed();
    }
};

// ── Load categories ──
async function loadCategories() {
    try {
        const res  = await fetch(`${API}/api/categories`);
        const data = await res.json();
        buildTabs(data.categories || []);
    } catch {
        buildTabs(["markets","startups","economy","tech","budget",
                   "politics","jobs","real-estate","auto","education"]);
    }
}

function buildTabs(categories) {
    const container = document.getElementById("tabs-container");
    if (!container) return;
    const labels = {
        "markets":"Markets","startups":"Startups","economy":"Economy",
        "tech":"Technology","budget":"Budget","politics":"Politics",
        "international":"International","jobs":"Jobs",
        "real-estate":"Real Estate","auto":"Auto","education":"Education"
    };
    container.innerHTML = `<button class="tab active" onclick="loadCategory('all',this)">All News</button>`;
    categories.forEach(cat => {
        const label = labels[cat] || cat.charAt(0).toUpperCase() + cat.slice(1);
        container.innerHTML += `<button class="tab" onclick="loadCategory('${cat}',this)">${label}</button>`;
    });
}

// ── Screen management ──
function showScreen(id) {
    document.querySelectorAll(".screen").forEach(s => s.classList.add("hidden"));
    document.getElementById(id).classList.remove("hidden");
}

function showPanel(id) {
    document.querySelectorAll(".panel").forEach(p => {
        p.classList.remove("active");
        p.classList.add("hidden");
        p.style.display = "none";
    });
    const panel = document.getElementById(id);
    if (panel) {
        panel.classList.add("active");
        panel.classList.remove("hidden");
        panel.style.display = "block";
    }
}

function showFeed() { showPanel("feed-panel"); }
function showOnboarding() { showScreen("onboarding-screen"); }

// ── Chip selection ──
document.addEventListener("click", function(e) {
    if (!e.target.classList.contains("chip")) return;
    const group = e.target.closest(".chip-group");
    if (!group) return;
    if (group.id === "interest-chips") {
        e.target.classList.toggle("active");
    } else {
        group.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
        e.target.classList.add("active");
    }
});

// ── Save profile ──
async function saveProfile() {
    const profession = document.querySelector("#profession-chips .chip.active")?.dataset.value || "general";
    const language   = document.querySelector("#language-chips .chip.active")?.dataset.value   || "english";
    const experience = document.querySelector("#experience-chips .chip.active")?.dataset.value || "general";
    const reading    = document.querySelector("#reading-chips .chip.active")?.dataset.value    || "any";
    const interests  = [...document.querySelectorAll("#interest-chips .chip.active")].map(c => c.dataset.value);

    localStorage.setItem("et_profile_done", "true");
    localStorage.setItem("et_profession",   profession);
    localStorage.setItem("et_language",     language);

    try {
        await fetch(`${API}/api/save-user`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id: USER_ID, profession, interests,
                language, experience_level: experience,
                reading_time_preference: reading
            })
        });
    } catch {}

    showScreen("main-screen");
    updateNavUser();
    loadFeed();
}

function skipOnboarding() {
    localStorage.setItem("et_profile_done", "true");
    showScreen("main-screen");
    loadFeed();
}

function updateNavUser() {
    const profession = localStorage.getItem("et_profession") || "";
    const language   = localStorage.getItem("et_language")   || "english";
    const el = document.getElementById("nav-user");
    if (!el || !profession) return;
    const label = profession.replace("_", " ");
    el.textContent = label.charAt(0).toUpperCase() + label.slice(1)
                   + " · " + language.charAt(0).toUpperCase() + language.slice(1);
}

// ── Load feed ──
async function loadFeed() {
    showPanel("feed-panel");
    setActiveTab("all");
    CURRENT_CAT = "all";
    document.getElementById("feed-title").textContent = "Your Feed";
    document.getElementById("feed-meta").textContent  = "Loading...";
    showLoading(true);

    const language = localStorage.getItem("et_language") || "english";
    try {
        const res  = await fetch(`${API}/api/feed`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: USER_ID, language })
        });
        const data = await res.json();
        showLoading(false);
        if (data.status === "success") {
            ALL_ARTICLES = data.feed || [];
            document.getElementById("feed-meta").textContent =
                `${data.total} articles · personalized for you`;
            renderArticles(ALL_ARTICLES);
        } else {
            showError("Could not load feed.");
        }
    } catch (err) {
        showLoading(false);
        showError("Cannot connect to backend. Run: uvicorn api.main:app --reload");
        console.error(err);
    }
}

function refreshFeed() {
    if (CURRENT_CAT === "all") loadFeed();
    else {
        const activeTab = document.querySelector(".tab.active");
        loadCategory(CURRENT_CAT, activeTab);
    }
}

// ── Category ──
async function loadCategory(cat, tabEl) {
    setActiveTab(cat, tabEl);
    CURRENT_CAT = cat;
    if (cat === "all") { loadFeed(); return; }

    showPanel("feed-panel");
    showLoading(true);

    const labels = {
        "markets":"Markets","startups":"Startups","economy":"Economy",
        "tech":"Technology","budget":"Budget","politics":"Politics",
        "international":"International","jobs":"Jobs",
        "real-estate":"Real Estate","auto":"Auto","education":"Education"
    };
    document.getElementById("feed-title").textContent = (labels[cat] || cat) + " News";
    document.getElementById("feed-meta").textContent  = "Loading...";

    const language = localStorage.getItem("et_language") || "english";
    try {
        const res  = await fetch(`${API}/api/category`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: USER_ID, category: cat, language })
        });
        const data = await res.json();
        showLoading(false);
        ALL_ARTICLES = data.feed || [];
        document.getElementById("feed-meta").textContent = `${data.total || 0} articles`;
        renderArticles(ALL_ARTICLES);
    } catch {
        showLoading(false);
        showError("Could not load category.");
    }
}

function setActiveTab(cat, tabEl) {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    if (tabEl) {
        tabEl.classList.add("active");
    } else {
        const first = document.querySelector(".tab");
        if (first) first.classList.add("active");
    }
}

// ── Search ──
function handleSearchKey(e) { if (e.key === "Enter") searchNews(); }

async function searchNews() {
    const query = document.getElementById("search-input").value.trim();
    if (!query) return;
    showPanel("feed-panel");
    showLoading(true);
    document.getElementById("feed-title").textContent = `"${query}"`;
    document.getElementById("feed-meta").textContent  = "Searching...";
    const language = localStorage.getItem("et_language") || "english";
    try {
        const res  = await fetch(`${API}/api/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: USER_ID, query, language })
        });
        const data = await res.json();
        showLoading(false);
        ALL_ARTICLES = data.feed || [];
        document.getElementById("feed-meta").textContent =
            `${data.total || 0} results for "${query}"`;
        renderArticles(ALL_ARTICLES);
    } catch {
        showLoading(false);
        showError("Search failed.");
    }
}

// ── Render articles ──
function renderArticles(articles) {
    const grid = document.getElementById("news-grid");
    grid.innerHTML = "";
    if (!articles || articles.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-title">No articles found</div>
                <div class="empty-state-sub">Try a different category or search</div>
            </div>`;
        return;
    }
    articles.forEach((article, idx) => grid.appendChild(buildCard(article, idx)));
}

function buildCard(article, idx) {
    const card     = document.createElement("div");
    card.className = "news-card";
    card.dataset.idx     = idx;
    card.dataset.title   = (article.title   || "").replace(/'/g, "&#39;");
    card.dataset.summary = (article.summary || "").replace(/'/g, "&#39;");

    const cat     = article.category || "general";
    const score   = article.relevance_score || 0.5;
    const reason  = article.reason || "";
    const timeAgo = formatTime(article.published_at);
    const isTranslated = !!article.translated_title;

    const displayTitle   = isTranslated ? article.translated_title   : article.title;
    const displaySummary = isTranslated ? article.translated_summary : article.summary;

    card.innerHTML = `
        <div class="card-top">
            <span class="card-tag tag-${cat}">${cat.replace("-"," ")}</span>
            <span class="card-score-badge">AI ${score}</span>
        </div>
        ${isTranslated ? `<div class="translated-badge">Translated</div>` : ""}
        <div class="card-title">${displayTitle}</div>
        <div class="card-summary">${displaySummary}</div>
        ${reason ? `<div class="card-reason">${reason}</div>` : ""}
        <div class="card-meta">
            <span>${timeAgo}</span>
            <span class="card-meta-dot"></span>
            <span>${article.source || "ET"}</span>
        </div>
        <div class="card-actions">
            <button class="btn-card btn-ask" data-idx="${idx}">Ask AI</button>
            <button class="btn-card btn-briefing" data-idx="${idx}">Deep Briefing</button>
            <button class="btn-card btn-arc" data-idx="${idx}">Story Arc</button>
            <button class="btn-card btn-translate" data-idx="${idx}">Translate</button>
            <a href="${article.url || '#'}" target="_blank" class="btn-card btn-read">Read →</a>
        </div>
    `;

    // Attach events after creating element
    // This avoids all inline onclick issues
// Card title click to open article
    card.querySelector(".card-title").addEventListener("click", () => {
        trackRead(article.title, cat);
        window.open(article.url || "#", "_blank");
    });
    return card;
}

// ── Q&A ──
function openQA(idx) {
    QA_ARTICLE = ALL_ARTICLES[idx];
    if (!QA_ARTICLE) {
        alert("Article not found. Please refresh.");
        return;
    }

    showPanel("qa-panel");
    document.getElementById("qa-breadcrumb").textContent =
        (QA_ARTICLE.title || "").substring(0, 40) + "...";

    const content = document.getElementById("qa-content");
    content.innerHTML = `
        <div class="qa-article-box">
            <div class="qa-article-label">Article context</div>
            <div class="qa-article-title">${QA_ARTICLE.title}</div>
            <div class="qa-article-summary">${QA_ARTICLE.summary || ""}</div>
        </div>
        <div class="qa-chat-area">
            <div class="qa-messages" id="qa-messages">
                <div class="qa-msg qa-msg-ai">
                    <div class="qa-msg-label">ET News AI</div>
                    <div class="qa-bubble">
                        I have read this article. Ask me anything — what it means,
                        how it affects you, or anything you want explained simply.
                    </div>
                </div>
            </div>
            <div class="qa-followups" id="qa-followups">
                <button class="qa-followup-btn">Why did this happen?</button>
                <button class="qa-followup-btn">How does this affect me?</button>
                <button class="qa-followup-btn">Explain in simple terms</button>
            </div>
            <div class="qa-input-bar">
                <input class="qa-input" id="qa-input"
                    placeholder="Ask anything about this article..."
                />
                <button class="qa-send-btn" id="qa-send-btn">Ask</button>
            </div>
        </div>
    `;

    // Attach events after rendering
    document.getElementById("qa-send-btn").addEventListener("click", sendCurrentQuestion);
    document.getElementById("qa-input").addEventListener("keypress", function(e) {
        if (e.key === "Enter") sendCurrentQuestion();
    });
    attachFollowupEvents();
}

function attachFollowupEvents() {
    document.querySelectorAll(".qa-followup-btn").forEach(btn => {
        btn.addEventListener("click", function() {
            sendQuestion(this.textContent.trim());
        });
    });
}

function sendCurrentQuestion() {
    const input = document.getElementById("qa-input");
    if (!input) return;
    const question = input.value.trim();
    if (!question) return;
    input.value = "";
    sendQuestion(question);
}

async function sendQuestion(question) {
    if (!QA_ARTICLE || !question) return;

    const messages = document.getElementById("qa-messages");
    const sendBtn  = document.getElementById("qa-send-btn");
    const input    = document.getElementById("qa-input");
    if (!messages) return;

    if (sendBtn) sendBtn.disabled = true;
    if (input)   input.disabled   = true;

    // User message
    const userMsg = document.createElement("div");
    userMsg.className = "qa-msg qa-msg-user";
    userMsg.innerHTML = `
        <div class="qa-msg-label">You</div>
        <div class="qa-bubble">${question}</div>
    `;
    messages.appendChild(userMsg);

    // Thinking indicator
    const thinkMsg = document.createElement("div");
    thinkMsg.className = "qa-msg qa-msg-ai";
    thinkMsg.innerHTML = `
        <div class="qa-msg-label">ET News AI</div>
        <div class="qa-thinking">
            <div class="pulse-dot"></div>
            <div class="pulse-dot"></div>
            <div class="pulse-dot"></div>
            Thinking...
        </div>
    `;
    messages.appendChild(thinkMsg);
    messages.scrollTop = messages.scrollHeight;

    const language = localStorage.getItem("et_language") || "english";

    try {
        const res  = await fetch(`${API}/api/qa`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id:         USER_ID,
                question:        question,
                article_title:   QA_ARTICLE.title,
                article_summary: QA_ARTICLE.summary || "",
                language:        language
            })
        });
        const data = await res.json();

        // Remove thinking
        thinkMsg.remove();

        // AI answer
        const aiMsg = document.createElement("div");
        aiMsg.className = "qa-msg qa-msg-ai";
        aiMsg.innerHTML = `
            <div class="qa-msg-label">ET News AI</div>
            <div class="qa-bubble">${data.answer || "Sorry, could not get an answer."}</div>
        `;
        messages.appendChild(aiMsg);

        // Update follow-ups
        if (data.follow_up_questions && data.follow_up_questions.length > 0) {
            const followups = document.getElementById("qa-followups");
            if (followups) {
                followups.innerHTML = data.follow_up_questions
                    .map(q => `<button class="qa-followup-btn">${q}</button>`)
                    .join("");
                attachFollowupEvents();
            }
        }

    } catch (err) {
        thinkMsg.remove();
        const errMsg = document.createElement("div");
        errMsg.className = "qa-msg qa-msg-ai";
        errMsg.innerHTML = `
            <div class="qa-bubble">Connection error. Make sure server is running.</div>
        `;
        messages.appendChild(errMsg);
        console.error(err);
    }

    if (sendBtn) sendBtn.disabled = false;
    if (input)   input.disabled   = false;
    messages.scrollTop = messages.scrollHeight;
}

// ── Deep Briefing ──
async function loadBriefing(idx) {
    const article = ALL_ARTICLES[idx];
    if (!article) return;

    showPanel("briefing-panel");
    document.getElementById("briefing-breadcrumb").textContent =
        (article.title || "").substring(0, 40) + "...";

    const content = document.getElementById("briefing-content");
    content.innerHTML = `
        <div class="center-loading">
            <div class="pulse-dot"></div>
            <div class="pulse-dot"></div>
            <div class="pulse-dot"></div>
            <div style="margin-top:12px;font-size:13px;color:var(--text-muted)">
                AI is writing your deep briefing...
            </div>
        </div>
    `;

    const language = localStorage.getItem("et_language") || "english";

    try {
        // Search for related articles on this topic
        const res  = await fetch(`${API}/api/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id:  USER_ID,
                query:    article.title,
                language: language
            })
        });
        const data = await res.json();
        const related = (data.feed || []).slice(0, 5);

        // Build briefing
        let briefingHTML = `
            <div class="briefing-hero">
                <div class="briefing-tag tag-${article.category || 'general'}">
                    ${(article.category || "general").replace("-"," ")}
                </div>
                <div class="briefing-title">${article.title}</div>
                <div class="briefing-meta">
                    ${formatTime(article.published_at)} · ${article.source || "ET"}
                </div>
            </div>
            <div class="briefing-summary-box">
                <div class="briefing-section-label">Summary</div>
                <div class="briefing-text">${article.summary || ""}</div>
            </div>
        `;

        if (related.length > 0) {
            briefingHTML += `
                <div class="briefing-related-label">Related coverage</div>
                <div class="briefing-related-list">
            `;
            related.forEach(r => {
                if (r.title !== article.title) {
                    briefingHTML += `
                        <div class="briefing-related-item">
                            <div class="briefing-related-title">${r.title}</div>
                            <div class="briefing-related-text">${r.summary || ""}</div>
                            <div class="briefing-related-meta">
                                ${formatTime(r.published_at)} · ${r.source || "ET"}
                            </div>
                        </div>
                    `;
                }
            });
            briefingHTML += `</div>`;
        }

        // Ask AI button at bottom
        briefingHTML += `
            <div class="briefing-ask-bar">
                <div class="briefing-ask-label">Have questions about this topic?</div>
                <button class="btn-primary" style="width:auto;padding:10px 20px;"
                    onclick="openQAFromBriefing(${idx})">
                    Ask AI about this
                </button>
            </div>
        `;

        content.innerHTML = briefingHTML;

    } catch (err) {
        content.innerHTML = `
            <div class="briefing-hero">
                <div class="briefing-title">${article.title}</div>
            </div>
            <div class="briefing-summary-box">
                <div class="briefing-text">${article.summary || ""}</div>
            </div>
        `;
        console.error(err);
    }
}

function openQAFromBriefing(idx) {
    openQA(idx);
}

// ── Story Arc ──
async function loadStoryArc(topic) {
    if (!topic) return;
    showPanel("arc-panel");

    document.getElementById("arc-breadcrumb").textContent =
        topic.substring(0, 40) + "...";
    document.getElementById("arc-content").innerHTML = "";
    document.getElementById("arc-loading").classList.remove("hidden");

    try {
        const res  = await fetch(`${API}/api/story-arc`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: USER_ID, topic: topic })
        });
        const data = await res.json();
        document.getElementById("arc-loading").classList.add("hidden");

        if (data.status === "success" && data.story_arc) {
            renderArc(data.story_arc, topic);
        } else {
            document.getElementById("arc-content").innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-title">Could not build story arc</div>
                    <div class="empty-state-sub">Try again or search for a different topic</div>
                </div>`;
        }
    } catch (err) {
        document.getElementById("arc-loading").classList.add("hidden");
        document.getElementById("arc-content").innerHTML = `
            <div class="empty-state">
                <div class="empty-state-title">Connection error</div>
                <div class="empty-state-sub">Make sure the server is running</div>
            </div>`;
        console.error(err);
    }
}

function renderArc(arc, topic) {
    const sentiment = arc.sentiment   || {};
    const timeline  = arc.timeline    || [];
    const players   = arc.key_players || [];
    const sources   = arc.sources_used|| [];
    const posW = sentiment.positive || 0;
    const neuW = sentiment.neutral  || 0;
    const negW = sentiment.negative || 0;

    const timelineHTML = timeline.map(ev => `
        <div class="tl-item">
            <div class="tl-left">
                <div class="tl-dot"></div>
                <div class="tl-line"></div>
            </div>
            <div>
                <div class="tl-date">${ev.date || "Recent"}</div>
                <div class="tl-event">${ev.event || ""}</div>
            </div>
        </div>`).join("");

    const playersHTML = players.map(p => `
        <div class="player-item">
            <div class="player-name">${p.name || ""}</div>
            <div class="player-role">${p.role || ""}</div>
        </div>`).join("");

    const sourcesHTML = sources.map(s =>
        `<span class="source-pill">${s.substring(0,50)}${s.length>50?"...":""}</span>`
    ).join("");

    document.getElementById("arc-content").innerHTML = `
        <div class="arc-hero">
            <div class="arc-topic">${topic}</div>
            <div class="arc-summary-text">${arc.summary || ""}</div>
        </div>
        <div class="arc-grid">
            <div class="arc-card">
                <div class="arc-card-title">Sentiment Analysis</div>
                <div class="sentiment-bars">
                    <div class="sent-item sent-positive">
                        <span class="sent-label">Positive</span>
                        <div class="sent-bar-wrap">
                            <div class="sent-bar" style="width:${posW}%"></div>
                        </div>
                        <span class="sent-pct">${posW}%</span>
                    </div>
                    <div class="sent-item sent-neutral">
                        <span class="sent-label">Neutral</span>
                        <div class="sent-bar-wrap">
                            <div class="sent-bar" style="width:${neuW}%"></div>
                        </div>
                        <span class="sent-pct">${neuW}%</span>
                    </div>
                    <div class="sent-item sent-negative">
                        <span class="sent-label">Negative</span>
                        <div class="sent-bar-wrap">
                            <div class="sent-bar" style="width:${negW}%"></div>
                        </div>
                        <span class="sent-pct">${negW}%</span>
                    </div>
                </div>
            </div>
            <div class="arc-card">
                <div class="arc-card-title">Key Players</div>
                <div class="players-list">
                    ${playersHTML || '<div style="color:var(--text-light);font-size:13px;">None identified</div>'}
                </div>
            </div>
        </div>
        <div class="arc-card" style="margin-bottom:16px;">
            <div class="arc-card-title">Timeline of Events</div>
            <div class="timeline-list">
                ${timelineHTML || '<div style="color:var(--text-light);font-size:13px;">No timeline</div>'}
            </div>
        </div>
        ${arc.conflicting_views && arc.conflicting_views !== "None" ? `
        <div class="arc-card" style="margin-bottom:16px;border-color:#fde68a;background:#fffbeb;">
            <div class="arc-card-title" style="color:var(--amber);">Conflicting Views</div>
            <div style="font-size:13px;color:var(--text);line-height:1.6;">
                ${arc.conflicting_views}
            </div>
        </div>` : ""}
        <div class="arc-watch">
            <div class="arc-watch-label">What to Watch Next</div>
            <div class="arc-watch-text">${arc.what_to_watch || ""}</div>
        </div>
        ${sources.length > 0 ? `
        <div class="arc-sources">
            <div class="arc-sources-title">Sources used by AI</div>
            ${sourcesHTML}
        </div>` : ""}
    `;
}

// ── Translate ──
function openTranslate(idx) {
    TRANSLATE_IDX = idx;
    document.getElementById("translate-modal").classList.remove("hidden");
}

function closeTranslateModal() {
    document.getElementById("translate-modal").classList.add("hidden");
}

async function translateArticle(language) {
    closeTranslateModal();
    const article = ALL_ARTICLES[TRANSLATE_IDX];
    if (!article) return;

    const cards = document.querySelectorAll(".news-card");
    const card  = cards[TRANSLATE_IDX];

    // If switching back to English
    if (language === "english") {
        if (card) {
            const titleEl   = card.querySelector(".card-title");
            const summaryEl = card.querySelector(".card-summary");
            if (titleEl)   titleEl.textContent   = article.title;
            if (summaryEl) summaryEl.textContent = article.summary;
            const badge = card.querySelector(".translated-badge");
            if (badge) badge.remove();
        }
        return;
    }

    try {
        const res  = await fetch(`${API}/api/translate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id:  USER_ID,
                title:    article.title,
                summary:  article.summary,
                language: language
            })
        });
        const data = await res.json();

        if (data.status === "success" && !data.translation_failed) {
            ALL_ARTICLES[TRANSLATE_IDX].translated_title   = data.translated_title;
            ALL_ARTICLES[TRANSLATE_IDX].translated_summary = data.translated_summary;

            if (card) {
                const titleEl   = card.querySelector(".card-title");
                const summaryEl = card.querySelector(".card-summary");
                if (titleEl)   titleEl.textContent   = data.translated_title;
                if (summaryEl) summaryEl.textContent = data.translated_summary;

                const existing = card.querySelector(".translated-badge");
                if (existing) existing.remove();
                const badge = document.createElement("div");
                badge.className   = "translated-badge";
                badge.textContent = "Translated · " + language;
                card.insertBefore(badge, card.querySelector(".card-title"));
            }
        } else {
            alert("Translation failed. Showing original English.");
        }
    } catch {
        alert("Translation error. Please try again.");
    }
}

// ── Track read ──
function trackRead(title, category) {
    fetch(`${API}/api/track-read`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_id: USER_ID, article_title: title,
            category: category, time_spent: 0
        })
    }).catch(() => {});
}

// ── Helpers ──
function showLoading(show) {
    const bar  = document.getElementById("loading-bar");
    const grid = document.getElementById("news-grid");
    if (show) {
        if (bar)  bar.classList.remove("hidden");
        if (grid) grid.innerHTML = "";
    } else {
        if (bar) bar.classList.add("hidden");
    }
}

function showError(msg) {
    const grid = document.getElementById("news-grid");
    if (grid) grid.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-title">Something went wrong</div>
            <div class="empty-state-sub">${msg}</div>
        </div>`;
}

function formatTime(dateStr) {
    if (!dateStr) return "Recently";
    try {
        const d    = new Date(dateStr);
        const diff = (Date.now() - d.getTime()) / 1000;
        if (diff < 3600)  return Math.floor(diff / 60)  + " min ago";
        if (diff < 86400) return Math.floor(diff / 3600) + " hrs ago";
        return Math.floor(diff / 86400) + " days ago";
    } catch { return "Recently"; }
}
