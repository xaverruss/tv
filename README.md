# TV – M3U-Playlists für IPTV

Sammlung von M3U-Playlists für IPTV-Streams.

## Verwendung

Die Playlists können mit jedem IPTV-Player genutzt werden, der das M3U-Format unterstützt (z. B. **VLC**, **Kodi**, **IPTV Smarters**, **TiviMate**).

### VLC (Desktop / Mobile)

```
VLC öffnen → Medien → Netzwerkstream öffnen → URL der M3U-Datei einfügen
```

Oder direkt per Kommandozeile:

```bash
vlc https://raw.githubusercontent.com/xaverruss/tv/main/m3u/steiermark-fb.m3u
```

### Kodi

1. PVR-Client **PVR IPTV Simple Client** installieren
2. Addon-Einstellungen → **M3U-Playlist-URL** → URL der gewünschten M3U-Datei eintragen
3. Neustarten

## Playlists

| Datei | Beschreibung |
|-------|-------------|
| `m3u/kieffer-fb.m3u` | Playlist Kieffer (FB) |
| `m3u/steiermark-fb.m3u` | Playlist Steiermark (FB) |

## EPG (Elektronischer Programmführer)

Die Playlists enthalten keine EPG-URLs. Für eine Programmübersicht kann eine externe EPG-XML-Datei im IPTV-Player hinterlegt werden.

### Empfohlene EPG-Quellen

| Quelle | URL | Sender | Hinweis |
|--------|-----|--------|---------|
| **iptv-epg.org** | `https://iptv-epg.org/files/epg-de.xml` | 422 deutsche Sender | **Beste Abdeckung** – hat fast alle Sender aus den Playlists (RTL, ProSieben, SAT.1, ZDF, ARD, etc.) |
| Open-EPG | `https://www.open-epg.com/files/germany3.xml.gz` | 334 deutsche Sender | Gute Alternative, 2-Tage-EPG |
| electronic-research.de | `https://electronic-research.de/kodi/epg/epg.xml.gz` | ~198 Sender (DE + HR) | Auch Balkan-Sender, aber weniger deutsche Privatsender |

### Integration

#### Kodi (PVR IPTV Simple Client)

1. Addon-Einstellungen → **EPG-Einstellungen**
2. **XMLTV-URL** → eine der obigen URLs eintragen
3. Neustarten

#### TiviMate

1. Einstellungen → **EPG** → **EPG-Quelle hinzufügen**
2. URL einfügen

#### VLC

VLC unterstützt kein EPG aus externen XML-Dateien – hierfür einen dedizierten IPTV-Player verwenden.

> **Tipp:** Die EPG-Sender-IDs in der XML-Datei müssen mit den Kanalnamen in der M3U-Datei übereinstimmen, damit die Zuordnung funktioniert. Die Kanalnamen in den Playlists sind i. d. R. ähnlich genug für eine automatische Erkennung.

## Quelle

**GitHub:** [https://github.com/xaverruss/tv](https://github.com/xaverruss/tv)

> **Hinweis:** Die Stream-URLs in den Playlists sind nur innerhalb des jeweiligen Netzwerks erreichbar (RTSP-Lokal-IPs).
