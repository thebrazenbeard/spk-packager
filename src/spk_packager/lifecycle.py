from __future__ import annotations

import shlex

from .model import Manifest

NOOP_LIFECYCLE_NAMES = (
    "preinst",
    "postinst",
    "preuninst",
    "postuninst",
    "preupgrade",
    "postupgrade",
)


def noop_script() -> bytes:
    return b"#!/bin/sh\nexit 0\n"


def _runtime_arg(value: str) -> str:
    if "{pkgdest}" not in value and "{pkgvar}" not in value:
        return shlex.quote(value)
    pkgdest = "__SPK_PKGDEST__"
    pkgvar = "__SPK_PKGVAR__"
    work = value.replace("{pkgdest}", pkgdest).replace("{pkgvar}", pkgvar)
    work = (
        work.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace(chr(96), "\\" + chr(96))
        .replace("$", "\\$")
    )
    work = work.replace(pkgdest, "${SYNOPKG_PKGDEST}").replace(
        pkgvar, "${SYNOPKG_PKGVAR}"
    )
    return f'"{work}"'


def render_start_stop_status(manifest: Manifest) -> bytes:
    service = manifest.service
    if not service.enabled:
        return b"""#!/bin/sh
case "${1:-}" in
    prestart|prestop|start|stop|killall|log) exit 0 ;;
    status) exit 0 ;;
    *) exit 1 ;;
esac
"""

    command = service.command
    assert command is not None
    args = " ".join(_runtime_arg(arg) for arg in service.args)
    arg_suffix = f" {args}" if args else ""
    state_mkdir = "\n".join(
        f'        mkdir -p "${{SYNOPKG_PKGVAR}}/{item}"'
        for item in service.state_dirs
    )
    if state_mkdir:
        state_mkdir += "\n"

    script = f"""#!/bin/sh
set -eu

PIDFILE="${{SYNOPKG_PKGVAR}}/{service.pid_file}"
LOGFILE="${{SYNOPKG_PKGVAR}}/{service.log_file}"
BIN="${{SYNOPKG_PKGDEST}}/{command}"

is_running() {{
    [ -f "$PIDFILE" ] || return 1
    pid="$(cat "$PIDFILE" 2>/dev/null || true)"
    [ -n "$pid" ] || return 1
    kill -0 "$pid" 2>/dev/null
}}

report_start_failure() {{
    if [ -n "${{SYNOPKG_TEMP_LOGFILE:-}}" ]; then
        {{
            echo "Package service failed to start."
            if [ -r "$LOGFILE" ]; then
                echo
                echo "Last service log lines:"
                tail -n 100 "$LOGFILE" 2>/dev/null || true
            fi
        }} >"$SYNOPKG_TEMP_LOGFILE"
    fi
}}

stop_service() {{
    if ! is_running; then
        rm -f "$PIDFILE"
        return 0
    fi
    pid="$(cat "$PIDFILE")"
    kill -TERM "$pid" 2>/dev/null || true
    i=0
    while kill -0 "$pid" 2>/dev/null && [ "$i" -lt {service.stop_timeout_seconds} ]; do
        sleep 1
        i=$((i + 1))
    done
    if kill -0 "$pid" 2>/dev/null; then
        kill -KILL "$pid" 2>/dev/null || true
    fi
    rm -f "$PIDFILE"
}}

case "${{1:-}}" in
    prestart)
        [ -n "${{SYNOPKG_PKGDEST:-}}" ] || exit 1
        [ -n "${{SYNOPKG_PKGVAR:-}}" ] || exit 1
        [ -x "$BIN" ] || {{
            if [ -n "${{SYNOPKG_TEMP_LOGFILE:-}}" ]; then
                echo "Package executable is missing or not executable: $BIN" >"$SYNOPKG_TEMP_LOGFILE"
            fi
            exit 1
        }}
        exit 0
        ;;
    prestop)
        exit 0
        ;;
    start)
        if is_running; then
            exit 0
        fi
        rm -f "$PIDFILE"
        umask 077
        mkdir -p "${{SYNOPKG_PKGVAR}}"
{state_mkdir}        nohup "$BIN"{arg_suffix} >>"$LOGFILE" 2>&1 &
        echo "$!" >"$PIDFILE"
        sleep {service.start_probe_seconds}
        if is_running; then
            exit 0
        fi
        rm -f "$PIDFILE"
        report_start_failure
        exit 1
        ;;
    stop)
        stop_service
        exit 0
        ;;
    killall)
        stop_service
        exit 0
        ;;
    status)
        if is_running; then
            exit 0
        fi
        if [ -f "$PIDFILE" ]; then
            exit 1
        fi
        exit 3
        ;;
    log)
        if [ -r "$LOGFILE" ]; then
            if [ -n "${{SYNOPKG_TEMP_LOGFILE:-}}" ]; then
                tail -n 100 "$LOGFILE" >"$SYNOPKG_TEMP_LOGFILE" 2>/dev/null || true
                echo "$SYNOPKG_TEMP_LOGFILE"
            else
                echo "$LOGFILE"
            fi
        fi
        exit 0
        ;;
    *)
        exit 1
        ;;
esac
"""
    return script.encode("utf-8")
