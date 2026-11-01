"""Stdlib-only mock of an OpenAI-compatible /v1/chat/completions endpoint.

P2.0 recon: proves that a runtime built ONLY from requirements.txt can run a
real translation round-trip. Responds to any POST ending in /chat/completions.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

LOG = []


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        LOG.append(body)
        try:
            user_text = body["messages"][-1]["content"]
            if isinstance(user_text, list):
                user_text = user_text[-1].get("text", "")
        except Exception:
            user_text = ""
        resp = {
            "id": "chatcmpl-mock", "object": "chat.completion", "created": 0,
            "model": body.get("model", "mock"),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": f"MOCK:{user_text}"},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        }
        data = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        LOG.append(fmt % args)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18923
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
