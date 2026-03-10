#!/bin/bash
# ============================================================
# 🏎️ GitHub Auto-Commit Scheduler
# Checks for changes daily and creates meaningful commits
# ============================================================

REPO_DIR="/home/diegokernel/proyectos"
LOG_FILE="$HOME/.github_scheduler.log"
BRANCH="dev"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Navigate to repo
cd "$REPO_DIR" || { log "❌ Cannot access $REPO_DIR"; exit 1; }

# Ensure we have a dev branch
if ! git rev-parse --verify "$BRANCH" &>/dev/null; then
    git checkout -b "$BRANCH" 2>/dev/null
    log "📌 Created branch '$BRANCH'"
else
    git checkout "$BRANCH" 2>/dev/null
fi

# Check for changes
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    log "✅ No changes detected. Skipping."
    exit 0
fi

# ============================================================
# Build a smart commit message based on what changed
# ============================================================
CHANGES=""
COMPONENTS=()

# Check each component for changes
if git diff --name-only --diff-filter=ACDMR | grep -q "^apps/" || git ls-files --others --exclude-standard | grep -q "^apps/"; then
    COMPONENTS+=("dashboards")
fi
if git diff --name-only --diff-filter=ACDMR | grep -q "^games/" || git ls-files --others --exclude-standard | grep -q "^games/"; then
    COMPONENTS+=("game recorders")
fi
if git diff --name-only --diff-filter=ACDMR | grep -q "^scripts/" || git ls-files --others --exclude-standard | grep -q "^scripts/"; then
    COMPONENTS+=("scripts")
fi
if git diff --name-only --diff-filter=ACDMR | grep -q "^lakehouse/" || git ls-files --others --exclude-standard | grep -q "^lakehouse/"; then
    COMPONENTS+=("lakehouse")
fi

# Count changes
NUM_MODIFIED=$(git diff --name-only | wc -l)
NUM_NEW=$(git ls-files --others --exclude-standard | wc -l)

# Build commit message
if [ ${#COMPONENTS[@]} -eq 0 ]; then
    COMMIT_MSG="🔄 Update project files"
else
    COMPONENT_STR=$(IFS=', '; echo "${COMPONENTS[*]}")
    COMMIT_MSG="🔄 Update $COMPONENT_STR"
fi

# Add details
DETAILS=""
[ "$NUM_MODIFIED" -gt 0 ] && DETAILS="$NUM_MODIFIED modified"
[ "$NUM_NEW" -gt 0 ] && DETAILS="$DETAILS${DETAILS:+, }$NUM_NEW new"

if [ -n "$DETAILS" ]; then
    COMMIT_MSG="$COMMIT_MSG ($DETAILS)"
fi

# Stage, commit, push
git add .
git commit -m "$COMMIT_MSG"

if git push origin "$BRANCH" 2>&1; then
    log "✅ Pushed: $COMMIT_MSG"
else
    log "❌ Push failed. Will retry next run."
    exit 1
fi

log "🏁 Done."
