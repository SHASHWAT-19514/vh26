# 🚀 QUICK START GUIDE — Abhedya-Chakra

## Instant Launch (Current Session)

**The system is ALREADY RUNNING!**

Open your browser and visit:
```
http://127.0.0.1:8001
```

The server is live with the full 2M transaction dataset loaded.

---

## Starting From Scratch

### Windows (start.bat)
```batch
cd "C:\Users\SHASHWAT SEN\Desktop\og"
start.bat
```

Then open: **http://127.0.0.1:8000**

### Manual Start
```batch
cd "C:\Users\SHASHWAT SEN\Desktop\og"
set ABHEDYA_START_DATASET=default
python -m abhedya serve --host 127.0.0.1 --port 8000
```

---

## What You Can Do NOW

### 1. View Dashboard
- Open http://127.0.0.1:8001
- See live metrics: **1.99M transactions, 24.8K accounts, 11.8K flagged**

### 2. Run Your First Investigation
1. Click **"Investigate"** in sidebar
2. Enter victim account: `KKBK10000000` (pre-filled)
3. Click **"Trace Money Trail →"**
4. Watch the **multi-layer graph** appear in seconds
5. Click any **node** to see account details
6. Click **"Isolate Connected Syndicate"** to focus on that subgraph

### 3. Explore Mule Layers
1. After tracing, click **"Mule Chain Layers"** tab
2. See the 3-column breakdown:
   - **L1 Collector Mules** (RED) — Direct victim recipients
   - **L2 Distributor Mules** (AMBER) — High fan-out pass-through
   - **L3 Terminal Cash-Out** (PURPLE) — Crypto/foreign IP/wallets
3. Click **"Isolate Subgraph →"** on any account

### 4. Use Timeline Playback
1. In **"Interactive Graph"** tab, scroll down to timeline slider
2. Click **▶ Play** to animate transactions chronologically
3. Watch the graph **grow over time** as funds flow
4. Use slider to **scrub through history**

### 5. Inspect Risk Indicators
1. Click **"Topologies & Risk Analysis"** tab
2. See **High-Velocity Pass-Through** panel (90% dispersal, 15min window)
3. See **Terminal Cash-Out Indicators** (4 markers detected)

### 6. Generate Legal Reports
1. After tracing, click **"Evidence & Reports"** in sidebar
2. Click **"Generate Case Diary (PDF/HTML) →"**
3. Wait for "Generated case-diary successfully!"
4. See file path in output: `C:\Users\SHASHWAT SEN\Desktop\og\data\reports\<evidence_id>-case-diary.pdf`
5. Open the PDF — it's a **proper formatted document** (not raw HTML)

### 7. Search Any Account
1. Click **"Account Lookup"** in sidebar
2. Enter account prefix: `AIRP` or `KKBK`
3. Click **"Search Accounts →"**
4. Click **"Inspect"** to see full transaction history
5. Click **"Trace"** to launch full money trail trace

### 8. Save & Manage Cases
1. After a successful trace, click **"+ Save as Case"**
2. Click **"Create Case"** in modal
3. Go to **"Cases"** in sidebar
4. Click **"View Case Dossier →"** on any case
5. Click **"Generate Case Diary (PDF)"** or **"Generate Freeze Requisition (PDF)"**

---

## Sample Test Victims

Try these accounts from the 2M dataset:

- `KKBK10000000` — 82 nodes, 87 edges, ₹455K siphoned
- `AIRP10001015` — Real alphanumeric account format
- `SBIN10000000` — State Bank accounts
- `HDFC10000000` — HDFC Bank accounts

---

## Dataset Information

**Currently Loaded:** `default` dataset

**Stats:**
- Transactions: **1,997,748** (rejected: 2,252)
- Accounts: **24,873**
- Flagged Accounts: **11,851** (47.6%)
- Connected Rings: **2**
- Ingestion Time: **13.17s**

**Source File:** `data/inbox/VoidHacks8_MuleAccount_2M_Transactions.csv` (274 MB)

---

## Keyboard Shortcuts

- **Graph:**
  - Scroll = Zoom
  - Drag = Pan
  - Click Node = Select & show details
  - Click Edge = Show transaction details
  - Click Canvas = Deselect

---

## Troubleshooting

### Server Already Running on Port 8000?
Use port 8001 instead:
```batch
python -m abhedya serve --host 127.0.0.1 --port 8001
```

### Dataset Not Loaded?
Set environment variable:
```batch
set ABHEDYA_START_DATASET=default
python -m abhedya serve --host 127.0.0.1 --port 8000
```

### Need to Re-ingest Dataset?
```batch
python -m abhedya ingest data/inbox/VoidHacks8_MuleAccount_2M_Transactions.csv
```

### Frontend Not Building?
```batch
cd frontend
npm install
npm run build
```

---

## API Endpoints (for testing)

```bash
# Health check
curl http://127.0.0.1:8001/api/health

# Metrics
curl http://127.0.0.1:8001/api/metrics

# Trace a victim (4 hops)
curl http://127.0.0.1:8001/api/trace/KKBK10000000?max_hops=4

# Search accounts
curl http://127.0.0.1:8001/api/accounts/search?q=KKBK

# List cases
curl http://127.0.0.1:8001/api/cases

# Benchmarks
curl http://127.0.0.1:8001/api/benchmarks
```

---

## Performance Expectations

| Operation | Target | Actual |
|-----------|--------|--------|
| Dataset ingestion (2M rows) | ≤60s | **13.2s** ⚡ |
| 4-hop trace | ≤2s | **0.44s** ⚡ |
| Graph render (82 nodes) | — | Instant ⚡ |
| Timeline playback | — | Smooth ⚡ |
| PDF generation | — | <1s ⚡ |

---

## What's Different Now?

### Before This Fix
- ❌ Graph had no interactivity (no clicks)
- ❌ No layer visualization (all nodes same color)
- ❌ No timeline slider (static list only)
- ❌ No subgraph isolation
- ❌ No high-velocity panel
- ❌ No terminal indicators display
- ❌ No case creation UI
- ❌ No account search
- ❌ PDFs contained raw HTML tags
- ❌ Windows /api/metrics crashed

### After This Fix
- ✅ **Full graph interactivity** (node/edge clicks, detail panels)
- ✅ **L1/L2/L3 color-coded layers** (red/amber/purple)
- ✅ **Timeline slider with ▶ Play/⏸ Pause** (animated playback)
- ✅ **One-click subgraph isolation** + reset
- ✅ **High-velocity detection panel** (90% dispersal metrics)
- ✅ **Terminal indicators panel** (4 markers visualized)
- ✅ **Case creation + management** (full CRUD)
- ✅ **Account search + inspection** (prefix search, txn history)
- ✅ **Proper PDF reports** (formatted tables, court-ready)
- ✅ **Cross-platform metrics** (psutil for Windows)

---

## Next Steps for Production

1. **Set Production API Key:**
   ```batch
   set ABHEDYA_ENV=production
   set ABHEDYA_API_KEY=<generate 32+ random characters>
   ```

2. **Configure Reverse Proxy (nginx):**
   ```nginx
   location / {
       proxy_pass http://127.0.0.1:8000;
       proxy_set_header X-API-Key $secure_api_key;
   }
   ```

3. **Use Systemd Service (Linux):**
   ```bash
   sudo cp deploy/abhedya.service /etc/systemd/system/
   sudo systemctl enable abhedya
   sudo systemctl start abhedya
   ```

4. **Set Up TLS:**
   - Use Let's Encrypt with Certbot
   - Configure nginx/caddy for HTTPS termination

5. **Configure Firewall:**
   ```bash
   sudo ufw allow from <reverse-proxy-IP> to any port 8000
   ```

---

## Documentation

- **Full Report:** `PRODUCTION_READINESS_REPORT.md`
- **Architecture:** `docs/ARCHITECTURE.md`
- **Benchmarks:** `docs/BENCHMARKS.md`
- **Detection Rules:** `docs/DETECTION.md`
- **Security:** `docs/SECURITY.md`
- **Production Guide:** `docs/PRODUCTION.md`

---

## Support

For issues or questions:
1. Check server logs: `logs/app.jsonl`
2. Review `PRODUCTION_READINESS_REPORT.md`
3. Test individual endpoints with curl
4. Check browser console for frontend errors

---

**Status:** ✅ **FULLY OPERATIONAL**  
**Server:** http://127.0.0.1:8001  
**Dataset:** 1,997,748 transactions loaded  
**All PS Requirements:** ✅ SATISFIED

**Ready to investigate financial cybercrimes!** 🚀
