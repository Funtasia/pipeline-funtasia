#!/bin/sh

detect_python() {
    local PYTHON_CMD=""

    if command -v python >/dev/null 2>&1; then
        PYTHON_CMD="python"
    elif command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python3"
    else
        echo "[FAIL] Python not found"
        return 1
    fi

    local VERSION
    VERSION=$("$PYTHON_CMD" --version 2>&1)

    local EXE
    EXE=$(command -v "$PYTHON_CMD")

    echo "[PASS] Python detected"
    echo "  Version : $VERSION"
    echo "  Command : $PYTHON_CMD"
    echo "  Path    : $EXE"

    return 0
}

detect_python