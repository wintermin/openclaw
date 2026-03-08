#!/bin/bash
# Intercepts agent-browser calls and redirects screenshot paths to /tmp/openclaw/
# /tmp/openclaw/ is in OpenClaw's assertLocalMediaAllowed whitelist.
# Original binary moved to agent-browser-real during Docker build.
export AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/chromium
export AGENT_BROWSER_ARGS="--no-sandbox,--disable-dev-shm-usage"

mkdir -p /tmp/openclaw

ORIG_PATH=""
NEWARGS=()
PREV=""
for arg in "$@"; do
  if [ "$PREV" = "screenshot" ] && [[ "$arg" == /* ]] && [[ "$arg" != /tmp/openclaw/* ]]; then
    BASENAME=$(basename "$arg")
    ORIG_PATH="$arg"
    NEWARGS+=("/tmp/openclaw/$BASENAME")
  else
    NEWARGS+=("$arg")
  fi
  PREV="$arg"
done

/usr/local/bin/agent-browser-real "${NEWARGS[@]}"
EXIT_CODE=$?

# Create symlink at original path so native send_image tool finds it.
# fs.realpath resolves symlink -> /tmp/openclaw/xxx which passes the whitelist check.
if [ $EXIT_CODE -eq 0 ] && [ -n "$ORIG_PATH" ]; then
  BASENAME=$(basename "$ORIG_PATH")
  ln -sf "/tmp/openclaw/$BASENAME" "$ORIG_PATH" 2>/dev/null || true
fi

exit $EXIT_CODE
