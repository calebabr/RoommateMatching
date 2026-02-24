import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api";

// --- API helpers ---
async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

async function uploadFile(path, file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

// --- Preference Slider ---
function PrefSlider({ label, value, onChange, min = 0, max = 10, isDealBreaker, onDealBreakerChange }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <label style={{ fontFamily: "'DM Sans', sans-serif", fontSize: 13, fontWeight: 600, color: "#2d3142", letterSpacing: "0.02em" }}>
          {label}
        </label>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 13, color: "#f4845f", fontWeight: 700 }}>{value}</span>
          <button
            onClick={() => onDealBreakerChange(!isDealBreaker)}
            style={{
              padding: "2px 8px",
              fontSize: 10,
              fontFamily: "'DM Sans', sans-serif",
              fontWeight: 700,
              letterSpacing: "0.05em",
              border: "2px solid",
              borderColor: isDealBreaker ? "#e63946" : "#c4c7d0",
              background: isDealBreaker ? "#e63946" : "transparent",
              color: isDealBreaker ? "#fff" : "#8b8fa3",
              borderRadius: 4,
              cursor: "pointer",
              transition: "all 0.2s",
              textTransform: "uppercase",
            }}
          >
            {isDealBreaker ? "DEAL BREAKER" : "flexible"}
          </button>
        </div>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{
          width: "100%",
          accentColor: "#f4845f",
          height: 6,
          cursor: "pointer",
        }}
      />
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#8b8fa3", fontFamily: "'DM Sans', sans-serif" }}>
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}

// --- Score Bar ---
function ScoreBar({ score, label }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "#2ec4b6" : pct >= 60 ? "#f4845f" : "#e63946";
  return (
    <div style={{ marginBottom: 8 }}>
      {label && (
        <div style={{ fontSize: 11, color: "#8b8fa3", fontFamily: "'DM Sans', sans-serif", marginBottom: 2 }}>{label}</div>
      )}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ flex: 1, height: 8, background: "#eef0f5", borderRadius: 4, overflow: "hidden" }}>
          <div
            style={{
              width: `${pct}%`,
              height: "100%",
              background: `linear-gradient(90deg, ${color}, ${color}dd)`,
              borderRadius: 4,
              transition: "width 0.6s cubic-bezier(0.22, 1, 0.36, 1)",
            }}
          />
        </div>
        <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 13, fontWeight: 700, color, minWidth: 42, textAlign: "right" }}>
          {pct}%
        </span>
      </div>
    </div>
  );
}

// --- Toast ---
function Toast({ message, type, onClose }) {
  if (!message) return null;
  const bg = type === "error" ? "#e63946" : type === "success" ? "#2ec4b6" : "#f4845f";
  return (
    <div
      style={{
        position: "fixed",
        top: 24,
        right: 24,
        padding: "14px 24px",
        background: bg,
        color: "#fff",
        borderRadius: 8,
        fontFamily: "'DM Sans', sans-serif",
        fontSize: 14,
        fontWeight: 600,
        boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
        zIndex: 1000,
        animation: "slideIn 0.3s ease-out",
        cursor: "pointer",
      }}
      onClick={onClose}
    >
      {message}
    </div>
  );
}

// --- Main App ---
export default function RoomMatchDashboard() {
  const [tab, setTab] = useState("upload");
  const [toast, setToast] = useState({ message: "", type: "" });
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [topMatches, setTopMatches] = useState([]);
  const [matchUserDetails, setMatchUserDetails] = useState({});
  const [loading, setLoading] = useState(false);

  // New user form
  const [username, setUsername] = useState("");
  const [sleepWD, setSleepWD] = useState(22);
  const [sleepWDdb, setSleepWDdb] = useState(false);
  const [sleepWE, setSleepWE] = useState(23);
  const [sleepWEdb, setSleepWEdb] = useState(false);
  const [clean, setClean] = useState(7);
  const [cleanDb, setCleanDb] = useState(false);
  const [noise, setNoise] = useState(5);
  const [noiseDb, setNoiseDb] = useState(false);
  const [guests, setGuests] = useState(5);
  const [guestsDb, setGuestsDb] = useState(false);

  const showToast = (message, type = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast({ message: "", type: "" }), 3500);
  };

  const fetchUsers = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/users/all`);
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (e) {
      // silent
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Upload JSON
  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoading(true);
    try {
      const result = await uploadFile("/uploadUsers", file);
      showToast(result.message, "success");
      await fetchUsers();
    } catch (err) {
      showToast(err.message, "error");
    }
    setLoading(false);
  };

  // Create user
  const handleCreateUser = async () => {
    if (!username.trim()) {
      showToast("Username required", "error");
      return;
    }
    setLoading(true);
    try {
      await api("/users", {
        method: "POST",
        body: JSON.stringify({
          username: username.trim(),
          sleepScoreWD: { value: sleepWD, isDealBreaker: sleepWDdb },
          sleepScoreWE: { value: sleepWE, isDealBreaker: sleepWEdb },
          cleanlinessScore: { value: clean, isDealBreaker: cleanDb },
          noiseToleranceScore: { value: noise, isDealBreaker: noiseDb },
          guestsScore: { value: guests, isDealBreaker: guestsDb },
        }),
      });
      showToast(`Created user: ${username}`, "success");
      setUsername("");
      await fetchUsers();
    } catch (err) {
      showToast(err.message, "error");
    }
    setLoading(false);
  };

  // Recompute
  const handleRecompute = async () => {
    setLoading(true);
    try {
      const result = await api("/admin/recompute", { method: "POST" });
      showToast(result.message, "success");
    } catch (err) {
      showToast(err.message, "error");
    }
    setLoading(false);
  };

  // View matches
  const handleViewMatches = async (userId) => {
    setSelectedUser(userId);
    setLoading(true);
    try {
      const data = await api(`/users/${userId}/top-matches`);
      setTopMatches(data.matches || []);

      // Fetch details for each matched user
      const details = {};
      for (const m of data.matches || []) {
        try {
          const u = await api(`/users/${m.user_id}`);
          details[m.user_id] = u;
        } catch (e) {
          // skip
        }
      }
      setMatchUserDetails(details);
    } catch (err) {
      showToast(err.message, "error");
      setTopMatches([]);
    }
    setLoading(false);
  };

  const selectedUserData = users.find((u) => u.id === selectedUser);

  const tabStyle = (t) => ({
    padding: "10px 28px",
    fontFamily: "'DM Sans', sans-serif",
    fontSize: 13,
    fontWeight: 700,
    letterSpacing: "0.04em",
    textTransform: "uppercase",
    background: tab === t ? "#2d3142" : "transparent",
    color: tab === t ? "#fff" : "#8b8fa3",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
    transition: "all 0.25s",
  });

  const cardStyle = {
    background: "#fff",
    borderRadius: 12,
    padding: 28,
    boxShadow: "0 2px 16px rgba(45,49,66,0.06)",
    border: "1px solid #eef0f5",
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(145deg, #f8f9fc 0%, #eef0f5 50%, #e8eaf0 100%)",
        fontFamily: "'DM Sans', sans-serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&family=Playfair+Display:wght@700;800;900&display=swap');
        @keyframes slideIn { from { transform: translateX(100px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        @keyframes fadeUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        input[type="range"] { -webkit-appearance: none; appearance: none; background: #eef0f5; border-radius: 4px; outline: none; }
        input[type="range"]::-webkit-slider-thumb { -webkit-appearance: none; width: 18px; height: 18px; background: #f4845f; border-radius: 50%; cursor: pointer; box-shadow: 0 2px 8px rgba(244,132,95,0.4); }
        * { box-sizing: border-box; }
        ::selection { background: #f4845f33; }
      `}</style>

      <Toast message={toast.message} type={toast.type} onClose={() => setToast({ message: "", type: "" })} />

      {/* Header */}
      <div
        style={{
          padding: "32px 48px 24px",
          borderBottom: "1px solid #e0e2ea",
          background: "#fff",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
        }}
      >
        <div>
          <h1
            style={{
              fontFamily: "'Playfair Display', serif",
              fontSize: 36,
              fontWeight: 900,
              color: "#2d3142",
              margin: 0,
              letterSpacing: "-0.02em",
            }}
          >
            Room<span style={{ color: "#f4845f" }}>Match</span>
          </h1>
          <p style={{ color: "#8b8fa3", fontSize: 14, margin: "4px 0 0", fontWeight: 500 }}>
            Algorithm Testing Dashboard
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: users.length > 0 ? "#2ec4b6" : "#e63946",
              boxShadow: users.length > 0 ? "0 0 8px #2ec4b644" : "0 0 8px #e6394644",
            }}
          />
          <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 13, color: "#8b8fa3" }}>
            {users.length} users in pool
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ padding: "20px 48px 0", display: "flex", gap: 8 }}>
        <button style={tabStyle("upload")} onClick={() => setTab("upload")}>Upload</button>
        <button style={tabStyle("create")} onClick={() => setTab("create")}>Create User</button>
        <button style={tabStyle("users")} onClick={() => setTab("users")}>Users</button>
        <button style={tabStyle("matches")} onClick={() => setTab("matches")}>Matches</button>
      </div>

      {/* Content */}
      <div style={{ padding: "24px 48px 48px", maxWidth: 1100 }}>

        {/* Upload Tab */}
        {tab === "upload" && (
          <div style={{ ...cardStyle, animation: "fadeUp 0.4s ease-out" }}>
            <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 22, fontWeight: 800, color: "#2d3142", margin: "0 0 8px" }}>
              Upload Test Users
            </h2>
            <p style={{ color: "#8b8fa3", fontSize: 14, margin: "0 0 24px" }}>
              Upload a JSON file with user profiles to populate the database.
            </p>

            <label
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "48px 24px",
                border: "2px dashed #c4c7d0",
                borderRadius: 12,
                cursor: "pointer",
                transition: "all 0.25s",
                background: "#fafbfd",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "#f4845f";
                e.currentTarget.style.background = "#fff8f5";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "#c4c7d0";
                e.currentTarget.style.background = "#fafbfd";
              }}
            >
              <div style={{ fontSize: 40, marginBottom: 12 }}>📂</div>
              <span style={{ fontWeight: 600, color: "#2d3142", fontSize: 15, marginBottom: 4 }}>
                Drop your JSON file here or click to browse
              </span>
              <span style={{ fontSize: 12, color: "#8b8fa3" }}>Accepts .json files</span>
              <input type="file" accept=".json" onChange={handleUpload} style={{ display: "none" }} />
            </label>

            <div style={{ marginTop: 24, display: "flex", gap: 12 }}>
              <button
                onClick={handleRecompute}
                disabled={loading || users.length < 2}
                style={{
                  padding: "12px 28px",
                  background: users.length >= 2 ? "linear-gradient(135deg, #2d3142, #3d4162)" : "#c4c7d0",
                  color: "#fff",
                  border: "none",
                  borderRadius: 8,
                  fontFamily: "'DM Sans', sans-serif",
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: users.length >= 2 ? "pointer" : "not-allowed",
                  letterSpacing: "0.03em",
                  transition: "all 0.25s",
                  boxShadow: users.length >= 2 ? "0 4px 16px rgba(45,49,66,0.2)" : "none",
                }}
              >
                {loading ? "Computing..." : "⚡ Recompute Matches"}
              </button>
            </div>
          </div>
        )}

        {/* Create User Tab */}
        {tab === "create" && (
          <div style={{ ...cardStyle, maxWidth: 520, animation: "fadeUp 0.4s ease-out" }}>
            <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 22, fontWeight: 800, color: "#2d3142", margin: "0 0 24px" }}>
              New Profile
            </h2>

            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 13, fontWeight: 600, color: "#2d3142", display: "block", marginBottom: 6 }}>
                Username
              </label>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. john.smith42"
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  border: "2px solid #eef0f5",
                  borderRadius: 8,
                  fontFamily: "'DM Sans', sans-serif",
                  fontSize: 14,
                  outline: "none",
                  transition: "border-color 0.2s",
                }}
                onFocus={(e) => (e.target.style.borderColor = "#f4845f")}
                onBlur={(e) => (e.target.style.borderColor = "#eef0f5")}
              />
            </div>

            <PrefSlider label="🌙 Sleep Schedule (Weekdays)" value={sleepWD} onChange={setSleepWD} min={0} max={24} isDealBreaker={sleepWDdb} onDealBreakerChange={setSleepWDdb} />
            <PrefSlider label="🌙 Sleep Schedule (Weekends)" value={sleepWE} onChange={setSleepWE} min={0} max={24} isDealBreaker={sleepWEdb} onDealBreakerChange={setSleepWEdb} />
            <PrefSlider label="🧹 Cleanliness" value={clean} onChange={setClean} min={1} max={10} isDealBreaker={cleanDb} onDealBreakerChange={setCleanDb} />
            <PrefSlider label="🔊 Noise Tolerance" value={noise} onChange={setNoise} min={1} max={10} isDealBreaker={noiseDb} onDealBreakerChange={setNoiseDb} />
            <PrefSlider label="👥 Guests" value={guests} onChange={setGuests} min={1} max={10} isDealBreaker={guestsDb} onDealBreakerChange={setGuestsDb} />

            <button
              onClick={handleCreateUser}
              disabled={loading}
              style={{
                marginTop: 12,
                width: "100%",
                padding: "14px",
                background: "linear-gradient(135deg, #f4845f, #f4a261)",
                color: "#fff",
                border: "none",
                borderRadius: 8,
                fontFamily: "'DM Sans', sans-serif",
                fontSize: 14,
                fontWeight: 700,
                cursor: "pointer",
                letterSpacing: "0.03em",
                boxShadow: "0 4px 16px rgba(244,132,95,0.3)",
                transition: "all 0.25s",
              }}
            >
              {loading ? "Creating..." : "Create Profile"}
            </button>
          </div>
        )}

        {/* Users Tab */}
        {tab === "users" && (
          <div style={{ animation: "fadeUp 0.4s ease-out" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 22, fontWeight: 800, color: "#2d3142", margin: 0 }}>
                All Users
              </h2>
              <button
                onClick={fetchUsers}
                style={{
                  padding: "8px 20px",
                  background: "#2d3142",
                  color: "#fff",
                  border: "none",
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                  fontFamily: "'DM Sans', sans-serif",
                }}
              >
                Refresh
              </button>
            </div>

            {users.length === 0 ? (
              <div style={{ ...cardStyle, textAlign: "center", padding: 48 }}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>🏠</div>
                <p style={{ color: "#8b8fa3", fontSize: 14 }}>No users yet. Upload a JSON file or create profiles.</p>
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
                {users.map((u) => (
                  <div
                    key={u.id}
                    style={{
                      ...cardStyle,
                      padding: 20,
                      cursor: "pointer",
                      transition: "all 0.25s",
                      borderColor: selectedUser === u.id ? "#f4845f" : "#eef0f5",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = "translateY(-2px)";
                      e.currentTarget.style.boxShadow = "0 8px 24px rgba(45,49,66,0.1)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = "translateY(0)";
                      e.currentTarget.style.boxShadow = "0 2px 16px rgba(45,49,66,0.06)";
                    }}
                    onClick={() => {
                      setSelectedUser(u.id);
                      setTab("matches");
                      handleViewMatches(u.id);
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                      <div>
                        <div style={{ fontWeight: 700, color: "#2d3142", fontSize: 15 }}>{u.username}</div>
                        <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 11, color: "#8b8fa3" }}>ID: {u.id}</div>
                      </div>
                      <div
                        style={{
                          padding: "3px 10px",
                          borderRadius: 4,
                          fontSize: 10,
                          fontWeight: 700,
                          textTransform: "uppercase",
                          letterSpacing: "0.05em",
                          background: u.matched ? "#2ec4b622" : "#f4845f22",
                          color: u.matched ? "#2ec4b6" : "#f4845f",
                        }}
                      >
                        {u.matched ? "Matched" : "Searching"}
                      </div>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: 12, color: "#5c6078" }}>
                      <div>🌙 Sleep WD: <strong>{u.sleepScoreWD?.value}</strong></div>
                      <div>🌙 Sleep WE: <strong>{u.sleepScoreWE?.value}</strong></div>
                      <div>🧹 Clean: <strong>{u.cleanlinessScore?.value}</strong></div>
                      <div>🔊 Noise: <strong>{u.noiseToleranceScore?.value}</strong></div>
                      <div>👥 Guests: <strong>{u.guestsScore?.value}</strong></div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Matches Tab */}
        {tab === "matches" && (
          <div style={{ animation: "fadeUp 0.4s ease-out" }}>
            <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 22, fontWeight: 800, color: "#2d3142", margin: "0 0 8px" }}>
              Top Matches
            </h2>

            {!selectedUser ? (
              <div style={{ ...cardStyle, textAlign: "center", padding: 48 }}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>🔍</div>
                <p style={{ color: "#8b8fa3", fontSize: 14 }}>Select a user from the Users tab to view their matches.</p>
              </div>
            ) : (
              <>
                {selectedUserData && (
                  <div style={{ ...cardStyle, marginBottom: 20, background: "linear-gradient(135deg, #2d3142, #3d4162)", color: "#fff" }}>
                    <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: "#8b8fa3", marginBottom: 4 }}>
                      Showing matches for
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 700 }}>{selectedUserData.username}</div>
                    <div style={{ display: "flex", gap: 16, marginTop: 12, fontSize: 13, color: "#b0b3c0" }}>
                      <span>🌙 {selectedUserData.sleepScoreWD?.value}h</span>
                      <span>🧹 {selectedUserData.cleanlinessScore?.value}/10</span>
                      <span>🔊 {selectedUserData.noiseToleranceScore?.value}/10</span>
                      <span>👥 {selectedUserData.guestsScore?.value}/10</span>
                    </div>
                  </div>
                )}

                {loading ? (
                  <div style={{ ...cardStyle, textAlign: "center", padding: 48 }}>
                    <p style={{ color: "#8b8fa3" }}>Loading matches...</p>
                  </div>
                ) : topMatches.length === 0 ? (
                  <div style={{ ...cardStyle, textAlign: "center", padding: 48 }}>
                    <div style={{ fontSize: 32, marginBottom: 12 }}>😕</div>
                    <p style={{ color: "#8b8fa3", fontSize: 14 }}>
                      No matches found. Make sure you've run Recompute Matches.
                    </p>
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {topMatches.map((m, i) => {
                      const detail = matchUserDetails[m.user_id];
                      return (
                        <div
                          key={m.user_id}
                          style={{
                            ...cardStyle,
                            padding: 20,
                            display: "flex",
                            alignItems: "center",
                            gap: 20,
                            transition: "all 0.25s",
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.transform = "translateX(4px)";
                            e.currentTarget.style.borderColor = "#f4845f";
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.transform = "translateX(0)";
                            e.currentTarget.style.borderColor = "#eef0f5";
                          }}
                        >
                          <div
                            style={{
                              width: 40,
                              height: 40,
                              borderRadius: 8,
                              background: `linear-gradient(135deg, ${i < 3 ? "#f4845f" : "#2d3142"}, ${i < 3 ? "#f4a261" : "#3d4162"})`,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              color: "#fff",
                              fontFamily: "'DM Mono', monospace",
                              fontWeight: 700,
                              fontSize: 16,
                              flexShrink: 0,
                            }}
                          >
                            {i + 1}
                          </div>

                          <div style={{ flex: 1 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                              <div>
                                <span style={{ fontWeight: 700, color: "#2d3142", fontSize: 15 }}>
                                  {detail?.username || `User ${m.user_id}`}
                                </span>
                                <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 11, color: "#8b8fa3", marginLeft: 8 }}>
                                  ID: {m.user_id}
                                </span>
                              </div>
                            </div>
                            <ScoreBar score={m.compatibilityScore} />
                            {detail && (
                              <div style={{ display: "flex", gap: 14, fontSize: 12, color: "#5c6078", marginTop: 4 }}>
                                <span>🌙 {detail.sleepScoreWD?.value}h</span>
                                <span>🧹 {detail.cleanlinessScore?.value}/10</span>
                                <span>🔊 {detail.noiseToleranceScore?.value}/10</span>
                                <span>👥 {detail.guestsScore?.value}/10</span>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
