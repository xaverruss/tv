#!/usr/bin/env python3
"""Pull an AVM SatIP RTSP stream over UDP and report real data flow.

Usage: rtsp_pull.py <rtsp-url> [seconds]
"""
import socket
import sys
import re
import time
from urllib.parse import urlparse

SECS = 5.0
if len(sys.argv) > 2:
    try:
        SECS = float(sys.argv[2])
    except ValueError:
        pass
TIMEOUT = 6.0


def recv_response(sock):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(65536)
        if not chunk:
            break
        data += chunk
    head, _, rest = data.partition(b"\r\n\r\n")
    headers, status = {}, ""
    lines = head.split(b"\r\n")
    if lines:
        status = lines[0].decode("latin1")
    for ln in lines[1:]:
        if b":" in ln:
            k, v = ln.split(b":", 1)
            headers[k.strip().lower().decode("latin1")] = v.strip().decode("latin1")
    cl = int(headers.get("content-length", "0") or 0)
    body = rest
    while len(body) < cl:
        chunk = sock.recv(65536)
        if not chunk:
            break
        body += chunk
    return status, headers, body


def request(sock, method, url, cseq, extra=""):
    req = f"{method} {url} RTSP/1.0\r\nCSeq: {cseq}\r\nUser-Agent: m3u-pull\r\n{extra}\r\n"
    sock.sendall(req.encode())
    return recv_response(sock)


def even_udp_pair():
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("0.0.0.0", 0))
        p = s.getsockname()[1]
        if p % 2 == 0:
            return s, p
        s.close()


def main():
    url = sys.argv[1]
    u = urlparse(url)
    host, port = u.hostname, u.port or 554
    rtp_sock, cport = even_udp_pair()
    rtp_sock.settimeout(1.0)

    with socket.create_connection((host, port), timeout=TIMEOUT) as s:
        s.settimeout(TIMEOUT)
        st, hdrs, body = request(s, "DESCRIBE", url, 1, "Accept: application/sdp\r\n")
        sdp = body.decode("latin1", "replace")
        cbase = hdrs.get("content-base", url)
        m = re.search(r"a=control:(\S+)", sdp)
        ctrl = m.group(1) if m else None
        candidates = [cbase]
        if ctrl and ctrl != "*":
            candidates.append(f"rtsp://{host}:{port}/{ctrl}")
        session = ""
        chosen = None
        setups = []
        transport = f"RTP/AVP;unicast;client_port={cport}-{cport + 1}"
        for i, cand in enumerate(candidates):
            st, hdrs, _ = request(s, "SETUP", cand, 2 + i,
                                  f"Transport: {transport}\r\n")
            setups.append((cand, st, hdrs.get("transport", "")))
            if st.startswith("RTSP/1.0 200"):
                chosen = cand
                session = hdrs.get("session", "").split(";")[0]
                # UDP hole-punch: off-subnet RTSP peers get no RTP unless the
                # client sends a datagram to the server's RTP port first.
                spm = re.search(r"server_port=(\d+)", hdrs.get("transport", ""))
                if spm:
                    for _ in range(3):
                        try:
                            rtp_sock.sendto(b"\x00\x00\x00\x00", (host, int(spm.group(1))))
                        except OSError:
                            pass
                break
        play_status = ""
        if chosen:
            st, hdrs, _ = request(s, "PLAY", cbase, 10,
                                  f"Session: {session}\r\nRange: npt=0.000-\r\n")
            play_status = st
        packets = bytes_total = 0
        deadline = time.time() + SECS
        while chosen and time.time() < deadline:
            try:
                data, _ = rtp_sock.recvfrom(65535)
            except socket.timeout:
                continue
            packets += 1
            bytes_total += len(data)
        if chosen:
            try:
                request(s, "TEARDOWN", cbase, 11, f"Session: {session}\r\n")
            except Exception:
                pass

    print(f"control  : {ctrl}   content-base-set={cbase != url}")
    print(f"setups   :")
    for c, st, tr in setups:
        print(f"   {st:<18} {tr}   <- {c}")
    print(f"PLAY     : {play_status}")
    print(f"RTP(UDP) : pkts={packets} bytes={bytes_total}  over {SECS}s  ~{bytes_total/SECS/1000:.0f} kB/s")


if __name__ == "__main__":
    main()
