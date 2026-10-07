#!/usr/bin/env python3
"""Probe RTSP streams from an M3U: send DESCRIBE, report status + SDP media info."""
import socket
import sys
import re
from urllib.parse import urlparse

TIMEOUT = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 0


def recv_response(sock):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    head, sep, rest = data.partition(b"\r\n\r\n")
    headers = {}
    lines = head.split(b"\r\n")
    status = lines[0].decode("latin1") if lines else ""
    for ln in lines[1:]:
        if b":" in ln:
            k, v = ln.split(b":", 1)
            headers[k.strip().lower()] = v.strip()
    cl = 0
    if b"content-length" in headers:
        try:
            cl = int(headers[b"content-length"])
        except ValueError:
            cl = 0
    body = rest
    while len(body) < cl:
        chunk = sock.recv(4096)
        if not chunk:
            break
        body += chunk
    return status, headers, body


def describe(url):
    u = urlparse(url)
    host, port = u.hostname, u.port or 554
    req = (
        f"DESCRIBE {url} RTSP/1.0\r\n"
        "CSeq: 1\r\n"
        "Accept: application/sdp\r\n"
        "User-Agent: m3u-probe\r\n\r\n"
    ).encode()
    with socket.create_connection((host, port), timeout=TIMEOUT) as s:
        s.settimeout(TIMEOUT)
        s.sendall(req)
        status, headers, body = recv_response(s)
    return status, headers, body


def summarize_sdp(body):
    txt = body.decode("latin1", "replace")
    codecs = re.findall(r"a=rtpmap:\d+\s+([^\r\n]+)", txt)
    has_video = "m=video" in txt
    has_audio = "m=audio" in txt
    return has_video, has_audio, codecs


def read_m3u(path):
    out = []
    name = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("#EXTINF:"):
                name = line.split(",", 1)[1] if "," in line else ""
            elif line.startswith("rtsp://"):
                out.append((name, line))
    return out


def main():
    path = sys.argv[1]
    entries = read_m3u(path)
    if LIMIT:
        entries = entries[:LIMIT]
    ok = fail = 0
    for name, url in entries:
        try:
            status, _, body = describe(url)
            has_v, has_a, codecs = summarize_sdp(body)
            good = status.startswith("RTSP/1.0 200") and (has_v or has_a)
            tag = "OK " if good else "??? "
            if good:
                ok += 1
            else:
                fail += 1
            detail = ",".join(codecs[:4]) if codecs else ("SDP" if (has_v or has_a) else "no-sdp")
            print(f"{tag}{status:<18} {name:<28} {detail}")
        except Exception as e:
            fail += 1
            print(f"ERR {type(e).__name__:<14} {name:<28} {e}")
    print(f"\n{path}: {len(entries)} channels  ok={ok}  fail={fail}")


if __name__ == "__main__":
    main()
