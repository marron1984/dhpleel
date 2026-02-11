#!/usr/bin/env python3
"""
北新地 大嵓埜 — Instagram Reels 動画生成スクリプト（2026 最先端シネマティック版）

最新Reelsトレンド × 高級感:
  - シネマティック映像演出（フィルムグレイン・カラーグレーディング・ビネット）
  - ボケパーティクル（浮遊光の粒子）
  - ブラーフラッシュトランジション
  - 1文字ずつリビールアニメーション
  - ゴールドライン装飾アニメーション
  - 集客フック → ブランドリビール → ショーケース → CTA

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
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── 設定 ──────────────────────────────────────────
WIDTH = 540                # 9:16 Reels解像度
HEIGHT = 960
FPS = 24                   # なめらかなフレームレート
BG_COLOR = (10, 10, 10)
GOLD = (196, 162, 101)
GOLD_LIGHT = (232, 213, 168)
GOLD_DIM = (140, 115, 70)
WHITE = (255, 255, 255)
WARM_WHITE = (255, 248, 238)

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

# ── シーン定義（2026 シネマティック・集客特化版）──────────────
# transition: "blur_flash" = ブラー→白フラッシュ, "cut" = ハードカット
# anim: "bounce" = ポップイン, "slide_up" = 下からスライド,
#        "fade" = 通常フェード, "char_reveal" = 1文字ずつリビール
SCENES = [
    # ━━ PHASE 1: ラピッドモンタージュ（0-2秒）━━━━━━━━━━━
    # テキストなし、高速4連射 → スクロール停止率MAX
    {   "image": IMG_SASHIMI,  "duration": 0.5, "effect": "zoom_in",
        "texts": [], "transition": "cut" },
    {   "image": IMG_DESSERT,  "duration": 0.5, "effect": "zoom_out",
        "texts": [], "transition": "cut" },
    {   "image": IMG_SHIIZAKA, "duration": 0.5, "effect": "pan_right",
        "texts": [], "transition": "cut" },
    {   "image": IMG_AGEMONO,  "duration": 0.5, "effect": "zoom_in",
        "texts": [], "transition": "cut" },

    # ━━ PHASE 2: 店名リビール（2-5秒）━━━━━━━━━━━━━━
    {   # 5. テキストフック（黒背景）
        "image": None, "duration": 1.8, "effect": "none",
        "texts": [
            {"text": "北新地の隠れ家で", "y": 0.36, "size": 26, "color": WARM_WHITE, "font": "body", "anim": "char_reveal"},
            {"text": "至福の一夜を", "y": 0.46, "size": 48, "color": GOLD, "spacing": 10, "font": "title", "anim": "char_reveal"},
        ],
        "gold_line": {"y": 0.42, "delay": 0.3},
        "text_delay": 0.0, "transition": "blur_flash",
    },
    {   # 6. ミシュラン + 店名
        "image": IMG_EXTERIOR, "duration": 2.0, "effect": "zoom_in",
        "texts": [
            {"text": "MICHELIN SELECTED", "y": 0.33, "size": 20, "color": GOLD, "spacing": 6, "font": "accent", "anim": "fade"},
            {"text": "大嵓埜", "y": 0.44, "size": 56, "color": WHITE, "spacing": 16, "font": "title", "anim": "char_reveal"},
        ],
        "gold_line": {"y": 0.39, "delay": 0.2},
        "text_delay": 0.1, "transition": "blur_flash",
    },

    # ━━ PHASE 3: 料理ショーケース（5-10.5秒）━━━━━━━━━━━━
    {   "image": IMG_SAKIZUKE, "duration": 1.0, "effect": "zoom_out",
        "texts": [
            {"text": "先付け", "y": 0.76, "size": 44, "color": WHITE, "spacing": 10, "align": "left", "font": "title", "anim": "slide_up"},
        ],
        "text_delay": 0.0, "transition": "blur_flash",
    },
    {   "image": IMG_YAKIMONO, "duration": 1.0, "effect": "pan_left",
        "texts": [
            {"text": "焼き物", "y": 0.76, "size": 44, "color": WHITE, "spacing": 10, "align": "left", "font": "title", "anim": "slide_up"},
        ],
        "text_delay": 0.0, "transition": "blur_flash",
    },
    {   "image": IMG_NIMONO, "duration": 1.0, "effect": "zoom_in",
        "texts": [
            {"text": "煮  物", "y": 0.76, "size": 44, "color": WHITE, "spacing": 10, "align": "left", "font": "title", "anim": "slide_up"},
        ],
        "text_delay": 0.0, "transition": "blur_flash",
    },
    {   "image": IMG_OWAN, "duration": 1.0, "effect": "zoom_tilt",
        "texts": [
            {"text": "清  湯", "y": 0.76, "size": 44, "color": WHITE, "spacing": 10, "align": "left", "font": "title", "anim": "slide_up"},
        ],
        "text_delay": 0.0, "transition": "blur_flash",
    },
    {   "image": IMG_GOHAN, "duration": 1.0, "effect": "pan_right",
        "texts": [
            {"text": "ご  飯", "y": 0.76, "size": 44, "color": WHITE, "spacing": 10, "align": "left", "font": "title", "anim": "slide_up"},
        ],
        "text_delay": 0.0, "transition": "blur_flash",
    },

    # ━━ PHASE 4: 価格 + 緊急性（10.5-14.5秒）━━━━━━━━━━━━
    {   # 12. 価格アンカー
        "image": IMG_EXTERIOR, "duration": 2.2, "effect": "zoom_in",
        "texts": [
            {"text": "全11品の特別懐石", "y": 0.34, "size": 24, "color": WARM_WHITE, "font": "body", "anim": "slide_up"},
            {"text": "¥30,000〜", "y": 0.43, "size": 60, "color": GOLD, "spacing": 6, "font": "title", "anim": "bounce"},
        ],
        "gold_line": {"y": 0.39, "delay": 0.15},
        "text_delay": 0.1, "transition": "blur_flash",
    },
    {   # 13. 緊急性
        "image": IMG_EXTERIOR, "duration": 1.8, "effect": "zoom_in",
        "texts": [
            {"text": "完全予約制", "y": 0.38, "size": 40, "color": WHITE, "spacing": 10, "font": "title", "anim": "char_reveal"},
            {"text": "席数限定", "y": 0.48, "size": 36, "color": GOLD, "spacing": 8, "font": "title", "anim": "char_reveal"},
        ],
        "text_delay": 0.15, "transition": "blur_flash",
    },

    # ━━ PHASE 5: CTA（14.5-18.5秒）━━━━━━━━━━━━━━━━━
    {   # 14. 予約誘導
        "image": IMG_EXTERIOR, "duration": 3.5, "effect": "zoom_in",
        "texts": [
            {"text": "ご予約・お問い合わせ", "y": 0.26, "size": 20, "color": (200, 200, 200), "font": "body", "anim": "fade"},
            {"text": "06-6341-3535", "y": 0.34, "size": 48, "color": GOLD, "spacing": 6, "font": "accent", "anim": "bounce"},
            {"text": "大嵓埜", "y": 0.50, "size": 48, "color": WHITE, "spacing": 14, "font": "title", "anim": "char_reveal"},
            {"text": "北新地 FOODEAR ビル 3F", "y": 0.59, "size": 16, "color": (180, 180, 180), "font": "body"},
            {"text": "DMまたはお電話で予約", "y": 0.68, "size": 26, "color": GOLD, "spacing": 3, "font": "body", "anim": "bounce"},
            {"text": "▶ プロフィールのリンクから", "y": 0.74, "size": 20, "color": GOLD_LIGHT, "font": "body", "anim": "slide_up"},
        ],
        "gold_line": {"y": 0.44, "delay": 0.25},
        "text_delay": 0.12, "transition": "blur_flash",
    },
]


# ── ヘルパー関数 ──────────────────────────────────

def download_image(url, cache_dir="output/.cache"):
    """画像をダウンロードしてPIL Imageとして返す（キャッシュ付き）"""
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
    """画像をcoverモードでリサイズ＆クロップ"""
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def ease_in_out(t):
    """スムーズなイージング"""
    return t * t * (3.0 - 2.0 * t)


def ease_out_back(t):
    """バウンス風イージング（オーバーシュート→戻る）"""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


def ease_out_cubic(t):
    """滑らかな減速イージング"""
    return 1 - pow(1 - t, 3)


# ── シネマティック映像エフェクト（高速LUT版）──────────────

# カラーグレーディング用LUT（起動時に1回だけ計算）
_COLOR_LUT_R = None
_COLOR_LUT_G = None
_COLOR_LUT_B = None
_VIGNETTE_MASK = None


def _build_color_luts():
    """カラーグレーディングLUTをビルド（各チャンネル256値のマッピング）"""
    global _COLOR_LUT_R, _COLOR_LUT_G, _COLOR_LUT_B

    def make_lut(shadow_shift, highlight_shift, gamma):
        lut = []
        for i in range(256):
            v = i / 255.0
            v = pow(v, gamma)
            if v < 0.5:
                v += shadow_shift * (0.5 - v) * 0.15
            else:
                v += highlight_shift * (v - 0.5) * 0.08
            lut.append(max(0, min(255, int(v * 255))))
        return lut

    _COLOR_LUT_R = make_lut(shadow_shift=0.6, highlight_shift=0.1, gamma=0.97)
    _COLOR_LUT_G = make_lut(shadow_shift=0.2, highlight_shift=0.0, gamma=1.0)
    _COLOR_LUT_B = make_lut(shadow_shift=-0.3, highlight_shift=-0.1, gamma=1.03)


def _build_vignette_mask(w, h):
    """ビネットマスクを1回だけ生成"""
    global _VIGNETTE_MASK
    mask = Image.new("L", (w, h))
    pixels = mask.load()
    cx, cy = w / 2.0, h / 2.0
    max_dist = math.sqrt(cx * cx + cy * cy)

    for y in range(h):
        for x in range(w):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            ratio = dist / max_dist
            if ratio < 0.4:
                v = 0
            else:
                falloff = (ratio - 0.4) / 0.6
                v = int(255 * falloff * falloff * 0.50)
            pixels[x, y] = min(255, v)

    _VIGNETTE_MASK = mask


def apply_film_grain(frame, intensity=10, seed=None):
    """フィルムグレインテクスチャ（高速版：小さいノイズをリサイズ）"""
    rng = random.Random(seed)
    # 小さいサイズでノイズ生成 → リサイズで高速化
    sw, sh = 135, 240  # 1/4サイズ
    grain_data = bytes(max(0, min(255, int(rng.gauss(128, intensity)))) for _ in range(sw * sh))
    grain_small = Image.frombytes("L", (sw, sh), grain_data)
    grain = grain_small.resize(frame.size, Image.BILINEAR)
    grain_rgb = Image.merge("RGB", [grain, grain, grain])
    return Image.blend(frame, grain_rgb, 0.05)


def apply_color_grade(frame):
    """シネマティックカラーグレーディング（LUT版・高速）"""
    if _COLOR_LUT_R is None:
        _build_color_luts()

    r, g, b = frame.split()
    r = r.point(_COLOR_LUT_R)
    g = g.point(_COLOR_LUT_G)
    b = b.point(_COLOR_LUT_B)
    graded = Image.merge("RGB", [r, g, b])
    # 彩度をわずかに落とす（高級感）
    gray = graded.convert("L").convert("RGB")
    return Image.blend(graded, gray, 0.08)


def apply_vignette(frame):
    """ビネットエフェクト（プリコンピュート済みマスク版・高速）"""
    w, h = frame.size
    if _VIGNETTE_MASK is None or _VIGNETTE_MASK.size != (w, h):
        _build_vignette_mask(w, h)

    black = Image.new("RGB", (w, h), (0, 0, 0))
    # マスク値が高い=暗い（ビネット）、低い=元画像
    return Image.composite(black, frame, _VIGNETTE_MASK)


def generate_bokeh_particles(count=8, seed=42):
    """ボケパーティクルの基本パラメータを事前生成"""
    rng = random.Random(seed)
    particles = []
    for _ in range(count):
        particles.append({
            "base_x": rng.uniform(0, WIDTH),
            "base_y": rng.uniform(0, HEIGHT),
            "radius": rng.uniform(10, 40),
            "speed_x": rng.uniform(-0.3, 0.3),
            "speed_y": rng.uniform(-0.6, -0.15),
            "phase": rng.uniform(0, math.pi * 2),
        })
    return particles


# パーティクル事前生成
_BOKEH_PARTICLES = generate_bokeh_particles()


def generate_bokeh_overlay(w, h, time_offset=0.0):
    """ボケパーティクルオーバーレイ（浮遊する光の粒子）"""
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for p in _BOKEH_PARTICLES:
        x = p["base_x"] + p["speed_x"] * time_offset * 60 + math.sin(p["phase"] + time_offset * 1.5) * 15
        y = p["base_y"] + p["speed_y"] * time_offset * 60
        x = x % w
        y = y % h

        brightness = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(p["phase"] + time_offset * 2.5))
        base_alpha = int(28 * brightness)
        radius = p["radius"]

        for r_step in range(int(radius), 0, -3):
            ratio = r_step / radius
            step_alpha = int(base_alpha * (1 - ratio * ratio))
            if step_alpha > 0:
                draw.ellipse([x - r_step, y - r_step, x + r_step, y + r_step],
                             fill=(220, 200, 160, step_alpha))

    return overlay


def apply_cinematic_pipeline(frame, frame_idx, has_image=True):
    """シネマティック映像パイプライン（グレイン + カラグレ + ビネット + ボケ）"""
    if has_image:
        frame = apply_color_grade(frame)
        frame = apply_vignette(frame)

    frame = apply_film_grain(frame, intensity=10, seed=frame_idx)

    bokeh = generate_bokeh_overlay(WIDTH, HEIGHT, time_offset=frame_idx / FPS)
    frame_rgba = frame.convert("RGBA")
    frame = Image.alpha_composite(frame_rgba, bokeh).convert("RGB")

    return frame


# ── Ken Burns ──────────────────────────────────

def apply_ken_burns(img, effect, progress, canvas_w, canvas_h):
    """Ken Burnsエフェクトを適用"""
    if img is None:
        return Image.new("RGB", (canvas_w, canvas_h), BG_COLOR)

    pad = 1.25
    base = fit_cover(img, int(canvas_w * pad), int(canvas_h * pad))
    bw, bh = base.size
    t = ease_in_out(progress)

    if effect == "zoom_in":
        scale = 1.0 + 0.12 * t
        cx, cy = bw / 2, bh / 2
    elif effect == "zoom_out":
        scale = 1.12 - 0.12 * t
        cx, cy = bw / 2, bh / 2
    elif effect == "pan_right":
        scale = 1.08
        cx = bw / 2 + (bw * 0.04) * (2 * t - 1)
        cy = bh / 2
    elif effect == "pan_left":
        scale = 1.08
        cx = bw / 2 - (bw * 0.04) * (2 * t - 1)
        cy = bh / 2
    elif effect == "zoom_tilt":
        scale = 1.0 + 0.08 * t
        cx = bw / 2 + math.sin(t * 0.5) * 5
        cy = bh / 2
    elif effect == "none":
        return Image.new("RGB", (canvas_w, canvas_h), BG_COLOR)
    else:
        scale = 1.0
        cx, cy = bw / 2, bh / 2

    crop_w = canvas_w / scale
    crop_h = canvas_h / scale
    left = max(0, cx - crop_w / 2)
    top = max(0, cy - crop_h / 2)
    right = min(bw, left + crop_w)
    bottom = min(bh, top + crop_h)

    if right - left < crop_w:
        left = max(0, right - crop_w)
    if bottom - top < crop_h:
        top = max(0, bottom - crop_h)

    cropped = base.crop((int(left), int(top), int(right), int(bottom)))
    return cropped.resize((canvas_w, canvas_h), Image.LANCZOS)


# ── グラデーション & トランジション ──────────────────

def draw_gradient_overlay(frame):
    """上下に暗いグラデーションオーバーレイ"""
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 上部グラデ
    for y in range(int(HEIGHT * 0.15)):
        alpha = int(60 * (1 - y / (HEIGHT * 0.15)))
        draw.rectangle([(0, y), (WIDTH, y + 1)], fill=(0, 0, 0, alpha))

    # 下部グラデ
    start_y = int(HEIGHT * 0.55)
    for y in range(start_y, HEIGHT):
        progress = (y - start_y) / (HEIGHT - start_y)
        alpha = int(200 * progress)
        draw.rectangle([(0, y), (WIDTH, y + 1)], fill=(0, 0, 0, alpha))

    frame_rgba = frame.convert("RGBA")
    return Image.alpha_composite(frame_rgba, overlay).convert("RGB")


def make_blur_flash_transition(prev_frame, next_frame, n_frames):
    """ブラーフラッシュトランジション（ブラー→白→次のシーン）"""
    frames = []
    mid = n_frames // 2

    for i in range(n_frames):
        if i <= mid:
            # 前半: 前のシーンがブラーして白に飛ぶ
            t = i / max(1, mid)
            blur_radius = int(t * 12)
            blurred = prev_frame.filter(ImageFilter.GaussianBlur(radius=max(1, blur_radius)))
            brightness = int(255 * ease_in_out(t) * 0.85)
            white = Image.new("RGB", (WIDTH, HEIGHT), (brightness, brightness, brightness))
            frame = Image.blend(blurred, white, ease_in_out(t) * 0.8)
        else:
            # 後半: 白から次のシーンに溶ける
            t = (i - mid) / max(1, n_frames - mid - 1)
            brightness = int(255 * (1 - ease_in_out(t)) * 0.7)
            white = Image.new("RGB", (WIDTH, HEIGHT), (brightness, brightness, brightness))
            frame = Image.blend(white, next_frame, ease_in_out(t))

        frames.append(frame)
    return frames


# ── テキスト描画 ──────────────────────────────────

def get_font(size, style="title"):
    """フォント取得"""
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

    if style in ("title", "accent"):
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


def draw_char_reveal(draw, text, x, y, font, color, alpha, progress, spacing=0):
    """1文字ずつリビールアニメーション"""
    chars = list(text)
    n = len(chars)
    if n == 0:
        return

    current_x = x
    for ci, ch in enumerate(chars):
        # 各文字の出現タイミング（均等に分散）
        char_start = ci / n * 0.7  # 全体の70%の時間で全文字開始
        char_end = char_start + 0.3
        if progress < char_start:
            char_alpha = 0
            char_offset_y = 12
        elif progress >= char_end:
            char_alpha = alpha
            char_offset_y = 0
        else:
            t = (progress - char_start) / (char_end - char_start)
            t = ease_out_cubic(t)
            char_alpha = int(alpha * t)
            char_offset_y = int(12 * (1 - t))

        if char_alpha > 0:
            fill = (*color, char_alpha)
            shadow_a = int(min(160, char_alpha * 0.7))

            # 影
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if abs(dx) + abs(dy) > 3:
                        continue
                    if dx == 0 and dy == 0:
                        continue
                    draw.text((current_x + dx, y + char_offset_y + dy), ch,
                              font=font, fill=(0, 0, 0, shadow_a))

            draw.text((current_x, y + char_offset_y), ch, font=font, fill=fill)

        # 文字幅を取得して次の位置へ
        bbox = draw.textbbox((0, 0), ch, font=font)
        char_w = bbox[2] - bbox[0]
        current_x += char_w + spacing


def draw_gold_line(draw, y, progress, delay=0.0):
    """ゴールドライン装飾アニメーション（中央から左右に伸びる）"""
    if progress <= delay:
        return
    t = min(1.0, (progress - delay) / 0.5)
    t = ease_out_cubic(t)

    max_half_width = 80
    half_w = int(max_half_width * t)
    cx = WIDTH // 2
    line_y = int(HEIGHT * y)
    alpha = int(180 * min(1.0, t * 1.5))

    if half_w > 0 and alpha > 0:
        # メインライン
        draw.rectangle([(cx - half_w, line_y), (cx + half_w, line_y + 1)],
                        fill=(*GOLD, alpha))
        # 端の装飾ドット
        if t > 0.5:
            dot_alpha = int(alpha * min(1.0, (t - 0.5) * 4))
            for dx in [-half_w - 4, half_w + 4]:
                draw.ellipse([(cx + dx - 1, line_y - 1), (cx + dx + 1, line_y + 1)],
                             fill=(*GOLD_LIGHT, dot_alpha))


def draw_text_overlay(frame, texts, text_progress, scene_progress=0.0, gold_line_config=None):
    """テキストオーバーレイ描画（リビール・バウンス・スライド対応）"""
    frame_rgba = frame.convert("RGBA")
    txt_layer = Image.new("RGBA", frame_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_layer)

    # ゴールドライン
    if gold_line_config:
        draw_gold_line(draw, gold_line_config["y"], scene_progress,
                       gold_line_config.get("delay", 0.0))

    for i, t in enumerate(texts):
        if i >= len(text_progress) or text_progress[i] <= 0:
            continue

        tp = min(1.0, text_progress[i])
        anim = t.get("anim", "fade")
        base_size = t["size"]
        font_style = t.get("font", "title")
        text_str = t["text"]
        color = t["color"]
        align = t.get("align", "center")
        spacing = t.get("spacing", 0)

        if anim == "char_reveal":
            # 1文字ずつリビール
            font = get_font(base_size, font_style)
            alpha = int(255 * min(1.0, tp * 2.0))
            y_pos = int(HEIGHT * t["y"])

            # テキスト全体幅を計算して中央揃え
            bbox = draw.textbbox((0, 0), text_str, font=font)
            tw = bbox[2] - bbox[0]
            if align == "center":
                x_pos = (WIDTH - tw - spacing * (len(text_str) - 1)) // 2
            else:
                x_pos = 36

            draw_char_reveal(draw, text_str, x_pos, y_pos, font, color,
                             alpha, tp, spacing)

        elif anim == "bounce":
            anim_t = ease_out_back(min(1.0, tp * 1.2))
            text_scale = 1.0 + 0.20 * (1 - anim_t)
            alpha = int(255 * min(1.0, tp * 2.5))
            y_offset = int(-6 * (1 - anim_t))

            actual_size = max(8, int(base_size * text_scale))
            font = get_font(actual_size, font_style)
            y_pos = int(HEIGHT * t["y"]) + y_offset
            bbox = draw.textbbox((0, 0), text_str, font=font)
            tw = bbox[2] - bbox[0]
            x_pos = (WIDTH - tw) // 2 if align == "center" else 36

            fill_a = (*color, alpha)
            shadow_a = int(160 * min(1.0, tp * 2.0))
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if abs(dx) + abs(dy) > 3 or (dx == 0 and dy == 0):
                        continue
                    draw.text((x_pos + dx, y_pos + dy), text_str, font=font,
                              fill=(0, 0, 0, shadow_a))
            draw.text((x_pos, y_pos), text_str, font=font, fill=fill_a)

        elif anim == "slide_up":
            anim_t = ease_in_out(tp)
            alpha = int(255 * min(1.0, tp * 2.0))
            y_offset = int(25 * (1 - anim_t))

            font = get_font(base_size, font_style)
            y_pos = int(HEIGHT * t["y"]) + y_offset
            bbox = draw.textbbox((0, 0), text_str, font=font)
            tw = bbox[2] - bbox[0]
            x_pos = (WIDTH - tw) // 2 if align == "center" else 36

            fill_a = (*color, alpha)
            shadow_a = int(160 * min(1.0, tp * 2.0))
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if abs(dx) + abs(dy) > 3 or (dx == 0 and dy == 0):
                        continue
                    draw.text((x_pos + dx, y_pos + dy), text_str, font=font,
                              fill=(0, 0, 0, shadow_a))
            draw.text((x_pos, y_pos), text_str, font=font, fill=fill_a)

        else:
            # 通常フェード
            anim_t = ease_in_out(tp)
            alpha = int(255 * tp)
            y_offset = int(6 * (1 - anim_t))

            font = get_font(base_size, font_style)
            y_pos = int(HEIGHT * t["y"]) + y_offset
            bbox = draw.textbbox((0, 0), text_str, font=font)
            tw = bbox[2] - bbox[0]
            x_pos = (WIDTH - tw) // 2 if align == "center" else 36

            fill_a = (*color, alpha)
            shadow_a = int(160 * min(1.0, tp * 2.0))
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if abs(dx) + abs(dy) > 3 or (dx == 0 and dy == 0):
                        continue
                    draw.text((x_pos + dx, y_pos + dy), text_str, font=font,
                              fill=(0, 0, 0, shadow_a))
            draw.text((x_pos, y_pos), text_str, font=font, fill=fill_a)

    return Image.alpha_composite(frame_rgba, txt_layer).convert("RGB")


def draw_progress_bar(frame, scene_idx, total_scenes, scene_progress):
    """上部のInstagram風プログレスバー"""
    frame_rgba = frame.convert("RGBA")
    draw = ImageDraw.Draw(frame_rgba)

    bar_y = 20
    bar_h = 2
    margin = 12
    gap = 4
    total_w = WIDTH - margin * 2
    seg_w = (total_w - gap * (total_scenes - 1)) / total_scenes

    for i in range(total_scenes):
        x = margin + i * (seg_w + gap)
        draw.rectangle([(x, bar_y), (x + seg_w, bar_y + bar_h)], fill=(255, 255, 255, 40))
        if i < scene_idx:
            fill_w = seg_w
        elif i == scene_idx:
            fill_w = seg_w * scene_progress
        else:
            fill_w = 0

        if fill_w > 0:
            draw.rectangle([(x, bar_y), (x + fill_w, bar_y + bar_h)],
                           fill=(255, 255, 255, 180))

    return frame_rgba.convert("RGB")


def crossfade_frames(frame_a, frame_b, t):
    """2フレーム間のクロスフェード"""
    return Image.blend(frame_a, frame_b, t)


# ── BGM生成（フォールバック）──────────────────────────

def generate_bgm_wav(path, duration_sec):
    """合成BGMフォールバック"""
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
            fade_in = min(1.0, t / 2.0)
            fade_out = min(1.0, (dur - t) / 2.0)
            env = fade_in * fade_out * volume
            val = (math.sin(2 * math.pi * freq * t) * 0.5 +
                   math.sin(2 * math.pi * freq * 1.002 * t) * 0.5)
            samples.append(val * env)
        return samples

    buf = [0.0] * total_samples
    pad_d = pad_tone(146.83, duration_sec, 0.06)
    pad_a = pad_tone(220.00, duration_sec, 0.04)
    for i in range(min(len(pad_d), total_samples)):
        buf[i] += pad_d[i] + pad_a[i]

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

    fade_in_samples = int(sr * 1.5)
    fade_out_samples = int(sr * 2.5)
    for i in range(min(fade_in_samples, total_samples)):
        buf[i] *= i / fade_in_samples
    for i in range(min(fade_out_samples, total_samples)):
        buf[total_samples - 1 - i] *= i / fade_out_samples

    peak = max(abs(s) for s in buf) or 1.0
    scale = 0.85 / peak
    raw = b"".join(struct.pack("<h", max(-32767, min(32767, int(s * scale * 32767)))) for s in buf)

    with open(path, "wb") as f:
        data_size = len(raw)
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<H", 1))
        f.write(struct.pack("<H", 1))
        f.write(struct.pack("<I", sr))
        f.write(struct.pack("<I", sr * 2))
        f.write(struct.pack("<H", 2))
        f.write(struct.pack("<H", 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(raw)


# ── メイン生成ロジック ──────────────────────────────

def generate_video():
    os.makedirs(FRAMES_DIR, exist_ok=True)

    # 1. 画像をダウンロード（Noneの場合はスキップ）
    print("📷 画像をダウンロード中...")
    images = []
    for i, scene in enumerate(SCENES):
        print(f"  Scene {i+1}/{len(SCENES)}")
        if scene["image"] is None:
            images.append(None)
        else:
            img = download_image(scene["image"])
            images.append(img)

    # 2. フレームを生成
    print(f"\n🎬 フレーム生成中 ({FPS}fps, シネマティック処理付き)...")
    all_frames = []
    total_scenes = len(SCENES)
    transition_frames = 4  # ブラーフラッシュ: 4フレーム

    # 各シーンの最終フレームを保持（トランジション用）
    prev_last_frame = None

    for si, scene in enumerate(SCENES):
        duration = scene["duration"]
        n_frames = int(duration * FPS)
        texts = scene["texts"]
        text_delay = scene.get("text_delay", 0.0)
        transition = scene.get("transition", "cut")
        gold_line_cfg = scene.get("gold_line", None)

        scene_frames = []

        for fi in range(n_frames):
            t = fi / max(1, n_frames - 1)
            time_s = fi / FPS

            # Ken Burns
            kb_frame = apply_ken_burns(images[si], scene["effect"], t, WIDTH, HEIGHT)

            has_image = scene["image"] is not None

            # グラデーションオーバーレイ（画像シーンのみ）
            if has_image:
                frame = draw_gradient_overlay(kb_frame)
            else:
                frame = kb_frame

            # テキスト進捗（クイック出現）
            text_prog = []
            for ti in range(len(texts)):
                delay = text_delay + ti * 0.18
                if time_s < delay:
                    text_prog.append(0.0)
                else:
                    raw = min(1.0, (time_s - delay) / 0.4)
                    text_prog.append(raw)

            scene_progress = time_s / max(0.01, duration)
            frame = draw_text_overlay(frame, texts, text_prog,
                                      scene_progress, gold_line_cfg)

            # プログレスバー
            frame = draw_progress_bar(frame, si, total_scenes, t)

            # シネマティック映像パイプライン
            global_frame_idx = len(all_frames) + fi
            frame = apply_cinematic_pipeline(frame, global_frame_idx, has_image)

            # シーン末尾フェードアウト（最後のシーンのみ）
            if si == total_scenes - 1:
                fade_out_start = 0.82
                if t > fade_out_start:
                    fade_t = (t - fade_out_start) / (1.0 - fade_out_start)
                    black = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
                    frame = crossfade_frames(frame, black, ease_in_out(fade_t))

            scene_frames.append(frame)

        # トランジション挿入
        if si > 0 and transition == "blur_flash" and prev_last_frame is not None:
            trans_frames = make_blur_flash_transition(
                prev_last_frame, scene_frames[0], transition_frames)
            all_frames.extend(trans_frames)
        elif si > 0 and transition == "cut":
            pass  # ハードカット — そのまま

        all_frames.extend(scene_frames)
        prev_last_frame = scene_frames[-1] if scene_frames else None
        print(f"  Scene {si+1}/{total_scenes} done ({n_frames} frames)")

    # 3. フレーム保存
    print(f"\n💾 {len(all_frames)} フレームを保存中...")
    for i, frame in enumerate(all_frames):
        frame.save(os.path.join(FRAMES_DIR, f"frame_{i:04d}.png"), "PNG")

    # 4. GIFアニメーション生成
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

    # 5. WebPアニメーション生成
    print("\n🎞️  WebPアニメーション生成中...")
    webp_path = os.path.join(OUTPUT_DIR, "reels_video.webp")
    webp_frames = [f.resize((gif_w, gif_h), Image.LANCZOS) for f in all_frames]
    webp_frames[0].save(
        webp_path, save_all=True, append_images=webp_frames[1:],
        duration=int(1000 / FPS), loop=0, quality=70, method=4,
    )
    webp_size = os.path.getsize(webp_path) / (1024 * 1024)
    print(f"  → {webp_path} ({webp_size:.1f} MB)")

    # 6. MP4動画生成
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
            # BGM準備
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

            # 映像 + BGM合成
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
        print("   macOS:  brew install ffmpeg")
        print("   Ubuntu: sudo apt install ffmpeg")
        mp4_path = None

    # 7. 完了サマリー
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
