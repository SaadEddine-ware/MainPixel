#!/bin/bash
# MainPixel Agent Supervisor
# Runs email checker + dev workflow in tmux sessions

PROJECT_DIR="/opt/MainPixel"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
VENV="$PROJECT_DIR/venv/bin/activate"

start() {
    echo "Starting MainPixel Agent..."

    # Start email checker
    tmux new-session -d -s email-checker "cd $SCRIPTS_DIR && python3 check_emails.py"
    echo "Email checker started in tmux session 'email-checker'"

    # Send shift start email
    cd $SCRIPTS_DIR && python3 send_email.py shift_start

    echo "All services started."
    echo "  - API: http://178.105.115.123:8000 (tmux: api)"
    echo "  - Email Checker: tmux session 'email-checker'"
    echo "  - pgAdmin: http://178.105.115.123:5050"
}

stop() {
    echo "Stopping MainPixel Agent..."
    cd $SCRIPTS_DIR && python3 send_email.py shift_end

    # Generate daily report
    cd $PROJECT_DIR && REPORT=$(git log --oneline --since="today" 2>/dev/null || echo "No commits today")
    cd $SCRIPTS_DIR && python3 send_email.py report "<h3>Git Activity</h3><pre>$REPORT</pre>"

    tmux kill-session -t email-checker 2>/dev/null
    echo "Agent stopped."
}

status() {
    echo "=== MainPixel Agent Status ==="
    tmux list-sessions 2>/dev/null || echo "No tmux sessions"
}

case "$1" in
    start) start ;;
    stop) stop ;;
    status) status ;;
    restart) stop; sleep 2; start ;;
    *) echo "Usage: $0 {start|stop|status|restart}" ;;
esac
