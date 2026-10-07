import socket, re, time, sys
from urllib.parse import urlparse

M3U = sys.argv[1]
SECS = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
HOST = "10.7.2.1"
sendonly_host = None


def read_resp(tcp):
    data = b""
    while b"\r\n\r\n" not in data:
        c = tcp.recv(65536)
        if not c:
            break
        data += c
    head, _, rest = data.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    status = lines[0].decode("latin1") if lines else ""
    hdrs = {}
    for ln in lines[1:]:
        if b":" in ln:
            k, v = ln.split(b":", 1)
            hdrs[k.strip().lower().decode("latin1")] = v.strip().decode("latin1")
    cl = int(hdrs.get("content-length", "0") or 0)
    body = rest
    while len(body) < cl:
        body += tcp.recv(65536)
    return status, hdrs, body


def send(tcp, m, target, cseq, extra=""):
    tcp.sendall(f"{m} {target} RTSP/1.0\r\nCSeq: {cseq}\r\nUser-Agent: x\r\n{extra}\r\n".encode())


def pull(url, secs):
    u = urlparse(url)
    host, port = u.hostname, u.port or 554
    tcp = socket.create_connection((host, port), timeout=6)
    tcp.settimeout(4.0)
    try:
        send(tcp, "DESCRIBE", url, 1, "Accept: application/sdp\r\n")
        st, h, b = read_resp(tcp)
        cb = h.get("content-base", url)
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.bind(("0.0.0.0", 0))
        cp = udp.getsockname()[1]
        if cp % 2:
            udp.close()
            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp.bind(("0.0.0.0", 0))
            cp = udp.getsockname()[1]
        send(tcp, "SETUP", cb, 2, f"Transport: RTP/AVP;unicast;client_port={cp}-{cp+1}\r\n")
        st, h, b = read_resp(tcp)
        setup_ok = st.startswith("RTSP/1.0 200")
        sess = h.get("session", "").split(";")[0]
        spm = re.search(r"server_port=(\d+)", h.get("transport", ""))
        if spm:
            for _ in range(3):
                try:
                    udp.sendto(b"\x00\x00\x00\x00", (host, int(spm.group(1))))
                except Exception:
                    pass
        play_ok = False
        if setup_ok:
            send(tcp, "PLAY", cb, 3, f"Session: {sess}\r\nRange: npt=0.000-\r\n")
            st, h, b = read_resp(tcp)
            play_ok = st.startswith("RTSP/1.0 200")
        udp.settimeout(1.0)
        t0 = time.time()
        by = pk = 0
        while time.time() < t0 + secs:
            try:
                d, _ = udp.recvfrom(65535)
                pk += 1
                by += len(d)
            except socket.timeout:
                pass
        try:
            send(tcp, "TEARDOWN", cb, 4, f"Session: {sess}\r\n")
            read_resp(tcp)
        except Exception:
            pass
        udp.close()
        return setup_ok, play_ok, by, pk
    finally:
        tcp.close()


def main():
    entries = []
    name = None
    with open(M3U, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("#EXTINF:"):
                name = line.split(",", 1)[1] if "," in line else ""
            elif line.startswith("rtsp://"):
                entries.append((name, line))
    print(f"{'idx':>3} {'name':<22} {'freq':>5} {'qam':>5} {'kB/s':>7} {'setup':>5} {'play':>5}")
    for i, (n, url) in enumerate(entries, 1):
        fm = re.search(r"freq=(\d+)", url)
        qm = re.search(r"mtype=(\w+)", url)
        freq = fm.group(1) if fm else "?"
        qam = qm.group(1) if qm else "?"
        try:
            so, po, by, pk = pull(url, SECS)
            kbs = by / SECS / 1000
            flag = "" if kbs > 50 else "   <== BAD"
            print(f"{i:>3} {n:<22} {freq:>5} {qam:>5} {kbs:7.0f} {str(so):>5} {str(po):>5}{flag}")
        except Exception as e:
            print(f"{i:>3} {n:<22} {freq:>5} {qam:>5}      - {type(e).__name__}   <== ERR")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
