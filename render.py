"""Draw QQ Music cards in Python; no browser, JavaScript or template engine."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
FONT = ROOT / "astrbot_assets" / "fonts" / "QQM-CJK-Regular.otf"
SOURCE_COLORS = {
    "qq": "#31c27c",
    "netease": "#e60026",
    "kugou": "#2b7fff",
    "kuwo": "#ffb300",
    "bilibili": "#fb7299",
    "qishui": "#00c2b3",
    "migu": "#ff6a00",
    "apple": "#b6255b",
    "youtube": "#ff0033",
}

THEME_SPECS = {
    "classic": {
        "style": "classic",
        "light": {
            "bg1": "#e6f6ee", "bg2": "#d9f7e9", "panel": "#ffffff",
            "panel2": "#f5fbf8", "text": "#14263a", "muted": "#5f706f",
            "line": "#d6e8de", "accent": "#0f8f63", "accent2": "#31c27c",
            "soft": "#e8f7ef",
        },
        "dark": {
            "bg1": "#0f1a16", "bg2": "#14251e", "panel": "#17251f",
            "panel2": "#1d3028", "text": "#eef8f3", "muted": "#a8c2b7",
            "line": "#2b4439", "accent": "#65e5ad", "accent2": "#31c27c",
            "soft": "#203a2f",
        },
    },
    "apple": {
        "style": "apple",
        "light": {
            "bg1": "#f8f9fc", "bg2": "#f2f5fa", "panel": "#ffffff",
            "panel2": "#f6f7f9", "text": "#1d1d1f", "muted": "#6e6e73",
            "line": "#e5e5ea", "accent": "#0071e3", "accent2": "#2997ff",
            "soft": "#eaf3ff",
        },
        "dark": {
            "bg1": "#0d0e11", "bg2": "#111319", "panel": "#1c1c1e",
            "panel2": "#2c2c2e", "text": "#f5f5f7", "muted": "#a1a1a6",
            "line": "#3a3a3c", "accent": "#2997ff", "accent2": "#64b5ff",
            "soft": "#1a2a3d",
        },
    },
    "nebula": {
        "style": "nebula",
        "light": {
            "bg1": "#eae0cc", "bg2": "#f4ecdc", "panel": "#fbf6ec",
            "panel2": "#f0e6d4", "text": "#17130f", "muted": "#6b5b48",
            "line": "#d8c6a8", "accent": "#8a6a35", "accent2": "#b8955a",
            "soft": "#efe3cd",
        },
        "dark": {
            "bg1": "#1a1417", "bg2": "#100d12", "panel": "#1f1a17",
            "panel2": "#2a231d", "text": "#f5efe3", "muted": "#b8a98f",
            "line": "#3a2f24", "accent": "#d3b481", "accent2": "#e5cda1",
            "soft": "#332a20",
        },
    },
    "multi": {
        "style": "multi",
        "light": {
            "bg1": "#f5f7fb", "bg2": "#eff2f8", "panel": "#ffffff",
            "panel2": "#f7f8fb", "text": "#12151b", "muted": "#667085",
            "line": "#e1e5ec", "accent": "#4f6bff", "accent2": "#7c8cff",
            "soft": "#edf1ff",
        },
        "dark": {
            "bg1": "#0c0f14", "bg2": "#101520", "panel": "#171b22",
            "panel2": "#1d222b", "text": "#eef1f6", "muted": "#9aa4b2",
            "line": "#2a313d", "accent": "#7c8cff", "accent2": "#a8b4ff",
            "soft": "#20283a",
        },
    },
}
WIDTH = 960
HEIGHT_LIMIT = 4800
MEDIA_DOMAINS = ("y.gtimg.cn", "i.gtimg.cn", "p.qpic.cn", "qpic.cn")


def _s(value):
    if value is None:
        return ""
    return str(value).replace("\x00", "")[:600].strip()


def _join(*values):
    return "  ·  ".join(s for value in values if (s := _s(value)))


def _label(key, val):
    return f"{key}：{_s(val)}" if _s(val) else ""


def _dicts(values, limit=35):
    return [value for value in (values or ()) if isinstance(value, dict)][:limit]


@dataclass(frozen=True)
class Row:
    title: str
    detail: str = ""
    badge: str = ""
    section: bool = False
    source: str = ""
    source_label: str = ""


@dataclass
class Card:
    label: str
    title: str
    subtitle: str = ""
    tip: str = ""
    rows: list[Row] = field(default_factory=list)
    cover: str = ""
    stats: list[tuple[str, str]] = field(default_factory=list)


def _commands(rows, commands):
    commands = _dicts(commands, 8)
    if commands:
        rows.append(Row("常用指令", section=True))
    rows.extend(Row(_s(c.get("name")), _join(c.get("example"), c.get("desc"))) for c in commands)


def describe(kind: str, data: dict) -> Card:
    """Normalize card payloads into bounded text, sections and safe optional cover."""
    kind = kind.removeprefix("qqmusic-")
    if kind == "help":
        card = Card("使用指南", "QQ 音乐", _join(data.get("version"), data.get("statQuality"), data.get("statMode")))
        for section in _dicts(data.get("sections"), 10):
            card.rows.append(Row(_s(section.get("title")), badge=_s(section.get("tag")), section=True))
            card.rows.extend(Row(_s(item.get("name")), _join(item.get("example"), item.get("desc")))
                             for item in _dicts(section.get("items"), 12))
    elif kind == "list":
        card = Card("搜索结果", _s(data.get("keyword")) or "歌曲列表")
        card.stats = [
            ("命中", f"{data.get('total', 0)} 首"),
            ("音质", _s(data.get("quality")) or "AUTO"),
            ("选曲", "#qqm听N"),
        ]
        for i, song in enumerate(_dicts(data.get("songs")), start=1):
            card.rows.append(Row(
                _s(song.get("songName")) or "未知曲目",
                _join(song.get("singerName"), song.get("albumName"), song.get("duration"),
                      "需会员" if song.get("payplay") else "", "MV" if song.get("hasMv") else ""),
                f"{i:02d}",
                source=_s(song.get("source")).lower(),
                source_label=_s(song.get("sourceLabel")),
            ))
        _commands(card.rows, data.get("commands"))
    elif kind == "hot":
        card = Card("热搜与推荐", _s(data.get("title")) or "QQ 音乐热搜", _s(data.get("subtitle")))
        for i, item in enumerate(_dicts(data.get("items")), start=1):
            card.rows.append(Row(_s(item.get("word")), _label("热度", item.get("hot")), f"{i:02d}"))
    elif kind in ("detail", "lyric", "poster", "comment"):
        label = {"detail": "曲目详情", "lyric": "歌词", "poster": "歌词海报", "comment": "热门评论"}[kind]
        if kind == "detail" and data.get("source") == "MV":
            label = "MV 详情"
        card = Card(label, _s(data.get("songName")) or "QQ 音乐",
                    _join(data.get("singerName"), data.get("albumName")), cover=_s(data.get("cover")))
        if kind == "detail":
            card.rows = [Row(k, _s(data.get(v))) for k, v in
                         (("来源", "source"), ("时长", "duration"), ("音质", "qualityLabel")) if data.get(v)]
            if data.get("showPay") and data.get("payplay"):
                card.rows.append(Row("播放权限", "该版本可能需要会员"))
        elif kind in ("lyric", "poster"):
            card.rows = [Row(_s(line)) for line in (data.get("lines") or ())[:36] if _s(line)]
        else:
            card.rows = [Row(_s(c.get("nick")) or "匿名", _s(c.get("content")),
                             _join(c.get("time"), f"赞 {c.get('likes')}" if c.get("likes") else "")[:23])
                         for c in _dicts(data.get("comments"), 20)]
    elif kind == "status":
        card = Card("账号与连接", _s(data.get("title")) or "QQ 音乐状态", _s(data.get("subtitle")))
        card.rows = [Row(k, _s(data.get(v))) for k, v in (
            ("昵称", "nickname"), ("QQ 号", "uin"), ("登录方式", "loginTypeText"),
            ("凭据状态", "keyStatus"), ("会员", "vipTitle"), ("会员状态", "vipStateText"),
            ("有效期", "vipExpireText"), ("音质", "musicQuality"), ("API", "apiBase"),
        ) if data.get(v)]
        for state in _dicts(data.get("stats"), 12):
            card.rows.append(Row(_s(state.get("label")), _s(state.get("value"))))
    elif kind == "settings":
        card = Card("插件配置", _s(data.get("title")) or "QQ 音乐设置", _s(data.get("subtitle")))
        card.rows = [Row(_s(r.get("k")), _s(r.get("v"))) for r in _dicts(data.get("rows"), 18)]
        _commands(card.rows, data.get("commands"))
    else:
        card = Card("音乐与演出", _s(data.get("title")) or "QQ 音乐", _s(data.get("subtitle")))
        card.rows = [Row(_s(row)) for row in (data.get("rows") or ())[:30] if _s(row)]
    card.tip = _join(data.get("tip"), data.get("apiHint"))
    return card


def _spec(cfg):
    cfg = cfg or {}
    theme_name = str(cfg.get("uiTheme") or "classic")
    if theme_name not in THEME_SPECS:
        theme_name = "classic"
    mode = cfg.get("uiDark")
    dark = mode == "深色" or (mode == "自动" and not 6 <= datetime.now().hour < 18)
    spec = THEME_SPECS[theme_name]["dark" if dark else "light"]
    return spec, theme_name, dark, THEME_SPECS[theme_name]["style"]


def _palette(cfg):
    spec, _, _, _ = _spec(cfg)
    return (
        spec["bg1"], spec["bg2"], spec["accent"], spec["panel"],
        spec["panel2"], spec["text"], spec["muted"], spec["line"],
    )


def web_palette(cfg):
    """Return the same palette used by cards for the plugin WebUI."""
    cfg = cfg or {}
    spec, theme_name, dark, style = _spec(cfg)
    return {
        "theme": theme_name,
        "mode": str(cfg.get("uiDark") or "浅色"),
        "dark": dark,
        "style": style,
        "bg": spec["bg1"],
        "bg2": spec["bg2"],
        "brand": spec["accent"],
        "panel": spec["panel"],
        "panel2": spec["panel2"],
        "text": spec["text"],
        "muted": spec["muted"],
        "line": spec["line"],
    }


def _font(cfg, size):
    for candidate in (
        str(cfg.get("renderFontPath") or ""), str(FONT),
        r"C:\Windows\Fonts\msyh.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ):
        if not candidate:
            continue
        try:
            return ImageFont.truetype(candidate, size)
        except (OSError, ValueError):
            continue
    raise RuntimeError("没有可用的中文字体")


def _wrap(text, font, width, cap):
    lines = []
    for paragraph in _s(text).splitlines():
        line = ""
        for char in paragraph:
            if line and font.getlength(line + char) > width:
                lines.append(line)
                if len(lines) >= cap:
                    return lines[:-1] + [lines[-1].rstrip()[:-1] + "…"]
                line = char
            else:
                line += char
        lines.append(line)
        if len(lines) >= cap:
            break
    return lines


def _rgb(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def _mix(fg, bg, amount):
    a, b = _rgb(fg), _rgb(bg)
    return tuple(round(x * amount + y * (1 - amount)) for x, y in zip(a, b))


def _redraw(card, target, cfg, cover):
    spec, theme_name, dark, style = _spec(cfg)
    start, end = spec["bg1"], spec["bg2"]
    accent, accent2 = spec["accent"], spec["accent2"]
    panel, rail, text, subtle, line, soft = (
        spec["panel"], spec["panel2"], spec["text"], spec["muted"], spec["line"], spec["soft"]
    )
    brand, display, main, small, footer = (_font(cfg, s) for s in (17, 47, 24, 18, 14))
    margin = 48
    inner = WIDTH - margin * 2
    radius = {"classic": 28, "apple": 26, "nebula": 30, "multi": 26}[style]
    art_size = 128 if card.cover else 0
    header_width = inner - 48 - (art_size + 24 if art_size else 0)
    titles = _wrap(card.title, display, header_width, 3) or ["QQ 音乐"]
    subs = _wrap(card.subtitle, main, header_width, 2)
    stats_h = 54 if card.stats else 0
    header_height = max(
        188 if art_size else 148,
        90 + len(titles) * 62 + len(subs) * 32 + stats_h,
    )
    tip = _wrap(card.tip, small, inner - 44, 4)
    available = HEIGHT_LIMIT - 185 - header_height - len(tip) * 26
    planned = []
    for row in card.rows[:80]:
        tag = _wrap(row.badge, brand, 180, 1)
        space = inner - 54 - (int(brand.getlength(tag[0])) + 56 if tag else 0)
        bottom_space = max(140, space - (86 if row.source_label else 0))
        top_lines = _wrap(row.title, main, space, 3)
        bottom_lines = _wrap(row.detail, small, bottom_space, 4)
        height = 21 + 32 * len(top_lines) + 27 * len(bottom_lines) + (6 if bottom_lines else 0)
        if height + 7 > available:
            tip = ["内容较长，更多内容可用对应文字指令查看。", *tip[:2]]
            break
        planned.append((row, tag, top_lines, bottom_lines, height))
        available -= height + 7
    height = (
        114 + header_height + sum(entry[-1] + 7 for entry in planned)
        + (len(tip) * 26 + 19 if tip else 0) + 34
    )
    canvas = Image.new("RGB", (WIDTH, height), panel)
    draw = ImageDraw.Draw(canvas)
    rgb_a, rgb_b = _rgb(start), _rgb(end)
    for y in range(height):
        draw.line(
            (0, y, WIDTH, y),
            fill=tuple(a + (b - a) * y // height for a, b in zip(rgb_a, rgb_b)),
        )
    draw.rounded_rectangle(
        (24, 24, WIDTH - 24, height - 24),
        radius=radius,
        fill=panel,
        outline=line,
        width=1 if style in {"apple", "multi"} else 2,
    )
    if style == "nebula":
        draw.rounded_rectangle(
            (26, 26, WIDTH - 26, height - 26),
            radius=radius + 1,
            outline=accent2,
            width=1,
        )
    if style in {"nebula", "multi"}:
        draw.line((margin, 45, WIDTH - margin, 45), fill=accent2, width=3)
    elif style == "apple":
        draw.line((margin, 45, WIDTH - margin, 45), fill=line, width=1)
    else:
        draw.line((margin, 45, WIDTH - margin, 45), fill=soft, width=2)
    draw.rounded_rectangle((margin, 52, margin + 44, 96), radius=12, fill=accent)
    try:
        with Image.open(ROOT / "logo.png") as origin:
            logo = ImageOps.contain(origin.convert("RGBA"), (38, 38))
            canvas.paste(logo, (margin + 3, 55), logo)
    except OSError:
        pass
    draw.text((margin + 62, 62), "QQ MUSIC  ·  点歌", font=brand, fill=accent, anchor="lt")
    draw.line((margin, 109, WIDTH - margin, 109), fill=line, width=1)
    draw.text((margin, 128), card.label, font=small, fill=accent, anchor="lt")
    cursor = 165
    for title in titles:
        draw.text((margin, cursor), title, font=display, fill=text, anchor="lt")
        cursor += 62
    for subtitle in subs:
        draw.text((margin, cursor), subtitle, font=main, fill=subtle, anchor="lt")
        cursor += 32
    if card.stats:
        chip_x, chip_y = margin, cursor + 4
        for label, value in card.stats[:3]:
            lw = int(small.getlength(label))
            vw = int(main.getlength(value))
            chip_w = lw + vw + 30
            draw.rounded_rectangle(
                (chip_x, chip_y, chip_x + chip_w, chip_y + 44),
                radius=11,
                fill=soft,
                outline=_mix(accent, soft, 0.25),
                width=1,
            )
            draw.text((chip_x + 10, chip_y + 9), label, font=small, fill=subtle, anchor="lt")
            draw.text((chip_x + 14 + lw, chip_y + 4), value, font=main, fill=text, anchor="lt")
            chip_x += chip_w + 10
        cursor += stats_h
    if art_size:
        x = WIDTH - margin - art_size
        mask = Image.new("L", (art_size, art_size))
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, art_size - 1, art_size - 1), radius=18, fill=255)
        if cover:
            canvas.paste(ImageOps.fit(cover, (art_size, art_size)), (x, 127), mask)
        else:
            draw.rounded_rectangle((x, 127, x + art_size, 127 + art_size), fill=rail, radius=18)
            draw.ellipse((x + 42, 191, x + 65, 211), fill=accent)
            draw.line((x + 63, 198, x + 63, 159, x + 84, 153), width=5, fill=accent)
    cursor = 83 + header_height
    for row, tag, tops, bottoms, row_h in planned:
        if not row.section:
            draw.rounded_rectangle(
                (margin, cursor, WIDTH - margin, cursor + row_h),
                radius=15 if style == "nebula" else 13,
                fill=rail,
            )
            if row.source and style == "multi":
                source_color = SOURCE_COLORS.get(row.source, accent)
                draw.rounded_rectangle(
                    (margin + 1, cursor + 10, margin + 5, cursor + row_h - 10),
                    radius=2,
                    fill=source_color,
                )
        if tag:
            right = WIDTH - margin - 14
            tw = int(brand.getlength(tag[0])) + 22
            draw.rounded_rectangle(
                (right - tw, cursor + 10, right, cursor + 37),
                radius=8,
                fill=soft if style in {"apple", "multi"} else None,
                outline=accent,
                width=1,
            )
            draw.text((right - 11, cursor + 13), tag[0], font=brand, fill=accent, anchor="rt")
        if row.source_label and not row.section:
            source_color = SOURCE_COLORS.get(row.source, accent)
            label = row.source_label[:8]
            sw = int(footer.getlength(label)) + 22
            sx = WIDTH - margin - 14 - sw
            sy = cursor + row_h - 29
            draw.rounded_rectangle(
                (sx, sy, sx + sw, sy + 22),
                radius=7,
                fill=_mix(source_color, rail, 0.16),
            )
            draw.text((sx + 11, sy + 2), label, font=footer, fill=source_color, anchor="lt")
        x_text = margin + (18 if row.source and not row.section else 14)
        y = cursor + 12
        for t in tops:
            draw.text((x_text, y), t, font=main, fill=accent if row.section else text, anchor="lt")
            y += 32
        for t in bottoms:
            draw.text((x_text, y), t, font=small, fill=subtle, anchor="lt")
            y += 27
        cursor += row_h + 7
    for t in tip:
        draw.text((margin + 8, cursor + 3), t, font=small, fill=subtle, anchor="lt")
        cursor += 26
    draw.text((WIDTH - margin, height - 19), "qqmusic-plugin", font=footer, fill=subtle, anchor="rb")
    path = Path(target)
    options = {"format": "PNG", "compress_level": 4} if path.suffix.lower() == ".png" else {
        "format": "JPEG", "quality": 89, "optimize": True,
    }
    canvas.save(path, **options)


async def _artwork(raw: str):
    """Fetch one public artwork only when opted in; don't forward tokens/redirects."""
    try:
        url = urlsplit(raw)
        host = url.hostname or ""
        if url.scheme != "https" or url.port or url.username or url.password or url.query or not any(
            host == suffix or host.endswith("." + suffix) for suffix in MEDIA_DOMAINS
        ):
            return None
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2.5)) as client:
            async with client.get(url.geturl(), allow_redirects=False) as res:
                if res.status != 200 or res.content_type not in {"image/jpeg", "image/png", "image/webp"}:
                    return None
                parts = bytearray()
                async for chunk in res.content.iter_chunked(65536):
                    parts.extend(chunk)
                    if len(parts) > 2_000_000:
                        return None
        return await asyncio.to_thread(_decode_cover, parts)
    except (aiohttp.ClientError, OSError, ValueError, TimeoutError, Image.DecompressionBombError):
        return None


def _decode_cover(payload):
    with Image.open(BytesIO(payload), formats=("JPEG", "PNG", "WEBP")) as image:
        if image.width * image.height > 4_000_000:
            return None
        image.thumbnail((384, 384))
        return image.convert("RGB")


class Renderer:
    def __init__(self):
        self._limit = asyncio.Semaphore(2)
        self._active = set()
        self._closed = False

    async def render(self, kind, data, target, cfg):
        async with self._limit:
            if self._closed:
                raise RuntimeError("绘图组件已关闭")
            card = describe(kind, data)
            job = asyncio.create_task(self._render(card, target, cfg))
            self._active.add(job)
            job.add_done_callback(self._active.discard)
            try:
                await asyncio.shield(job)
            except asyncio.CancelledError:
                # A worker thread cannot stop mid-save; keep it owned by the
                # Star and remove its artifact before propagating cancellation.
                await asyncio.gather(job, return_exceptions=True)
                Path(target).unlink(missing_ok=True)
                raise

    async def _render(self, card, target, cfg):
        cover = await _artwork(card.cover) if card.cover and cfg.get("renderCover", False) else None
        await asyncio.to_thread(_redraw, card, target, cfg, cover)

    async def close(self):
        self._closed = True
        await asyncio.gather(*self._active, return_exceptions=True)
