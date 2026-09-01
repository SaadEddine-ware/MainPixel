# MainPixel Development Workflow

## Server Details
- **IP:** 178.105.115.123
- **SSH:** `ssh -i ~/.ssh/orema_deploy root@178.105.115.123`
- **Project:** `/opt/MainPixel`
- **Backend:** `/opt/MainPixel/backend`
- **Venv:** `/opt/MainPixel/venv`
- **API:** `http://178.105.115.123:8000`
- **pgAdmin:** `http://178.105.115.123:5050`

## Daily Work Limit
- **Max 10 hours/day** of active development
- Track time with start/stop timestamps
- Log all work in `WORK_LOG.md`

## Work Protocol

### 1. Start of Day
```bash
ssh -i ~/.ssh/orema_deploy root@178.105.115.123
cd /opt/MainPixel
git pull
source venv/bin/activate
# Start tmux session
tmux new-session -d -s work
tmux send-keys -t work "cd /opt/MainPixel/backend && source ../venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" Enter
```

### 2. During Development
- Write code on server via SSH
- Test each endpoint with curl
- Commit after each feature unit
- Push to GitHub after commit

### 3. End of Day
```bash
# Commit all work
git add -A
git commit -m "feat: [description]"
git push origin main

# Log work done
# Send email summary
```

## Communication
- **Email:** sghamri20@gmail.com
- Send email after every change, issue, or milestone
- Check for new messages before starting work

## Phase Progress
| Phase | Status | Hours Used |
|-------|--------|------------|
| 0 | ✅ Done | ~2h |
| 1 | 🔄 In Progress | 0h |
| 2 | ⏳ Pending | 0h |
| 3 | ⏳ Pending | 0h |
| 4 | ⏳ Pending | 0h |
| 5 | ⏳ Pending | 0h |
| 6 | ⏳ Pending | 0h |
| 7 | ⏳ Pending | 0h |
| 8 | ⏳ Pending | 0h |
| 9 | ⏳ Pending | 0h |

## Time Log
| Date | Start | End | Hours | Work Done |
|------|-------|-----|-------|-----------|
| 2026-08-30 | 08:00 | 08:30 | 0.5 | Phase 0: Server setup, backend core |
