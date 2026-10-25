# -*- coding: utf-8 -*-
"""BATCH Q-C / Q.8b STEP 0 — connect/read failure matrix on CURRENT code.

Three cases from the prompt (plus the Dmitry-observed default-timeout variant):
  1. testnet-default  192.0.2.1:<port> (TEST-NET-1, packets silently dropped),
     profile default timeout (600 s) — Dmitry observed ~65 s to the
     "timed out after 10 minutes (600 s)" message (MT 1:07, LLM 1:05).
  2. testnet-short    same host, profile timeout 0.05 min (3 s).
  3. refused          127.0.0.1:1 (closed port, instant refusal).
  4. silent           loopback server that accepts TCP and never answers
     (true READ timeout), profile timeout 0.05 min (3 s).

For each: wall time, exception class chain (incl. __cause__), message text.
No product code is changed by this probe.
"""
import json, socket, sys, threading, time

TREE = r"E:\Dev\SupervertalerPortable"
OUT = r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-qc\q8\step0_connect_cases.json"
sys.path.insert(0, TREE)

# ---- silent server: accept TCP, never send a byte --------------------------
silent_srv = socket.socket()
silent_srv.bind(("127.0.0.1", 0))
silent_srv.listen(8)
SILENT_PORT = silent_srv.getsockname()[1]


def silent_loop():
    conns = []
    while True:
        try:
            c, _ = silent_srv.accept()
            conns.append(c)  # hold open, never respond
        except OSError:
            return


threading.Thread(target=silent_loop, daemon=True).start()

from modules.llm_clients import LLMClient  # noqa: E402

CASES = []


def run_case(name, endpoint, timeout_minutes):
    timeout_s = None if timeout_minutes is None else timeout_minutes * 60.0
    client = LLMClient(api_key="probe", provider="custom_openai", model="probe-model",
                       base_url=endpoint, timeout_seconds=timeout_s,
                       profile_name="Probe profile")
    t0 = time.perf_counter()
    rec = {"case": name, "endpoint": endpoint,
           "timeout_minutes": timeout_minutes}
    try:
        try:
            result = client.translate(text="hi", source_lang="en", target_lang="nl")
            rec.update(outcome="returned", result=repr(result)[:80])
        except Exception as e:
            cause = getattr(e, "__cause__", None)
            rec.update(outcome="raised",
                       exc_class=type(e).__name__,
                       exc_module=type(e).__module__,
                       cause_class=(type(cause).__name__ if cause else None),
                       exc_str=str(e)[:300])
    finally:
        rec["wall_seconds"] = round(time.perf_counter() - t0, 1)
    CASES.append(rec)
    print(json.dumps(rec, ensure_ascii=False))


# Fast cases first, slow default-timeout case last.
run_case("refused-closed-port", "http://127.0.0.1:1/v1", 0.05)
run_case("silent-server-read-timeout", f"http://127.0.0.1:{SILENT_PORT}/v1", 0.05)
run_case("testnet-short-timeout", "http://192.0.2.1:65500/v1", 0.05)
run_case("testnet-default-timeout", "http://192.0.2.1:65500/v1", None)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(CASES, f, ensure_ascii=False, indent=1)
print("STEP0-Q8B DONE", OUT)
