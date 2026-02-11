#!/usr/bin/env python3
"""
北新地 大嵓埜 — Instagram Reels 動画生成スクリプト

PillowのみでReels動画（9:16）を生成します。
出力形式: 連番PNG → 最終的にGIFアニメーション or WebPアニメーション

使い方:
    python3 generate_reels_video.py

出力:
    output/reels_video.mp4   — MP4動画（メイン出力）
    output/reels_video.gif   — GIFアニメーション
    output/reels_video.webp  — WebPアニメーション（高品質）
    output/frames/           — 全フレーム連番PNG

必要なもの:
    pip3 install Pillow
    ffmpeg（MP4生成に必要。なくてもGIF/WebPは生成される）

    macOS:   brew install ffmpeg
    Ubuntu:  sudo apt install ffmpeg
"""

import os
import io
import math
import random
import shutil
import struct
import subprocess
import zlib
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── 設定 ──────────────────────────────────────────
WIDTH = 540                # 9:16 Reels解像度
HEIGHT = 960
FPS = 24                   # なめらかなフレームレート
BG_COLOR = (10, 10, 10)
GOLD = (196, 162, 101)
GOLD_LIGHT = (232, 213, 168)
WHITE = (255, 255, 255)

OUTPUT_DIR = "output"
FRAMES_DIR = os.path.join(OUTPUT_DIR, "frames")
BGM_FILE = "bgm.mp3"        # カスタムBGMファイル（プロジェクトルートに配置）

# ── シーン定義 ─────────────────────────────────────
SCENES = [
    {   # オープニング — 店名
        "image": "https://github.com/user-attachments/assets/6e9bb9c1-0ead-47de-b875-ac9dfde0c3b7",
        "duration": 3.2,
        "effect": "zoom_in",
        "texts": [
            {"text": "MICHELIN SELECTED", "y": 0.32, "size": 16, "color": GOLD, "spacing": 6, "font": "accent"},
            {"text": "━━━━", "y": 0.37, "size": 14, "color": GOLD},
            {"text": "北新地  大嵓埜", "y": 0.43, "size": 40, "color": WHITE, "spacing": 12, "font": "title"},
            {"text": "季節の恵みを味わう、特別なひととき", "y": 0.51, "size": 16, "color": GOLD_LIGHT, "spacing": 3, "font": "body"},
        ],
        "text_delay": 0.5,
    },
    {   # 先付け
        "image": "https://github.com/user-attachments/assets/b02cc12f-1be7-4498-835c-e002b4d5afa2",
        "duration": 2.5,
        "effect": "zoom_out",
        "texts": [
            {"text": "先付け", "y": 0.78, "size": 34, "color": WHITE, "spacing": 8, "align": "left", "font": "title"},
            {"text": "爽やかな季節野菜のハーモニー", "y": 0.85, "size": 14, "color": (220, 220, 220), "spacing": 2, "align": "left", "font": "body"},
        ],
        "text_delay": 0.4,
    },
    {   # 刺身
        "image": "https://github.com/user-attachments/assets/b3a7eefa-2fd5-4ce0-8830-d665a788b10d",
        "duration": 2.5,
        "effect": "pan_right",
        "texts": [
            {"text": "刺  身", "y": 0.78, "size": 34, "color": WHITE, "spacing": 8, "align": "left", "font": "title"},
            {"text": "海の恵みを華やかに", "y": 0.85, "size": 14, "color": (220, 220, 220), "spacing": 2, "align": "left", "font": "body"},
        ],
        "text_delay": 0.4,
    },
    {   # 焼き物
        "image": "https://github.com/user-attachments/assets/89d7a632-b7be-46f6-b301-5feb0b31991d",
        "duration": 2.5,
        "effect": "zoom_in",
        "texts": [
            {"text": "焼き物", "y": 0.78, "size": 34, "color": WHITE, "spacing": 8, "align": "left", "font": "title"},
            {"text": "香ばしい竹の子と帆立", "y": 0.85, "size": 14, "color": (220, 220, 220), "spacing": 2, "align": "left", "font": "body"},
        ],
        "text_delay": 0.4,
    },
    {   # 揚げ物
        "image": "https://github.com/user-attachments/assets/34173214-d90e-4556-b22f-75f53e756304",
        "duration": 2.3,
        "effect": "pan_left",
        "texts": [
            {"text": "揚げ物", "y": 0.78, "size": 34, "color": WHITE, "spacing": 8, "align": "left", "font": "title"},
            {"text": "サクサクの食感で心を掴む", "y": 0.85, "size": 14, "color": (220, 220, 220), "spacing": 2, "align": "left", "font": "body"},
        ],
        "text_delay": 0.4,
    },
    {   # 強肴
        "image": "https://github.com/user-attachments/assets/a990a366-4d57-4cdd-8766-0c5d794f5bfc",
        "duration": 2.3,
        "effect": "zoom_out",
        "texts": [
            {"text": "強  肴", "y": 0.78, "size": 34, "color": WHITE, "spacing": 8, "align": "left", "font": "title"},
            {"text": "手まり寿司の贅沢", "y": 0.85, "size": 14, "color": (220, 220, 220), "spacing": 2, "align": "left", "font": "body"},
        ],
        "text_delay": 0.4,
    },
    {   # ご飯
        "image": "https://github.com/user-attachments/assets/ee7a5a4a-885d-4f95-b83c-5ee014652a4c",
        "duration": 2.5,
        "effect": "zoom_tilt",
        "texts": [
            {"text": "ご  飯", "y": 0.78, "size": 34, "color": WHITE, "spacing": 8, "align": "left", "font": "title"},
            {"text": "えびと緑のハーモニー", "y": 0.85, "size": 14, "color": (220, 220, 220), "spacing": 2, "align": "left", "font": "body"},
        ],
        "text_delay": 0.4,
    },
    {   # デザート
        "image": "https://github.com/user-attachments/assets/b39bf119-c360-47df-b8b1-5399b4445ab1",
        "duration": 2.5,
        "effect": "zoom_in",
        "texts": [
            {"text": "デザート", "y": 0.78, "size": 34, "color": WHITE, "spacing": 8, "align": "left", "font": "title"},
            {"text": "苺・メロン・マンゴーの甘美", "y": 0.85, "size": 14, "color": (220, 220, 220), "spacing": 2, "align": "left", "font": "body"},
        ],
        "text_delay": 0.4,
    },
    {   # エンディング — 店舗情報
        "image": "https://github.com/user-attachments/assets/6e9bb9c1-0ead-47de-b875-ac9dfde0c3b7",
        "duration": 3.8,
        "effect": "zoom_in",
        "texts": [
            {"text": "接待・記念日に", "y": 0.30, "size": 18, "color": WHITE, "spacing": 4, "font": "body"},
            {"text": "━━━━", "y": 0.36, "size": 14, "color": GOLD},
            {"text": "大嵓埜", "y": 0.43, "size": 46, "color": WHITE, "spacing": 14, "font": "title"},
            {"text": "06-6341-3535", "y": 0.54, "size": 28, "color": GOLD, "spacing": 5, "font": "accent"},
            {"text": "北新地 FOODEAR ビル 3F", "y": 0.61, "size": 13, "color": (180, 180, 180), "spacing": 2, "font": "body"},
        ],
        "text_delay": 0.4,
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
    """スムーズなイージング（ゆっくり始まり、ゆっくり終わる）"""
    return t * t * (3.0 - 2.0 * t)


def apply_ken_burns(img, effect, progress, canvas_w, canvas_h):
    """Ken Burnsエフェクトを適用（progress: 0.0〜1.0）
    高級感のある微かなズーム/パン — ゆったりとした動き。
    """
    # 大きめに取って変形後にクロップ
    pad = 1.25  # 25%余分に確保
    base = fit_cover(img, int(canvas_w * pad), int(canvas_h * pad))
    bw, bh = base.size
    t = ease_in_out(progress)  # スムーズなイージング

    if effect == "zoom_in":
        scale = 1.0 + 0.09 * t
        cx, cy = bw / 2, bh / 2
    elif effect == "zoom_out":
        scale = 1.09 - 0.09 * t
        cx, cy = bw / 2, bh / 2
    elif effect == "pan_right":
        scale = 1.06
        cx = bw / 2 + (bw * 0.03) * (2 * t - 1)
        cy = bh / 2
    elif effect == "pan_left":
        scale = 1.06
        cx = bw / 2 - (bw * 0.03) * (2 * t - 1)
        cy = bh / 2
    elif effect == "zoom_tilt":
        scale = 1.0 + 0.06 * t
        cx = bw / 2 + math.sin(t * 0.3) * 4
        cy = bh / 2
    else:
        scale = 1.0
        cx, cy = bw / 2, bh / 2

    # クロップ範囲を計算
    crop_w = canvas_w / scale
    crop_h = canvas_h / scale
    left = max(0, cx - crop_w / 2)
    top = max(0, cy - crop_h / 2)
    right = min(bw, left + crop_w)
    bottom = min(bh, top + crop_h)

    # はみ出し補正
    if right - left < crop_w:
        left = max(0, right - crop_w)
    if bottom - top < crop_h:
        top = max(0, bottom - crop_h)

    cropped = base.crop((int(left), int(top), int(right), int(bottom)))
    return cropped.resize((canvas_w, canvas_h), Image.LANCZOS)


def draw_gradient_overlay(frame):
    """上下に暗いグラデーションオーバーレイ"""
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 上部グラデーション
    for y in range(int(HEIGHT * 0.2)):
        alpha = int(80 * (1 - y / (HEIGHT * 0.2)))
        draw.rectangle([(0, y), (WIDTH, y + 1)], fill=(0, 0, 0, alpha))

    # 下部グラデーション（より濃く）
    start_y = int(HEIGHT * 0.55)
    for y in range(start_y, HEIGHT):
        progress = (y - start_y) / (HEIGHT - start_y)
        alpha = int(180 * progress)
        draw.rectangle([(0, y), (WIDTH, y + 1)], fill=(0, 0, 0, alpha))

    frame_rgba = frame.convert("RGBA")
    return Image.alpha_composite(frame_rgba, overlay).convert("RGB")


def generate_bgm_wav(path, duration_sec):
    """ピアノ風アンビエントBGMをWAVとして生成（外部ライブラリ不要）

    日本料理店にふさわしい落ち着いた和風アンビエント。
    ペンタトニックスケールのピアノ風音色 + リバーブ + パッド。
    """
    sr = 44100
    total_samples = int(sr * duration_sec)

    # 和風ペンタトニック（D minor pentatonic ベース）
    # D4, F4, G4, A4, C5, D5, F5
    base_freqs = [293.66, 349.23, 392.00, 440.00, 523.25, 587.33, 698.46]

    rng = random.Random(42)  # 再現性のため固定シード

    def piano_tone(freq, dur, volume=0.3):
        """ピアノ風の減衰する正弦波（倍音付き）"""
        n = int(sr * dur)
        samples = []
        for i in range(n):
            t = i / sr
            env = math.exp(-t * 3.0) * volume  # 減衰エンベロープ
            # 基音 + 軽い倍音でピアノ風の音色
            val = (math.sin(2 * math.pi * freq * t) * 0.7 +
                   math.sin(2 * math.pi * freq * 2 * t) * 0.15 +
                   math.sin(2 * math.pi * freq * 3 * t) * 0.08 +
                   math.sin(2 * math.pi * freq * 5 * t) * 0.03)
            samples.append(val * env)
        return samples

    def pad_tone(freq, dur, volume=0.08):
        """持続するパッド音（背景の厚み）"""
        n = int(sr * dur)
        samples = []
        for i in range(n):
            t = i / sr
            # ゆっくりフェードイン・アウト
            fade_in = min(1.0, t / 2.0)
            fade_out = min(1.0, (dur - t) / 2.0)
            env = fade_in * fade_out * volume
            val = (math.sin(2 * math.pi * freq * t) * 0.5 +
                   math.sin(2 * math.pi * freq * 1.002 * t) * 0.5)  # デチューン
            samples.append(val * env)
        return samples

    # メインバッファ
    buf = [0.0] * total_samples

    # 背景パッド（低音D3 + A3）
    pad_d = pad_tone(146.83, duration_sec, 0.06)
    pad_a = pad_tone(220.00, duration_sec, 0.04)
    for i in range(min(len(pad_d), total_samples)):
        buf[i] += pad_d[i] + pad_a[i]

    # ピアノノート配置（ランダムだが再現可能）
    time_pos = 0.5  # 0.5秒後から開始
    while time_pos < duration_sec - 2.0:
        freq = rng.choice(base_freqs)
        note_dur = rng.choice([1.5, 2.0, 2.5, 3.0])
        vol = rng.uniform(0.15, 0.30)
        note = piano_tone(freq, note_dur, vol)
        start_idx = int(time_pos * sr)
        for i in range(min(len(note), total_samples - start_idx)):
            buf[start_idx + i] += note[i]
        time_pos += rng.uniform(1.0, 2.5)

    # 全体フェードイン/フェードアウト
    fade_in_samples = int(sr * 1.5)
    fade_out_samples = int(sr * 2.5)
    for i in range(min(fade_in_samples, total_samples)):
        buf[i] *= i / fade_in_samples
    for i in range(min(fade_out_samples, total_samples)):
        idx = total_samples - 1 - i
        buf[idx] *= i / fade_out_samples

    # クリッピング防止 & 16-bit変換
    peak = max(abs(s) for s in buf) or 1.0
    scale = 0.85 / peak
    raw = b"".join(struct.pack("<h", max(-32767, min(32767, int(s * scale * 32767)))) for s in buf)

    # WAVヘッダー書き込み
    with open(path, "wb") as f:
        data_size = len(raw)
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))       # chunk size
        f.write(struct.pack("<H", 1))        # PCM
        f.write(struct.pack("<H", 1))        # mono
        f.write(struct.pack("<I", sr))       # sample rate
        f.write(struct.pack("<I", sr * 2))   # byte rate
        f.write(struct.pack("<H", 2))        # block align
        f.write(struct.pack("<H", 16))       # bits per sample
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(raw)


def get_font(size, style="title"):
    """フォント取得（用途別に最適なフォントを選択）

    style:
        "title"  — 明朝体（タイトル・料理名・店名に）
        "body"   — ゴシック体（説明文・住所に）
        "accent" — 明朝体（英字・装飾テキストに）
    """
    # 明朝体（上品・高級感）: タイトル・料理名・店名
    mincho_paths = [
        # macOS
        "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc",
        "/System/Library/Fonts/ヒラギノ明朝 ProN W6.otf",
        "/Library/Fonts/Yu Mincho.ttc",
        # Linux
        "/usr/share/fonts/opentype/ipafont-mincho/ipamp.ttf",
        "/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf",
        "/usr/share/fonts/truetype/fonts-japanese-mincho.ttf",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSerifCJK-Regular.ttc",
    ]

    # ゴシック体（読みやすい）: 説明文・住所
    gothic_paths = [
        # macOS
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        # Linux
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

    # 最終フォールバック
    fallback = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for fp in fallback:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_text_with_shadow(draw, text, x, y, font, fill, shadow_color=(0, 0, 0), shadow_offset=2, shadow_blur=False):
    """影付きテキスト描画"""
    # 影
    for dx in range(-shadow_offset, shadow_offset + 1):
        for dy in range(-shadow_offset, shadow_offset + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=(*shadow_color, 120))
    # 本体
    draw.text((x, y), text, font=font, fill=fill)


def draw_text_overlay(frame, texts, text_progress):
    """テキストオーバーレイを描画（text_progress: 各テキストの可視進捗）"""
    frame_rgba = frame.convert("RGBA")
    txt_layer = Image.new("RGBA", frame_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_layer)

    for i, t in enumerate(texts):
        if i >= len(text_progress) or text_progress[i] <= 0:
            continue

        tp = min(1.0, text_progress[i])
        alpha = int(255 * tp)
        y_offset = int(8 * (1 - tp))  # 控えめなフェードアップ

        font = get_font(t["size"], t.get("font", "title"))
        text_str = t["text"]
        color = t["color"]
        y_pos = int(HEIGHT * t["y"]) + y_offset
        align = t.get("align", "center")

        # テキスト幅を取得
        bbox = draw.textbbox((0, 0), text_str, font=font)
        tw = bbox[2] - bbox[0]

        if align == "center":
            x_pos = (WIDTH - tw) // 2
        else:  # left
            x_pos = 30

        # 影付き描画（alpha適用）
        fill_with_alpha = (*color, alpha)
        shadow_alpha = int(120 * tp)

        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x_pos + dx, y_pos + dy), text_str, font=font, fill=(0, 0, 0, shadow_alpha))

        draw.text((x_pos, y_pos), text_str, font=font, fill=fill_with_alpha)

    return Image.alpha_composite(frame_rgba, txt_layer).convert("RGB")


def draw_gold_line(frame, y_ratio, progress):
    """金色の水平ライン"""
    if progress <= 0:
        return frame
    frame_rgba = frame.convert("RGBA")
    draw = ImageDraw.Draw(frame_rgba)
    line_w = int(60 * progress)
    cx = WIDTH // 2
    y = int(HEIGHT * y_ratio)
    alpha = int(255 * min(1.0, progress))
    draw.rectangle(
        [(cx - line_w // 2, y), (cx + line_w // 2, y + 1)],
        fill=(*GOLD, alpha)
    )
    return frame_rgba.convert("RGB")


def crossfade_frames(frame_a, frame_b, t):
    """2フレーム間のクロスフェード（t: 0.0=A, 1.0=B）"""
    return Image.blend(frame_a, frame_b, t)


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
        # Background
        draw.rectangle([(x, bar_y), (x + seg_w, bar_y + bar_h)], fill=(255, 255, 255, 70))
        # Fill
        if i < scene_idx:
            fill_w = seg_w
        elif i == scene_idx:
            fill_w = seg_w * scene_progress
        else:
            fill_w = 0

        if fill_w > 0:
            draw.rectangle([(x, bar_y), (x + fill_w, bar_y + bar_h)], fill=(255, 255, 255, 220))

    return frame_rgba.convert("RGB")


# ── メイン生成ロジック ──────────────────────────────

def generate_video():
    os.makedirs(FRAMES_DIR, exist_ok=True)

    # 1. 画像をダウンロード
    print("📷 画像をダウンロード中...")
    images = []
    for i, scene in enumerate(SCENES):
        print(f"  Scene {i+1}/{len(SCENES)}")
        img = download_image(scene["image"])
        images.append(img)

    # 2. フレームを生成
    print(f"\n🎬 フレーム生成中 ({FPS}fps)...")
    all_frames = []
    frame_count = 0
    total_scenes = len(SCENES)
    crossfade_duration = 0.4  # クロスフェード

    for si, scene in enumerate(SCENES):
        duration = scene["duration"]
        n_frames = int(duration * FPS)
        texts = scene["texts"]
        text_delay = scene.get("text_delay", 0.2)
        has_fade_in = scene.get("fade_in", False)

        scene_frames = []

        for fi in range(n_frames):
            t = fi / max(1, n_frames - 1)  # 0.0 ~ 1.0
            time_s = fi / FPS

            # Ken Burns
            kb_frame = apply_ken_burns(images[si], scene["effect"], t, WIDTH, HEIGHT)

            # 蓋開け効果（黒からフェードイン）
            if has_fade_in and t < 0.3:
                fade_t = t / 0.3
                black = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
                kb_frame = crossfade_frames(black, kb_frame, fade_t)

            # グラデーションオーバーレイ
            frame = draw_gradient_overlay(kb_frame)

            # テキスト進捗（ゆっくりフェードイン）
            text_prog = []
            for ti in range(len(texts)):
                delay = text_delay + ti * 0.35
                if time_s < delay:
                    text_prog.append(0.0)
                else:
                    raw = min(1.0, (time_s - delay) / 0.8)
                    text_prog.append(ease_in_out(raw))

            frame = draw_text_overlay(frame, texts, text_prog)

            # プログレスバー
            frame = draw_progress_bar(frame, si, total_scenes, t)

            scene_frames.append(frame)
            frame_count += 1

        # クロスフェード: 前のシーンの最後数フレームと合成
        cf_frames = int(crossfade_duration * FPS)
        if si > 0 and len(all_frames) >= cf_frames:
            for ci in range(cf_frames):
                blend_t = (ci + 1) / cf_frames
                idx = len(all_frames) - cf_frames + ci
                all_frames[idx] = crossfade_frames(all_frames[idx], scene_frames[ci], blend_t)
            scene_frames = scene_frames[cf_frames:]

        all_frames.extend(scene_frames)
        print(f"  Scene {si+1}/{total_scenes} done ({len(scene_frames)} frames)")

    # 3. フレーム保存
    print(f"\n💾 {len(all_frames)} フレームを保存中...")
    for i, frame in enumerate(all_frames):
        frame.save(os.path.join(FRAMES_DIR, f"frame_{i:04d}.png"), "PNG")

    # 4. GIFアニメーション生成
    print("\n🎞️  GIFアニメーション生成中...")
    gif_path = os.path.join(OUTPUT_DIR, "reels_video.gif")
    # GIF用にリサイズ（ファイルサイズ削減）
    gif_w, gif_h = 270, 480
    gif_frames = [f.resize((gif_w, gif_h), Image.LANCZOS).quantize(colors=128, method=Image.Quantize.MEDIANCUT) for f in all_frames]
    gif_frames[0].save(
        gif_path,
        save_all=True,
        append_images=gif_frames[1:],
        duration=int(1000 / FPS),
        loop=0,
        optimize=True,
    )
    gif_size = os.path.getsize(gif_path) / (1024 * 1024)
    print(f"  → {gif_path} ({gif_size:.1f} MB)")

    # 5. WebPアニメーション生成（高品質）
    print("\n🎞️  WebPアニメーション生成中...")
    webp_path = os.path.join(OUTPUT_DIR, "reels_video.webp")
    webp_frames = [f.resize((gif_w, gif_h), Image.LANCZOS) for f in all_frames]
    webp_frames[0].save(
        webp_path,
        save_all=True,
        append_images=webp_frames[1:],
        duration=int(1000 / FPS),
        loop=0,
        quality=70,
        method=4,
    )
    webp_size = os.path.getsize(webp_path) / (1024 * 1024)
    print(f"  → {webp_path} ({webp_size:.1f} MB)")

    # 6. MP4動画生成（FFmpegが使える場合）
    total_duration = len(all_frames) / FPS
    mp4_path = os.path.join(OUTPUT_DIR, "reels_video.mp4")
    if shutil.which("ffmpeg"):
        # 6a. 無音MP4を先に生成
        print("\n🎬 MP4動画生成中...")
        mp4_silent = os.path.join(OUTPUT_DIR, "reels_video_silent.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", os.path.join(FRAMES_DIR, "frame_%04d.png"),
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={WIDTH}:{HEIGHT}",
            mp4_silent,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ⚠️  MP4生成に失敗しました: {result.stderr[-200:]}")
            mp4_path = None
        else:
            # 6b. BGM準備
            bgm_source = None
            if os.path.exists(BGM_FILE):
                bgm_source = BGM_FILE
                print(f"\n🎵 カスタムBGM: {BGM_FILE}")
            else:
                # フォールバック: 合成BGM
                print("\n🎵 BGM生成中（ピアノアンビエント）...")
                bgm_source = os.path.join(OUTPUT_DIR, "bgm.wav")
                generate_bgm_wav(bgm_source, total_duration)

            bgm_size = os.path.getsize(bgm_source) / 1024
            print(f"  → {bgm_source} ({bgm_size:.0f} KB)")

            # 6c. 映像 + BGM合成（ループ＋フェードアウト対応）
            print("\n🎬 映像とBGMを合成中...")
            # BGMをループして動画長に合わせ、末尾2秒フェードアウト
            fade_out_sec = 2.0
            audio_filter = (
                f"aloop=loop=-1:size=2e+09,"
                f"atrim=duration={total_duration},"
                f"afade=t=out:st={total_duration - fade_out_sec}:d={fade_out_sec}"
            )
            cmd_merge = [
                "ffmpeg", "-y",
                "-i", mp4_silent,
                "-stream_loop", "-1",
                "-i", bgm_source,
                "-c:v", "copy",
                "-af", audio_filter,
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                mp4_path,
            ]
            result2 = subprocess.run(cmd_merge, capture_output=True, text=True)
            if result2.returncode == 0:
                mp4_size = os.path.getsize(mp4_path) / (1024 * 1024)
                print(f"  → {mp4_path} ({mp4_size:.1f} MB) ♪ BGM付き")
                os.remove(mp4_silent)
                # 合成BGMの一時ファイルがあれば削除
                tmp_bgm = os.path.join(OUTPUT_DIR, "bgm.wav")
                if os.path.exists(tmp_bgm):
                    os.remove(tmp_bgm)
            else:
                print(f"  ⚠️  BGM合成に失敗。無音版を使用します: {result2.stderr[-200:]}")
                os.rename(mp4_silent, mp4_path)
                mp4_size = os.path.getsize(mp4_path) / (1024 * 1024)
                print(f"  → {mp4_path} ({mp4_size:.1f} MB)")
    else:
        print("\n⚠️  ffmpegが見つかりません。MP4生成をスキップします。")
        print("   インストール方法:")
        print("     macOS:  brew install ffmpeg")
        print("     Ubuntu: sudo apt install ffmpeg")
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
