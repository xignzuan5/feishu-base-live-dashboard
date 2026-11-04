"""Thin wrapper around `lark-cli` for scripts in this skill.

All calls run as the logged-in user (`--as user`). Large JSON payloads are
written to a temp file under the current working directory and passed as
`@relative/path`, because lark-cli only accepts cwd-relative file paths.
"""
import json
import os
import subprocess
import tempfile
import time

TMP_DIR = ".lark-tmp"


class LarkError(RuntimeError):
    pass


def _payload_arg(payload):
    os.makedirs(TMP_DIR, exist_ok=True)
    fd, path = tempfile.mkstemp(prefix="payload-", suffix=".json", dir=TMP_DIR)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    return "@" + os.path.relpath(path), path


def run(args, payload=None, payload_flag="--json", retries=3):
    """Run `lark-cli <args>` and return the parsed JSON envelope's `data`."""
    cmd = ["lark-cli"] + list(args)
    if "--as" not in cmd:
        cmd += ["--as", "user"]
    tmp_path = None
    if payload is not None:
        ref, tmp_path = _payload_arg(payload)
        cmd += [payload_flag, ref]
    try:
        last_err = None
        for attempt in range(retries):
            proc = subprocess.run(cmd, capture_output=True, text=True)
            out = proc.stdout.strip()
            try:
                env = json.loads(out) if out else {}
            except json.JSONDecodeError:
                env = {}
            if proc.returncode == 0 and env.get("ok", True):
                return env.get("data", env)
            err = env.get("error") or {}
            msg = err.get("message") or proc.stderr.strip() or out
            last_err = "%s\n  hint: %s" % (msg, err.get("hint", ""))
            # 1254291 = concurrent write conflict; back off and retry.
            if "1254291" in out or "rate" in msg.lower() or "timeout" in msg.lower():
                time.sleep(2 * (attempt + 1))
                continue
            break
        raise LarkError("lark-cli %s failed: %s" % (" ".join(args[:2]), last_err))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def find_key(obj, key):
    """Depth-first search for the first value stored under `key`."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = find_key(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_key(v, key)
            if found is not None:
                return found
    return None


def batch_create(base_token, table_id, rows, batch_size=200, on_batch=None):
    """Create records in serial batches (max 200 per call). Returns record ids in input order."""
    ids = []
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        data = run(
            ["base", "+record-batch-create", "--base-token", base_token, "--table-id", table_id],
            payload={"create_records": chunk},
        )
        got = find_key(data, "record_id_list")
        if got is None:
            recs = find_key(data, "records") or []
            got = [r.get("record_id") for r in recs]
        if len(got) != len(chunk):
            raise LarkError("batch create returned %d ids for %d rows: %s" % (len(got), len(chunk), str(data)[:300]))
        ids.extend(got)
        if on_batch:
            on_batch(i + len(chunk), len(rows), got)
    return ids


def batch_update(base_token, table_id, updates, batch_size=200):
    """updates: {record_id: {field: value}}"""
    items = list(updates.items())
    for i in range(0, len(items), batch_size):
        chunk = dict(items[i:i + batch_size])
        run(
            ["base", "+record-batch-update", "--base-token", base_token, "--table-id", table_id],
            payload={"update_records": chunk},
        )
