require('dotenv').config({ override: true });
const express = require('express');
const { exec } = require('child_process');
const path = require('path');
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 3001;

// Auto-detect Python: prefer python3.10, fall back to python3
const { execSync } = require('child_process');
function findPython() {
  for (const cmd of ['python3.10', 'python3', 'python']) {
    try { execSync(`${cmd} --version`, { stdio: 'ignore' }); return cmd; } catch (_) {}
  }
  return 'python3';
}
const PYTHON = findPython();

const SCRIPT            = path.join(__dirname, 'fetch_stocks.py');
const HISTORY_SCRIPT    = path.join(__dirname, 'fetch_history.py');
const CANDIDATES_SCRIPT = path.join(__dirname, 'fetch_candidates.py');

app.use(express.static(path.join(__dirname, 'public')));

// Original market-cap ranked endpoint (kept for reference)
app.get('/api/stocks', (req, res) => {
  exec(`${PYTHON} "${SCRIPT}"`, { timeout: 30000 }, (err, stdout, stderr) => {
    if (err) {
      console.error('Script error:', stderr || err.message);
      return res.status(500).json({ error: 'Failed to fetch stock data', detail: err.message });
    }
    try {
      const data = JSON.parse(stdout.trim());
      data.updatedAt = new Date().toISOString();
      res.json(data);
    } catch (parseErr) {
      console.error('Parse error:', parseErr.message, '\nstdout:', stdout);
      res.status(500).json({ error: 'Invalid data from script' });
    }
  });
});

// History endpoint
app.get('/api/history/:ticker', (req, res) => {
  const ticker = req.params.ticker;
  exec(`${PYTHON} "${HISTORY_SCRIPT}" "${ticker}"`, { timeout: 30000 }, (err, stdout, stderr) => {
    if (err) {
      console.error('History script error:', stderr || err.message);
      return res.status(500).json({ error: 'Failed to fetch history', detail: err.message });
    }
    try {
      res.json(JSON.parse(stdout.trim()));
    } catch (e) {
      res.status(500).json({ error: 'Invalid data from script' });
    }
  });
});

// ── Scoring algorithm (designed by Claude, no API key required) ──────────────

/**
 * Score each candidate stock using three factors:
 *   Momentum (40%): percentile rank by changePct among all candidates
 *   Size     (30%): percentile rank by marketCap (large-cap stability)
 *   Stability(30%): penalise sharp drops, reward moderate gains
 *
 * Returns candidates sorted by score descending, with sector diversity applied
 * (max 2 per sector) and Korean reason text generated from the stock's profile.
 */
function scoreAndPick(candidates, topN = 10) {
  const valid = candidates.filter(s => s.price != null);

  // Build percentile helpers
  function percentile(arr, val) {
    if (arr.length === 0) return 0.5;
    const sorted = [...arr].sort((a, b) => a - b);
    const rank = sorted.filter(v => v <= val).length;
    return rank / sorted.length;
  }

  const changePcts  = valid.map(s => s.changePct ?? 0);
  const marketCaps  = valid.map(s => s.marketCap ?? 0);

  // Score each stock
  const scored = valid.map(s => {
    const pct = s.changePct ?? 0;
    const cap = s.marketCap ?? 0;

    const momentumScore  = percentile(changePcts, pct) * 40;
    const sizeScore      = percentile(marketCaps, cap) * 30;

    // Stability: full 30 for slight positive, reduce for extremes
    let stabilityScore;
    if (pct >= 0 && pct <= 3)       stabilityScore = 30;
    else if (pct > 3 && pct <= 6)   stabilityScore = 22;
    else if (pct > 6)               stabilityScore = 14; // possibly overbought
    else if (pct >= -2)             stabilityScore = 18;
    else if (pct >= -4)             stabilityScore = 8;
    else                            stabilityScore = 0;  // sharp drop

    const total = momentumScore + sizeScore + stabilityScore;
    return { ...s, _score: total };
  });

  // Sort by score descending
  scored.sort((a, b) => b._score - a._score);

  // Apply sector diversity: max 2 per sector
  const sectorCount = {};
  const picks = [];
  for (const s of scored) {
    if (picks.length >= topN) break;
    const count = sectorCount[s.sector] || 0;
    if (count < 2) {
      picks.push(s);
      sectorCount[s.sector] = count + 1;
    }
  }

  // Generate Korean reason text
  return picks.map((s, i) => {
    const rank = i + 1;
    const pct  = s.changePct ?? 0;
    const cap  = s.marketCap;
    const tier = cap >= 50e12 ? '초대형주' : cap >= 10e12 ? '대형주' : cap >= 2e12 ? '중형주' : '중소형주';

    let momentum;
    if (pct > 2)        momentum = `오늘 ${pct}% 상승하며 강한 매수세가 유입되고 있습니다.`;
    else if (pct > 0)   momentum = `소폭 ${pct}% 상승하며 안정적인 흐름을 보이고 있습니다.`;
    else if (pct === 0) momentum = `전일 대비 보합세로, 방향성 탐색 구간에 있습니다.`;
    else if (pct > -2)  momentum = `소폭 ${Math.abs(pct)}% 조정을 받아 단기 매수 기회로 주목됩니다.`;
    else                momentum = `${Math.abs(pct)}% 하락했으나 시총 기준 저평가 매력이 부각됩니다.`;

    const reason =
      `${s.sector} 섹터의 ${tier}로, ${momentum} ` +
      `시가총액 ${cap ? (cap / 1e12).toFixed(1) + '조원' : 'N/A'} 규모의 KOSPI 200 핵심 종목으로서 ` +
      `섹터 대표주 지위와 유동성을 바탕으로 단기 투자에 유망한 종목으로 선정되었습니다.`;

    const { _score, ...rest } = s;
    return { ...rest, rank, reason };
  });
}

// ── Recommendation endpoint (with 5-min cache) ───────────────────────────────

let cache = null; // { stocks, updatedAt, fetchedAt }
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

function fetchFresh(callback) {
  exec(`${PYTHON} "${CANDIDATES_SCRIPT}"`, { timeout: 90000 }, (err, stdout, stderr) => {
    if (err) return callback(new Error(stderr || err.message));
    try {
      const candidates = JSON.parse(stdout.trim()).candidates;
      const stocks = scoreAndPick(candidates, 10);
      const now = new Date().toISOString();
      cache = { stocks, updatedAt: now, fetchedAt: Date.now() };
      callback(null, cache);
    } catch (e) {
      callback(e);
    }
  });
}

app.get('/api/recommend', (req, res) => {
  const cacheValid = cache && (Date.now() - cache.fetchedAt < CACHE_TTL);

  if (cacheValid) {
    return res.json({ stocks: cache.stocks, updatedAt: cache.updatedAt, cached: true });
  }

  // If stale cache exists, return it immediately and refresh in background
  if (cache) {
    res.json({ stocks: cache.stocks, updatedAt: cache.updatedAt, cached: true });
    fetchFresh((err) => { if (err) console.error('Background refresh failed:', err.message); });
    return;
  }

  // No cache: must wait for fresh data
  fetchFresh((err, result) => {
    if (err) {
      console.error('Candidates script error:', err.message);
      return res.status(500).json({ error: 'Failed to fetch candidate data' });
    }
    res.json({ stocks: result.stocks, updatedAt: result.updatedAt });
  });
});

app.listen(PORT, () => {
  console.log(`KOSPI 200 app running at http://localhost:${PORT}`);
});
