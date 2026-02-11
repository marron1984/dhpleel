#!/usr/bin/env python3
"""
北新地 大嵓埜 — Instagram Reels 動画生成スクリプト（一品一会 ギャラリー版）

コンセプト: 美術館のように一品ずつ静かに魅せる
  - ギャラリーフレーム（余白 + 細い金線ボーダー）
  - ゆったりクロスフェード（フラッシュなし）
  - 漢数字のコース番号（壱・弐・参…）
  - タイプライター風テキスト
  - モノクロ→カラーリビール
  - フィルムグレイン + ビネット
  - ミニマルな品格で惹きつけ、最後にだけCTA

使い方:
    python3 generate_reels_video.py

出力:
    output/reels_video.mp4   — MP4動画（メイン出力）
    output/reels_video.gif   — GIFアニメーション
    output/reels_video.webp  — WebPアニメーション
    output/frames/           — 全フレーム連番PNG

必要なもの:
    pip3 install Pillow
    ffmpeg（MP4生成に必要。なくてもGIF/WebPは生成される）
"""

import os
import io
import math
import random
import shutil
import struct
import subprocess
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ── 設定 ──────────────────────────────────────────
WIDTH = 540
HEIGHT = 960
FPS = 24
BG_COLOR = (12, 12, 12)
GOLD = (186, 155, 95)
GOLD_LIGHT = (218, 198, 148)
GOLD_DIM = (120, 100, 60)
WHITE = (240, 237, 230)
GRAY = (130, 127, 122)
DARK_GRAY = (60, 58, 55)

# ギャラリーフレーム設定
FRAME_MARGIN = 40          # 写真周囲の余白
FRAME_BORDER = 1           # 金線ボーダーの太さ
PHOTO_AREA_TOP = 120       # 写真エリアの上端
PHOTO_AREA_BOTTOM = 680    # 写真エリアの下端

OUTPUT_DIR = "output"
FRAMES_DIR = os.path.join(OUTPUT_DIR, "frames")
BGM_FILE = "bgm.mp3"

# ── 画像URL ──────────────────────────────────────
IMG_EXTERIOR = "https://github.com/user-attachments/assets/6e9bb9c1-0ead-47de-b875-ac9dfde0c3b7"
IMG_SAKIZUKE = "https://github.com/user-attachments/assets/b02cc12f-1be7-4498-835c-e002b4d5afa2"
IMG_SASHIMI  = "https://github.com/user-attachments/assets/b3a7eefa-2fd5-4ce0-8830-d665a788b10d"
IMG_YAKIMONO = "https://github.com/user-attachments/assets/89d7a632-b7be-46f6-b301-5feb0b31991d"
IMG_AGEMONO  = "https://github.com/user-attachments/assets/34173214-d90e-4556-b22f-75f53e756304"
IMG_SHIIZAKA = "https://github.com/user-attachments/assets/a990a366-4d57-4cdd-8766-0c5d794f5bfc"
IMG_GOHAN    = "https://github.com/user-attachments/assets/ee7a5a4a-885d-4f95-b83c-5ee014652a4c"
IMG_DESSERT  = "https://github.com/user-attachments/assets/b39bf119-c360-47df-b8b1-5399b4445ab1"
IMG_NIMONO   = "https://github.com/user-attachments/assets/58250abe-6813-4005-9973-aaf2266b4ea6"
IMG_OWAN     = "https://github.com/user-attachments/assets/d192340c-a5af-4ef6-acd7-56ed93cb771f"

# ── 懐石コース（漢数字ナンバリング）──────────────────────
COURSE = [
    {"image": IMG_SAKIZUKE, "number": "壱", "name": "先付",  "sub": "Sakizuke"},
    {"image": IMG_SASHIMI,  "number": "弐", "name": "向付",  "sub": "Mukōzuke"},
    {"image": IMG_NIMONO,   "number": "参", "name": "煮物椀","sub": "Nimono-wan"},
    {"image": IMG_YAKIMONO, "number": "肆", "name": "焼物",  "sub": "Yakimono"},
    {"image": IMG_SHIIZAKA, "number": "伍", "name": "強肴",  "sub": "Shiizakana"},
    {"image": IMG_AGEMONO,  "number": "陸", "name": "揚物",  "sub": "Agemono"},
    {"image": IMG_OWAN,     "number": "漆", "name": "清湯",  "sub": "Sumashi"},
    {"image": IMG_GOHAN,    "number": "捌", "name": "御飯",  "sub": "Gohan"},
    {"image": IMG_DESSERT,  "number": "玖", "name": "甘味",  "sub": "Kanmi"},
]

# ── シーン構成 ──────────────────────────────────────
# type: "opening" / "course" / "text_card" / "cta"
SCENES = [
    # ━━ OPENING: 静かな導入（0-3秒）━━━━━━━━━━━━━━
    {"type": "opening", "duration": 3.0},

    # ━━ COURSE PARADE: 一品ずつ（3-18秒）━━━━━━━━━━━━
    {"type": "course", "course_idx": 0, "duration": 1.5},
    {"type": "course", "course_idx": 1, "duration": 1.5},
    {"type": "course", "course_idx": 2, "duration": 1.5},
    {"type": "course", "course_idx": 3, "duration": 1.5},
    {"type": "course", "course_idx": 4, "duration": 1.5},
    {"type": "course", "course_idx": 5, "duration": 1.3},
    {"type": "course", "course_idx": 6, "duration": 1.3},
    {"type": "course", "course_idx": 7, "duration": 1.3},
    {"type": "course", "course_idx": 8, "duration": 1.3},

    # ━━ CLOSING: 余韻 + CTA（18-23秒）━━━━━━━━━━━━━━
    {"type": "text_card", "duration": 2.0},
    {"type": "cta", "duration": 3.5},
]


# ── ヘルパー関数 ──────────────────────────────────

def download_image(url, cache_dir="output/.cache"):
    os.makedirs(cache_dir, exist_ok=True)
    filename = url.split("/")[-1]
    cache_path = os.path.join(cache_dir, filename)
    if os.path.exists(cache_path):
        print(f"  [cache] {filename}")
        return Image.open(cache_path).convert("RGB")
    print(f"  [download] {url[:80]}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.save(cache_path, "JPEG", quality=90)
    return img


def fit_cover(img, w, h):
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def ease_in_out(t):
    return t * t * (3.0 - 2.0 * t)


def ease_out_cubic(t):
    return 1 - pow(1 - t, 3)


def ease_out_quart(t):
    return 1 - pow(1 - t, 4)


# ── フォント ──────────────────────────────────────

def get_font(size, style="title"):
    mincho_paths = [
        "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc",
        "/System/Library/Fonts/ヒラギノ明朝 ProN W6.otf",
        "/Library/Fonts/Yu Mincho.ttc",
        "/usr/share/fonts/opentype/ipafont-mincho/ipamp.ttf",
        "/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf",
        "/usr/share/fonts/truetype/fonts-japanese-mincho.ttf",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSerifCJK-Regular.ttc",
    ]
    gothic_paths = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf",
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    if style in ("title", "accent", "number"):
        search_order = mincho_paths + gothic_paths
    else:
        search_order = gothic_paths + mincho_paths
    for fp in search_order:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    fallback = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for fp in fallback:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ── シネマティック映像エフェクト ──────────────────────

_COLOR_LUT_R = None
_COLOR_LUT_G = None
_COLOR_LUT_B = None
_VIGNETTE_MASK = None


def _build_color_luts():
    global _COLOR_LUT_R, _COLOR_LUT_G, _COLOR_LUT_B
    def make_lut(shadow_shift, highlight_shift, gamma):
        lut = []
        for i in range(256):
            v = i / 255.0
            v = pow(v, gamma)
            if v < 0.5:
                v += shadow_shift * (0.5 - v) * 0.12
            else:
                v += highlight_shift * (v - 0.5) * 0.06
            lut.append(max(0, min(255, int(v * 255))))
        return lut
    _COLOR_LUT_R = make_lut(shadow_shift=0.4, highlight_shift=0.05, gamma=0.98)
    _COLOR_LUT_G = make_lut(shadow_shift=0.15, highlight_shift=0.0, gamma=1.0)
    _COLOR_LUT_B = make_lut(shadow_shift=-0.2, highlight_shift=-0.05, gamma=1.02)


def _build_vignette_mask(w, h):
    global _VIGNETTE_MASK
    mask = Image.new("L", (w, h))
    pixels = mask.load()
    cx, cy = w / 2.0, h / 2.0
    max_dist = math.sqrt(cx * cx + cy * cy)
    for y in range(h):
        for x in range(w):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            ratio = dist / max_dist
            if ratio < 0.35:
                v = 0
            else:
                falloff = (ratio - 0.35) / 0.65
                v = int(255 * falloff * falloff * 0.45)
            pixels[x, y] = min(255, v)
    _VIGNETTE_MASK = mask


def apply_film_grain(frame, intensity=8, seed=None):
    rng = random.Random(seed)
    sw, sh = 135, 240
    grain_data = bytes(max(0, min(255, int(rng.gauss(128, intensity)))) for _ in range(sw * sh))
    grain_small = Image.frombytes("L", (sw, sh), grain_data)
    grain = grain_small.resize(frame.size, Image.BILINEAR)
    grain_rgb = Image.merge("RGB", [grain, grain, grain])
    return Image.blend(frame, grain_rgb, 0.04)


def apply_color_grade(frame):
    if _COLOR_LUT_R is None:
        _build_color_luts()
    r, g, b = frame.split()
    r = r.point(_COLOR_LUT_R)
    g = g.point(_COLOR_LUT_G)
    b = b.point(_COLOR_LUT_B)
    graded = Image.merge("RGB", [r, g, b])
    gray = graded.convert("L").convert("RGB")
    return Image.blend(graded, gray, 0.10)


def apply_vignette(frame):
    w, h = frame.size
    if _VIGNETTE_MASK is None or _VIGNETTE_MASK.size != (w, h):
        _build_vignette_mask(w, h)
    black = Image.new("RGB", (w, h), (0, 0, 0))
    return Image.composite(black, frame, _VIGNETTE_MASK)


def apply_cinematic(frame, frame_idx):
    frame = apply_color_grade(frame)
    frame = apply_vignette(frame)
    frame = apply_film_grain(frame, intensity=8, seed=frame_idx)
    return frame


# ── Ken Burns（控えめ）──────────────────────────────

def apply_ken_burns(img, progress, effect="zoom_in"):
    if img is None:
        return Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    pad = 1.18
    cw = WIDTH - FRAME_MARGIN * 2
    ch = PHOTO_AREA_BOTTOM - PHOTO_AREA_TOP
    base = fit_cover(img, int(cw * pad), int(ch * pad))
    bw, bh = base.size
    t = ease_in_out(progress)

    if effect == "zoom_in":
        scale = 1.0 + 0.06 * t
        cx, cy = bw / 2, bh / 2
    elif effect == "zoom_out":
        scale = 1.06 - 0.06 * t
        cx, cy = bw / 2, bh / 2
    elif effect == "pan_right":
        scale = 1.04
        cx = bw / 2 + (bw * 0.025) * (2 * t - 1)
        cy = bh / 2
    elif effect == "pan_left":
        scale = 1.04
        cx = bw / 2 - (bw * 0.025) * (2 * t - 1)
        cy = bh / 2
    else:
        scale = 1.0
        cx, cy = bw / 2, bh / 2

    crop_w = cw / scale
    crop_h = ch / scale
    left = max(0, cx - crop_w / 2)
    top = max(0, cy - crop_h / 2)
    right = min(bw, left + crop_w)
    bottom = min(bh, top + crop_h)
    if right - left < crop_w:
        left = max(0, right - crop_w)
    if bottom - top < crop_h:
        top = max(0, bottom - crop_h)

    cropped = base.crop((int(left), int(top), int(right), int(bottom)))
    return cropped.resize((cw, ch), Image.LANCZOS)


# ── ギャラリーフレーム描画 ────────────────────────────

def draw_gallery_frame(bg, photo, border_alpha=180):
    """写真をギャラリーフレーム（金線ボーダー付き）で配置"""
    frame = bg.copy()
    draw = ImageDraw.Draw(frame)

    x1 = FRAME_MARGIN
    y1 = PHOTO_AREA_TOP
    x2 = WIDTH - FRAME_MARGIN
    y2 = PHOTO_AREA_BOTTOM

    # 写真を配置
    frame.paste(photo, (x1, y1))

    # 金線ボーダー
    frame_rgba = frame.convert("RGBA")
    border_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    bd = ImageDraw.Draw(border_layer)
    border_color = (*GOLD_DIM, border_alpha)

    # 外枠
    for offset in range(FRAME_BORDER):
        bd.rectangle(
            [(x1 - 3 - offset, y1 - 3 - offset), (x2 + 3 + offset, y2 + 3 + offset)],
            outline=border_color
        )

    result = Image.alpha_composite(frame_rgba, border_layer).convert("RGB")
    return result


def draw_text_shadow(draw, pos, text, font, fill, shadow_color=(0, 0, 0), shadow_range=2):
    """テキストを影付きで描画"""
    x, y = pos
    if isinstance(fill, tuple) and len(fill) == 4:
        sa = min(120, fill[3])
    else:
        sa = 120
    for dx in range(-shadow_range, shadow_range + 1):
        for dy in range(-shadow_range, shadow_range + 1):
            if dx == 0 and dy == 0:
                continue
            if abs(dx) + abs(dy) > shadow_range + 1:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=(*shadow_color, sa))
    draw.text((x, y), text, font=font, fill=fill)


# ── シーン描画関数 ──────────────────────────────────

def render_opening(frame_idx, n_frames, images):
    """オープニング: 店名 + ミシュラン + 「懐石 全九品」"""
    t = frame_idx / max(1, n_frames - 1)
    frame = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)

    # 外観写真（モノクロ → カラー）
    exterior = images["exterior"]
    photo = apply_ken_burns(exterior, t, "zoom_in")

    # モノクロ→カラーのリビール
    mono = ImageEnhance.Color(photo).enhance(0.0)
    color_t = ease_out_quart(min(1.0, t * 1.5))  # 前半2/3でカラーに
    photo = Image.blend(mono, photo, color_t)

    frame = draw_gallery_frame(frame, photo, border_alpha=int(180 * min(1.0, t * 3)))

    # テキストオーバーレイ
    frame_rgba = frame.convert("RGBA")
    txt = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt)

    time_s = frame_idx / FPS

    # ミシュラン（0.3秒後にフェード）
    if time_s > 0.3:
        tp = min(1.0, (time_s - 0.3) / 0.8)
        alpha = int(200 * tp)
        font = get_font(14, "body")
        text = "MICHELIN SELECTED"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw_text_shadow(draw, ((WIDTH - tw) // 2, 75), text, font,
                         (*GOLD_DIM, alpha), shadow_range=1)

    # 店名「大嵓埜」（0.6秒後にタイプライター）
    if time_s > 0.6:
        tp = min(1.0, (time_s - 0.6) / 1.0)
        store_name = "大 嵓 埜"
        visible_chars = max(0, int(len(store_name) * ease_out_cubic(tp)))
        visible_text = store_name[:visible_chars]
        if visible_text:
            font = get_font(52, "title")
            bbox = draw.textbbox((0, 0), store_name, font=font)
            full_tw = bbox[2] - bbox[0]
            x = (WIDTH - full_tw) // 2
            alpha = int(255 * min(1.0, tp * 2))
            draw_text_shadow(draw, (x, PHOTO_AREA_BOTTOM + 30), visible_text,
                             font, (*WHITE, alpha))

    # 「懐石 全九品」（1.2秒後）
    if time_s > 1.2:
        tp = min(1.0, (time_s - 1.2) / 0.8)
        alpha = int(180 * tp)
        font = get_font(16, "body")
        text = "懐石   全九品"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw_text_shadow(draw, ((WIDTH - tw) // 2, PHOTO_AREA_BOTTOM + 100),
                         text, font, (*GRAY, alpha), shadow_range=1)

    # 「北新地」（1.5秒後）
    if time_s > 1.5:
        tp = min(1.0, (time_s - 1.5) / 0.6)
        alpha = int(140 * tp)
        font = get_font(13, "body")
        text = "北新地"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw_text_shadow(draw, ((WIDTH - tw) // 2, PHOTO_AREA_BOTTOM + 130),
                         text, font, (*DARK_GRAY, alpha), shadow_range=1)

    # 下部に薄いゴールドライン
    if time_s > 1.0:
        tp = min(1.0, (time_s - 1.0) / 0.6)
        line_half_w = int(60 * ease_out_cubic(tp))
        line_alpha = int(100 * tp)
        cx = WIDTH // 2
        ly = PHOTO_AREA_BOTTOM + 90
        if line_half_w > 0:
            draw.rectangle([(cx - line_half_w, ly), (cx + line_half_w, ly)],
                           fill=(*GOLD_DIM, line_alpha))

    frame = Image.alpha_composite(frame_rgba, txt).convert("RGB")
    return frame


def render_course(frame_idx, n_frames, course_data, course_img, effect):
    """コース一品: ギャラリーフレーム + 漢数字 + 料理名"""
    t = frame_idx / max(1, n_frames - 1)
    time_s = frame_idx / FPS
    frame = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)

    # 写真
    photo = apply_ken_burns(course_img, t, effect)

    # ギャラリーフレーム
    frame = draw_gallery_frame(frame, photo, border_alpha=160)

    # テキスト
    frame_rgba = frame.convert("RGBA")
    txt = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt)

    # 漢数字（左上、大きく）
    num_tp = min(1.0, time_s / 0.4)
    num_alpha = int(100 * ease_out_cubic(num_tp))
    num_font = get_font(72, "number")
    draw_text_shadow(draw, (FRAME_MARGIN + 8, PHOTO_AREA_TOP + 8),
                     course_data["number"], num_font,
                     (*GOLD_DIM, num_alpha), shadow_range=2)

    # 料理名（写真下、中央）
    name_delay = 0.2
    if time_s > name_delay:
        tp = min(1.0, (time_s - name_delay) / 0.5)
        alpha = int(240 * ease_out_cubic(tp))
        y_offset = int(8 * (1 - ease_out_cubic(tp)))
        font = get_font(36, "title")
        text = course_data["name"]
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw_text_shadow(draw, ((WIDTH - tw) // 2, PHOTO_AREA_BOTTOM + 35 + y_offset),
                         text, font, (*WHITE, alpha))

    # ローマ字サブタイトル
    sub_delay = 0.4
    if time_s > sub_delay:
        tp = min(1.0, (time_s - sub_delay) / 0.5)
        alpha = int(100 * ease_out_cubic(tp))
        font = get_font(12, "body")
        text = course_data["sub"]
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw_text_shadow(draw, ((WIDTH - tw) // 2, PHOTO_AREA_BOTTOM + 80),
                         text, font, (*DARK_GRAY, alpha), shadow_range=1)

    frame = Image.alpha_composite(frame_rgba, txt).convert("RGB")
    return frame


def render_text_card(frame_idx, n_frames):
    """テキストカード: 「一品一会」の余韻"""
    t = frame_idx / max(1, n_frames - 1)
    time_s = frame_idx / FPS
    frame = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)

    frame_rgba = frame.convert("RGBA")
    txt = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt)

    # 金線（上下）
    line_tp = min(1.0, time_s / 0.5)
    line_hw = int(40 * ease_out_cubic(line_tp))
    line_alpha = int(120 * line_tp)
    cx = WIDTH // 2
    if line_hw > 0:
        draw.rectangle([(cx - line_hw, 400), (cx + line_hw, 400)],
                       fill=(*GOLD_DIM, line_alpha))
        draw.rectangle([(cx - line_hw, 560), (cx + line_hw, 560)],
                       fill=(*GOLD_DIM, line_alpha))

    # 「一品一会」
    if time_s > 0.2:
        tp = min(1.0, (time_s - 0.2) / 0.8)
        text = "一 品 一 会"
        visible_chars = max(0, int(len(text) * ease_out_cubic(tp)))
        visible = text[:visible_chars]
        if visible:
            alpha = int(220 * min(1.0, tp * 1.5))
            font = get_font(44, "title")
            bbox = draw.textbbox((0, 0), text, font=font)
            full_tw = bbox[2] - bbox[0]
            x = (WIDTH - full_tw) // 2
            draw_text_shadow(draw, (x, 440), visible, font, (*WHITE, alpha))

    # 「季節を味わう、北新地の夜」
    if time_s > 0.8:
        tp = min(1.0, (time_s - 0.8) / 0.6)
        alpha = int(140 * tp)
        font = get_font(15, "body")
        text = "季節を味わう、北新地の夜"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw_text_shadow(draw, ((WIDTH - tw) // 2, 510), text, font,
                         (*GRAY, alpha), shadow_range=1)

    frame = Image.alpha_composite(frame_rgba, txt).convert("RGB")
    return frame


def render_cta(frame_idx, n_frames, exterior_img):
    """CTA: 控えめな予約誘導"""
    t = frame_idx / max(1, n_frames - 1)
    time_s = frame_idx / FPS
    frame = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)

    # 外観写真（暗めに）
    photo = apply_ken_burns(exterior_img, t, "zoom_in")
    darkener = ImageEnhance.Brightness(photo).enhance(0.6)
    frame = draw_gallery_frame(frame, darkener, border_alpha=100)

    frame_rgba = frame.convert("RGBA")
    txt = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt)

    # 店名
    if time_s > 0.2:
        tp = min(1.0, (time_s - 0.2) / 0.6)
        alpha = int(240 * tp)
        font = get_font(42, "title")
        text = "大 嵓 埜"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw_text_shadow(draw, ((WIDTH - tw) // 2, PHOTO_AREA_BOTTOM + 25), text,
                         font, (*WHITE, alpha))

    # ゴールドライン
    if time_s > 0.5:
        tp = min(1.0, (time_s - 0.5) / 0.4)
        hw = int(50 * ease_out_cubic(tp))
        la = int(130 * tp)
        cx = WIDTH // 2
        ly = PHOTO_AREA_BOTTOM + 80
        if hw > 0:
            draw.rectangle([(cx - hw, ly), (cx + hw, ly)], fill=(*GOLD_DIM, la))

    # 電話番号
    if time_s > 0.8:
        tp = min(1.0, (time_s - 0.8) / 0.5)
        alpha = int(220 * tp)
        font = get_font(32, "accent")
        text = "06-6341-3535"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw_text_shadow(draw, ((WIDTH - tw) // 2, PHOTO_AREA_BOTTOM + 100), text,
                         font, (*GOLD, alpha))

    # 住所
    if time_s > 1.2:
        tp = min(1.0, (time_s - 1.2) / 0.5)
        alpha = int(120 * tp)
        font = get_font(12, "body")
        text = "北新地 FOODEAR ビル 3F"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw_text_shadow(draw, ((WIDTH - tw) // 2, PHOTO_AREA_BOTTOM + 148), text,
                         font, (*DARK_GRAY, alpha), shadow_range=1)

    # 「完全予約制」
    if time_s > 1.5:
        tp = min(1.0, (time_s - 1.5) / 0.5)
        alpha = int(160 * tp)
        font = get_font(16, "body")
        text = "完 全 予 約 制"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw_text_shadow(draw, ((WIDTH - tw) // 2, PHOTO_AREA_BOTTOM + 178), text,
                         font, (*GOLD_LIGHT, alpha), shadow_range=1)

    # 「プロフィールから予約」
    if time_s > 2.0:
        tp = min(1.0, (time_s - 2.0) / 0.5)
        alpha = int(140 * tp)
        font = get_font(14, "body")
        text = "プロフィールのリンクからご予約"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        y_off = int(6 * (1 - ease_out_cubic(tp)))
        draw_text_shadow(draw, ((WIDTH - tw) // 2, PHOTO_AREA_BOTTOM + 210 + y_off),
                         text, font, (*GRAY, alpha), shadow_range=1)

    # フェードアウト（最後0.8秒）
    frame = Image.alpha_composite(frame_rgba, txt).convert("RGB")

    fade_start = 0.78
    if t > fade_start:
        fade_t = (t - fade_start) / (1.0 - fade_start)
        black = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        frame = Image.blend(frame, black, ease_in_out(fade_t))

    return frame


# ── BGM生成（フォールバック）──────────────────────────

def generate_bgm_wav(path, duration_sec):
    sr = 44100
    total_samples = int(sr * duration_sec)
    base_freqs = [293.66, 349.23, 392.00, 440.00, 523.25, 587.33, 698.46]
    rng = random.Random(42)

    def piano_tone(freq, dur, volume=0.3):
        n = int(sr * dur)
        samples = []
        for i in range(n):
            t = i / sr
            env = math.exp(-t * 3.0) * volume
            val = (math.sin(2 * math.pi * freq * t) * 0.7 +
                   math.sin(2 * math.pi * freq * 2 * t) * 0.15 +
                   math.sin(2 * math.pi * freq * 3 * t) * 0.08)
            samples.append(val * env)
        return samples

    def pad_tone(freq, dur, volume=0.08):
        n = int(sr * dur)
        samples = []
        for i in range(n):
            t = i / sr
            fi = min(1.0, t / 2.0)
            fo = min(1.0, (dur - t) / 2.0)
            env = fi * fo * volume
            val = (math.sin(2 * math.pi * freq * t) * 0.5 +
                   math.sin(2 * math.pi * freq * 1.002 * t) * 0.5)
            samples.append(val * env)
        return samples

    buf = [0.0] * total_samples
    pd = pad_tone(146.83, duration_sec, 0.06)
    pa = pad_tone(220.00, duration_sec, 0.04)
    for i in range(min(len(pd), total_samples)):
        buf[i] += pd[i] + pa[i]

    time_pos = 0.5
    while time_pos < duration_sec - 2.0:
        freq = rng.choice(base_freqs)
        note_dur = rng.choice([1.5, 2.0, 2.5, 3.0])
        vol = rng.uniform(0.15, 0.30)
        note = piano_tone(freq, note_dur, vol)
        start_idx = int(time_pos * sr)
        for i in range(min(len(note), total_samples - start_idx)):
            buf[start_idx + i] += note[i]
        time_pos += rng.uniform(1.0, 2.5)

    fade_in_s = int(sr * 1.5)
    fade_out_s = int(sr * 2.5)
    for i in range(min(fade_in_s, total_samples)):
        buf[i] *= i / fade_in_s
    for i in range(min(fade_out_s, total_samples)):
        buf[total_samples - 1 - i] *= i / fade_out_s

    peak = max(abs(s) for s in buf) or 1.0
    sc = 0.85 / peak
    raw = b"".join(struct.pack("<h", max(-32767, min(32767, int(s * sc * 32767)))) for s in buf)

    with open(path, "wb") as f:
        ds = len(raw)
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + ds))
        f.write(b"WAVEfmt ")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<HH", 1, 1))
        f.write(struct.pack("<I", sr))
        f.write(struct.pack("<I", sr * 2))
        f.write(struct.pack("<HH", 2, 16))
        f.write(b"data")
        f.write(struct.pack("<I", ds))
        f.write(raw)


# ── メイン ──────────────────────────────────────

def generate_video():
    os.makedirs(FRAMES_DIR, exist_ok=True)

    # 1. 画像をダウンロード
    print("📷 画像をダウンロード中...")
    images = {"exterior": download_image(IMG_EXTERIOR)}
    course_images = []
    for i, c in enumerate(COURSE):
        print(f"  Course {i+1}/{len(COURSE)}: {c['name']}")
        course_images.append(download_image(c["image"]))

    # Ken Burnsエフェクトのパターン（コースごとに交互）
    kb_effects = ["zoom_in", "zoom_out", "pan_right", "pan_left",
                  "zoom_in", "zoom_out", "pan_right", "zoom_in", "zoom_out"]

    # 2. フレーム生成
    print(f"\n🎬 フレーム生成中 ({FPS}fps, ギャラリーモード)...")
    all_frames = []
    total_scenes = len(SCENES)
    crossfade_frames_count = 8  # クロスフェード: 8フレーム（0.33秒）

    prev_last_frame = None

    for si, scene in enumerate(SCENES):
        duration = scene["duration"]
        n_frames = int(duration * FPS)
        scene_type = scene["type"]
        scene_frames = []

        for fi in range(n_frames):
            if scene_type == "opening":
                frame = render_opening(fi, n_frames, images)
            elif scene_type == "course":
                ci = scene["course_idx"]
                frame = render_course(fi, n_frames, COURSE[ci],
                                      course_images[ci], kb_effects[ci])
            elif scene_type == "text_card":
                frame = render_text_card(fi, n_frames)
            elif scene_type == "cta":
                frame = render_cta(fi, n_frames, images["exterior"])
            else:
                frame = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)

            # シネマティック処理（コースと外観シーンのみ画像ありとして扱う）
            global_idx = len(all_frames) + fi
            frame = apply_cinematic(frame, global_idx)

            scene_frames.append(frame)

        # クロスフェードトランジション
        if si > 0 and prev_last_frame is not None and len(scene_frames) > 0:
            cf_count = min(crossfade_frames_count, len(scene_frames))
            trans = []
            for ci in range(cf_count):
                blend_t = ease_in_out((ci + 1) / cf_count)
                blended = Image.blend(prev_last_frame, scene_frames[ci], blend_t)
                trans.append(blended)
            # トランジション分を差し替え
            all_frames.extend(trans)
            all_frames.extend(scene_frames[cf_count:])
        else:
            all_frames.extend(scene_frames)

        prev_last_frame = scene_frames[-1] if scene_frames else None
        print(f"  Scene {si+1}/{total_scenes} ({scene_type}) done ({n_frames} frames)")

    # 3. フレーム保存
    print(f"\n💾 {len(all_frames)} フレームを保存中...")
    for i, frame in enumerate(all_frames):
        frame.save(os.path.join(FRAMES_DIR, f"frame_{i:04d}.png"), "PNG")

    # 4. GIF
    print("\n🎞️  GIFアニメーション生成中...")
    gif_path = os.path.join(OUTPUT_DIR, "reels_video.gif")
    gif_w, gif_h = 270, 480
    gif_frames = [f.resize((gif_w, gif_h), Image.LANCZOS).quantize(
        colors=128, method=Image.Quantize.MEDIANCUT) for f in all_frames]
    gif_frames[0].save(
        gif_path, save_all=True, append_images=gif_frames[1:],
        duration=int(1000 / FPS), loop=0, optimize=True,
    )
    gif_size = os.path.getsize(gif_path) / (1024 * 1024)
    print(f"  → {gif_path} ({gif_size:.1f} MB)")

    # 5. WebP
    print("\n🎞️  WebPアニメーション生成中...")
    webp_path = os.path.join(OUTPUT_DIR, "reels_video.webp")
    webp_frames = [f.resize((gif_w, gif_h), Image.LANCZOS) for f in all_frames]
    webp_frames[0].save(
        webp_path, save_all=True, append_images=webp_frames[1:],
        duration=int(1000 / FPS), loop=0, quality=70, method=4,
    )
    webp_size = os.path.getsize(webp_path) / (1024 * 1024)
    print(f"  → {webp_path} ({webp_size:.1f} MB)")

    # 6. MP4
    total_duration = len(all_frames) / FPS
    mp4_path = os.path.join(OUTPUT_DIR, "reels_video.mp4")
    if shutil.which("ffmpeg"):
        print("\n🎬 MP4動画生成中...")
        mp4_silent = os.path.join(OUTPUT_DIR, "reels_video_silent.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", os.path.join(FRAMES_DIR, "frame_%04d.png"),
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={WIDTH}:{HEIGHT}",
            mp4_silent,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ⚠️  MP4生成に失敗: {result.stderr[-200:]}")
            mp4_path = None
        else:
            bgm_source = None
            if os.path.exists(BGM_FILE):
                bgm_source = BGM_FILE
                print(f"\n🎵 カスタムBGM: {BGM_FILE}")
            else:
                print("\n🎵 BGM生成中...")
                bgm_source = os.path.join(OUTPUT_DIR, "bgm.wav")
                generate_bgm_wav(bgm_source, total_duration)

            bgm_size = os.path.getsize(bgm_source) / 1024
            print(f"  → {bgm_source} ({bgm_size:.0f} KB)")

            print("\n🎬 映像とBGMを合成中...")
            fade_out_sec = 2.0
            audio_filter = (
                f"aloop=loop=-1:size=2e+09,"
                f"atrim=duration={total_duration},"
                f"afade=t=out:st={total_duration - fade_out_sec}:d={fade_out_sec}"
            )
            cmd_merge = [
                "ffmpeg", "-y",
                "-i", mp4_silent,
                "-stream_loop", "-1", "-i", bgm_source,
                "-c:v", "copy",
                "-af", audio_filter,
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                mp4_path,
            ]
            result2 = subprocess.run(cmd_merge, capture_output=True, text=True)
            if result2.returncode == 0:
                mp4_size = os.path.getsize(mp4_path) / (1024 * 1024)
                print(f"  → {mp4_path} ({mp4_size:.1f} MB) ♪ BGM付き")
                os.remove(mp4_silent)
                tmp_bgm = os.path.join(OUTPUT_DIR, "bgm.wav")
                if os.path.exists(tmp_bgm):
                    os.remove(tmp_bgm)
            else:
                print(f"  ⚠️  BGM合成失敗。無音版を使用: {result2.stderr[-200:]}")
                os.rename(mp4_silent, mp4_path)
                mp4_size = os.path.getsize(mp4_path) / (1024 * 1024)
                print(f"  → {mp4_path} ({mp4_size:.1f} MB)")
    else:
        print("\n⚠️  ffmpegが見つかりません。MP4生成をスキップ。")
        mp4_path = None

    print(f"\n✅ 完了！")
    print(f"   フレーム数: {len(all_frames)}")
    print(f"   合計秒数:   {total_duration:.1f}秒")
    print(f"\n📁 出力ファイル:")
    if mp4_path:
        print(f"   {mp4_path}   ← Instagramにそのまま投稿可能（BGM付き♪）")
    print(f"   {gif_path}")
    print(f"   {webp_path}")
    print(f"   {FRAMES_DIR}/")


if __name__ == "__main__":
    generate_video()
