#!/usr/bin/env python3
"""G3.2 probe: fake loopback OpenAI-compatible endpoint + request-body traps.

Modes:
  capture <stage_dir>   Run against the PRE-EDIT code (HEAD). Records the exact
                        request bodies (byte-for-byte) a custom profile WITHOUT
                        the new fields produces (plain + vision calls). These
                        files are the regression reference for matrix item 7.
  verify  <stage_dir>   Run against the POST-EDIT code. Executes probe matrix
                        items 1-11 against the same fake endpoint.

Nothing outside 127.0.0.1 is contacted: every request is served by the local
ThreadingHTTPServer; the trap assertion checks the Host header of every
recorded request is the loopback endpoint.

Usage (bundled runtime, project root as CWD):
  E:/Dev/python-embed/python.exe -u docs/refactoring/audits/batch-g32_fake_endpoint_probe.py capture D:/Temp/SupervertalerPortable/refactoring/batch-g32
  E:/Dev/python-embed/python.exe -u docs/refactoring/audits/batch-g32_fake_endpoint_probe.py verify  D:/Temp/SupervertalerPortable/refactoring/batch-g32
"""

import hashlib
import json
import os
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT)

from modules.llm_clients import LLMClient  # noqa: E402

SECRET_REASONING = "SECRET-REASONING-MUST-NOT-LEAK"
VISION_B64 = "ZmFrZSBpbWFnZSBkYXRhIC0gRzMuMiBwcm9iZSBvbmx5"  # fake image payload


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_completion(content, finish="stop", reasoning=None, reasoning_tokens=None):
    message = {"role": "assistant", "content": content}
    if reasoning is not None:
        message["reasoning_content"] = reasoning
    choice = {"index": 0, "message": message, "finish_reason": finish}
    usage = {"prompt_tokens": 11, "completion_tokens": 23}
    if reasoning_tokens is not None:
        usage["completion_tokens_details"] = {"reasoning_tokens": reasoning_tokens}
    return {
        "id": "chatcmpl-probe-g32",
        "object": "chat.completion",
        "created": 1730000000,
        "model": "probe-model",
        "choices": [choice],
        "usage": usage,
    }


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(length)
        self.server.bodies.append(raw)
        self.server.hosts.append(self.headers.get("host"))
        spec = self.server.responses.popleft() if self.server.responses else {"json": make_completion("x")}
        if spec.get("delay"):
            time.sleep(spec["delay"])
        payload = json.dumps(spec["json"], ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except OSError:
            pass  # client timed out and closed the connection

    def log_message(self, *args):
        pass


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.responses = deque()
        self.bodies = []
        self.hosts = []


def start_server():
    srv = Server()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def make_client(port, **kw):
    kw.setdefault("api_key", "not-needed")
    kw.setdefault("provider", "custom_openai")
    kw.setdefault("model", "probe-model")
    kw.setdefault("base_url", f"http://127.0.0.1:{port}/v1")
    return LLMClient(**kw)


def call_plain(client, srv, spec):
    srv.responses.clear()
    srv.responses.append(spec)
    text, usage = client.translate_with_usage(
        "Hello world", source_lang="en", target_lang="nl")
    return text, usage


def call_vision(client, srv, spec):
    srv.responses.clear()
    srv.responses.append(spec)
    text, usage = client.translate_with_usage(
        "Hello vision", source_lang="en", target_lang="nl",
        images=[("seg5.png", VISION_B64)])
    return text, usage


# ---------------------------------------------------------------------------
# capture (pre-edit)
# ---------------------------------------------------------------------------

def capture(stage):
    out = os.path.join(stage, "capture")
    os.makedirs(out, exist_ok=True)
    srv, port = start_server()

    manifest = {"mode": "capture", "python": sys.version, "port": port, "cases": {}}

    c = make_client(port)
    text, usage = call_plain(c, srv, {"json": make_completion("Привет мир")})
    body = srv.bodies[-1]
    with open(os.path.join(out, "req_plain.body"), "wb") as f:
        f.write(body)
    manifest["cases"]["plain"] = {
        "sha256": sha(body),
        "bytes": len(body),
        "returned_text": text,
        "usage": usage,
        "host_seen": srv.hosts[-1],
    }

    c2 = make_client(port, supports_vision=True)
    text2, usage2 = call_vision(c2, srv, {"json": make_completion("Vision OK")})
    body2 = srv.bodies[-1]
    with open(os.path.join(out, "req_vision.body"), "wb") as f:
        f.write(body2)
    manifest["cases"]["vision"] = {
        "sha256": sha(body2),
        "bytes": len(body2),
        "returned_text": text2,
        "usage": usage2,
        "host_seen": srv.hosts[-1],
    }

    with open(os.path.join(out, "capture_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"CAPTURE done: plain={manifest['cases']['plain']['sha256'][:16]} "
          f"vision={manifest['cases']['vision']['sha256'][:16]} -> {out}")
    srv.shutdown()


# ---------------------------------------------------------------------------
# verify (post-edit) — matrix 1..11
# ---------------------------------------------------------------------------

def verify(stage):
    from modules.llm_clients import (
        LLMTruncatedError,
        LLMEmptyResponseError,
        LLMTimeoutError,
        set_llm_log_callback,
        parse_profile_request_fields,
    )

    out = os.path.join(stage, "verify")
    os.makedirs(out, exist_ok=True)
    srv, port = start_server()
    results = []

    def record(name, ok, detail):
        results.append({"item": name, "ok": bool(ok), "detail": detail})
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")

    def expect_exc(name, fn, exc_type, contains=(), not_contains=()):
        try:
            value = fn()
            record(name, False, f"expected {exc_type.__name__}, got return {value!r}")
        except exc_type as exc:
            msg = str(exc)
            missing = [c for c in contains if c not in msg]
            leaked = [c for c in not_contains if c in msg]
            record(name, not missing and not leaked,
                   f"{exc_type.__name__}: {msg!r}"
                   + (f" missing={missing}" if missing else "")
                   + (f" leaked={leaked}" if leaked else ""))
        except Exception as exc:
            record(name, False, f"expected {exc_type.__name__}, got {type(exc).__name__}: {exc}")

    # 1 — normal finish=stop: result byte-identical to canned content
    c = make_client(port)
    text, usage = call_plain(c, srv, {"json": make_completion("Привет мир")})
    body = json.loads(srv.bodies[-1].decode("utf-8"))
    record("1-normal-stop",
           text == "Привет мир" and "extra_body" not in body
           and usage.get("input_tokens") == 11 and usage.get("output_tokens") == 23
           and srv.hosts[-1] == f"127.0.0.1:{port}",
           f"text={text!r} usage={usage} host={srv.hosts[-1]}")

    # 2 — think/thinking stripping
    strip_cases = [
        ("<think>deep thought</think>Привет", "Привет"),
        ("<think>a</think>mid<think>b</think>Привет", "midПривет"),
        ("<Think>deep</Think>Привет", "Привет"),
        ("<thinking>deep</thinking>Привет", "Привет"),
        ("<thinking>\nline1\nline2\n</thinking>Привет", "Привет"),
        ("<think>deep</think>   ", "Привет"),  # canned text irrelevant; expect exception
    ]
    strip_ok = True
    strip_detail = []
    for i, (content, expected) in enumerate(strip_cases[:5]):
        text, _ = call_plain(make_client(port), srv, {"json": make_completion(content)})
        strip_ok = strip_ok and text == expected
        strip_detail.append(f"case{i+1}: got {text!r} want {expected!r}")
    # 2f: content only think-block + spaces, finish stop -> empty after strip
    def strip2f():
        return call_plain(make_client(port), srv,
                          {"json": make_completion(strip_cases[5][0])})
    try:
        v, _ = strip2f()
        strip_ok = False
        strip_detail.append(f"case6: expected LLMEmptyResponseError, got {v!r}")
    except LLMEmptyResponseError as exc:
        strip_detail.append(f"case6: LLMEmptyResponseError: {exc}")
    except Exception as exc:
        strip_ok = False
        strip_detail.append(f"case6: expected LLMEmptyResponseError, got {type(exc).__name__}: {exc}")
    record("2-think-stripping", strip_ok, " | ".join(strip_detail))

    # 3 — unclosed <think> + finish=length -> LLMTruncatedError
    def s3():
        return call_plain(make_client(port), srv,
                          {"json": make_completion("<think>reasoning that never closes", finish="length")})
    expect_exc("3-unclosed-think-length", s3, LLMTruncatedError,
               contains=["length", "Max tokens"])

    # 4 — empty content + reasoning + finish=length -> LLMTruncatedError
    def s4():
        return call_plain(make_client(port), srv,
                          {"json": make_completion("", finish="length",
                                                   reasoning=SECRET_REASONING, reasoning_tokens=12345)})
    def s4_run():
        try:
            s4()
            return None
        except LLMTruncatedError as exc:
            return exc
    exc4 = s4_run()
    if exc4 is None:
        record("4-reasoning-exhausted-length", False, "no exception raised")
    else:
        record("4-reasoning-exhausted-length",
               exc4.finish_reason == "length" and exc4.has_reasoning is True
               and exc4.reasoning_tokens == 12345
               and "Max tokens" in str(exc4) and "Extra request body" in str(exc4)
               and SECRET_REASONING not in str(exc4),
               f"finish={exc4.finish_reason} has_reasoning={exc4.has_reasoning} "
               f"reasoning_tokens={exc4.reasoning_tokens} msg={str(exc4)!r}")

    # 5 — empty content + reasoning + finish=stop -> LLMEmptyResponseError
    def s5():
        return call_plain(make_client(port), srv,
                          {"json": make_completion("", finish="stop", reasoning=SECRET_REASONING)})
    expect_exc("5-reasoning-only-stop", s5, LLMEmptyResponseError,
               contains=["stop", "reasoning"], not_contains=[SECRET_REASONING])

    # 6 — non-empty content + finish=length -> return + log warning
    log_lines = []
    set_llm_log_callback(log_lines.append)
    text6, usage6 = call_plain(make_client(port), srv,
                               {"json": make_completion("Partial answer", finish="length")})
    set_llm_log_callback(None)
    warned = any("truncat" in ln.lower() for ln in log_lines)
    record("6-nonempty-length-warning", text6 == "Partial answer" and warned,
           f"text={text6!r} log={log_lines}")

    # 7 — regression: request body without new fields byte-equal to pre-edit capture
    cap_dir = os.path.join(stage, "capture")
    s7_ok, s7_detail = True, []
    for label, fn in (("plain", lambda: call_plain(make_client(port), srv,
                                                   {"json": make_completion("Привет мир")})),
                      ("vision", lambda: call_vision(make_client(port, supports_vision=True), srv,
                                                     {"json": make_completion("Vision OK")}))):
        fn()
        new_body = srv.bodies[-1]
        ref_path = os.path.join(cap_dir, f"req_{label}.body")
        ref = open(ref_path, "rb").read()
        same = new_body == ref
        s7_ok = s7_ok and same
        s7_detail.append(f"{label}: {'byte-equal' if same else f'DIFF new={sha(new_body)[:16]} ref={sha(ref)[:16]}'}")
    record("7-body-regression", s7_ok, " | ".join(s7_detail))

    # 8 — extra_body forwarded into request body
    eb = {"chat_template_kwargs": {"enable_thinking": False}}
    c8 = make_client(port, extra_body=eb)
    call_plain(c8, srv, {"json": make_completion("OK")})
    body8 = json.loads(srv.bodies[-1].decode("utf-8"))
    record("8-extra-body-forwarded",
           body8.get("chat_template_kwargs") == {"enable_thinking": False},
           f"body keys={sorted(body8.keys())} chat_template_kwargs={body8.get('chat_template_kwargs')}")

    # 9 — profile timeout applied: fake endpoint delay > timeout -> timeout message
    def s9():
        c9 = make_client(port, timeout_seconds=0.5, profile_name="ProbeProfile")
        srv.responses.clear()
        # The SDK retries timeouts (max_retries=2 default): every attempt must
        # hit the delay so the final raised APITimeoutError gets wrapped.
        for _ in range(3):
            srv.responses.append({"json": make_completion("too late"), "delay": 1.5})
        return c9.translate_with_usage("Hello", source_lang="en", target_lang="nl")
    expect_exc("9-profile-timeout", s9, LLMTimeoutError,
               contains=["ProbeProfile", "0.5"])

    # 10 — save validation blocks invalid values
    bad_cases = [
        ("not json", "extra_body invalid json"),
        ("[1, 2]", "extra_body not an object"),
        ('{"model": "x"}', "forbidden key model"),
        ('{"messages": []}', "forbidden key messages"),
        ('{"max_tokens": 10}', "forbidden key max_tokens"),
        ('{"stream": true}', "forbidden key stream"),
        ('{"tools": []}', "forbidden key tools"),
    ]
    s10_ok, s10_detail = True, []
    for raw, label in bad_cases:
        _, _, _, errors = parse_profile_request_fields({"extra_body": raw})
        ok = len(errors) > 0
        s10_ok = s10_ok and ok
        s10_detail.append(f"{label}: {'blocked' if ok else 'NOT BLOCKED'} ({errors})")
    for raw, label in [("abc", "max_tokens non-number"), ("-3", "timeout_min non-positive")]:
        if label.startswith("max"):
            _, _, _, errors = parse_profile_request_fields({"max_tokens": raw})
        else:
            _, _, _, errors = parse_profile_request_fields({"timeout_min": raw})
        s10_ok = s10_ok and len(errors) > 0
        s10_detail.append(f"{label} {raw!r}: {'blocked' if errors else 'NOT BLOCKED'} ({errors})")
    mt, to, ebv, errors = parse_profile_request_fields(
        {"max_tokens": "5000", "timeout_min": "5", "extra_body": '{"chat_template_kwargs": {"enable_thinking": false}}'})
    s10_ok = s10_ok and not errors and mt == 5000 and to == 300.0 \
        and ebv == {"chat_template_kwargs": {"enable_thinking": False}}
    s10_detail.append(f"valid: mt={mt} to={to} eb={ebv} errors={errors}")
    record("10-save-validation", s10_ok, " | ".join(s10_detail))

    # 11 — vision request carries the same profile params
    c11 = make_client(port, supports_vision=True, max_tokens=1234,
                      timeout_seconds=45, extra_body=eb)
    text11, _ = call_vision(c11, srv, {"json": make_completion("Vision answer")})
    body11 = json.loads(srv.bodies[-1].decode("utf-8"))
    parts = body11["messages"][-1]["content"]
    has_image = isinstance(parts, list) and any(
        p.get("type") == "image_url" and VISION_B64 in p["image_url"]["url"] for p in parts)
    record("11-vision-profile-params",
           text11 == "Vision answer" and has_image
           and body11.get("max_tokens") == 1234
           and body11.get("chat_template_kwargs") == {"enable_thinking": False},
           f"image_parts={has_image} max_tokens={body11.get('max_tokens')} "
           f"chat_template_kwargs={body11.get('chat_template_kwargs')}")

    # network trap assertion: every recorded request went to the loopback endpoint
    bad_hosts = sorted({h for h in srv.hosts if h != f"127.0.0.1:{port}"})
    record("net-traps", not bad_hosts, f"requests={len(srv.hosts)} foreign_hosts={bad_hosts}")

    with open(os.path.join(out, "verify_matrix.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    n_fail = sum(1 for r in results if not r["ok"])
    print(f"VERIFY done: {len(results) - n_fail}/{len(results)} PASS -> {out}")
    srv.shutdown()
    sys.exit(1 if n_fail else 0)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    mode, stage = sys.argv[1], sys.argv[2]
    os.makedirs(stage, exist_ok=True)
    if mode == "capture":
        capture(stage)
    elif mode == "verify":
        verify(stage)
    else:
        print(f"unknown mode {mode!r}")
        sys.exit(2)


if __name__ == "__main__":
    main()
