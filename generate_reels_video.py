#!/usr/bin/env python3
"""
北新地 大嵓埜 — Instagram Reels 動画生成スクリプト

PillowのみでReels動画（9:16）を生成します。
出力形式: 連番PNG → 最終的にGIFアニメーション or WebPアニメーション

使い方:
    python3 generate_reels_video.py

出力:
    output/reels_video.gif   — GIFアニメーション
    output/reels_video.webp  — WebPアニメーション（高品質）
    output/frames/           — 全フレーム連番PNG
"""

import os
import io
import math
import struct
import zlib
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── 設定 ──────────────────────────────────────────
WIDTH = 540                # 9:16 Reels解像度
HEIGHT = 960
FPS = 12                   # GIF/WebP用フレームレート
BG_COLOR = (10, 10, 10)
GOLD = (196, 162, 101)
GOLD_LIGHT = (232, 213, 168)
WHITE = (255, 255, 255)

OUTPUT_DIR = "output"
FRAMES_DIR = os.path.join(OUTPUT_DIR, "frames")

# ── シーン定義 ─────────────────────────────────────
SCENES = [
    {
        "image": "https://github.com/user-attachments/assets/6e9bb9c1-0ead-47de-b875-ac9dfde0c3b7",
        "duration": 2.5,
        "effect": "zoom_in",
        "texts": [
            {"text": "MICHELIN SELECTED", "y": 0.32, "size": 16, "color": GOLD, "spacing": 4},
            {"text": "━━", "y": 0.37, "size": 14, "color": GOLD},
            {"text": "北新地 大嵓埜", "y": 0.43, "size": 36, "color": WHITE, "spacing": 8},
            {"text": "季節の恵みを味わう、特別なひととき", "y": 0.50, "size": 16, "color": GOLD_LIGHT, "spacing": 2},
        ],
        "text_delay": 0.3,
    },
    {
        "image": "https://github.com/user-attachments/assets/b02cc12f-1be7-4498-835c-e002b4d5afa2",
        "duration": 2.2,
        "effect": "zoom_out",
        "texts": [
            {"text": "先付け", "y": 0.78, "size": 32, "color": WHITE, "spacing": 6, "align": "left"},
            {"text": "爽やかな季節野菜のハーモニー", "y": 0.84, "size": 15, "color": (220, 220, 220), "spacing": 2, "align": "left"},
        ],
        "text_delay": 0.2,
    },
    {
        "image": "https://github.com/user-attachments/assets/b3a7eefa-2fd5-4ce0-8830-d665a788b10d",
        "duration": 2.2,
        "effect": "pan_right",
        "texts": [
            {"text": "刺  身", "y": 0.78, "size": 32, "color": WHITE, "spacing": 6, "align": "left"},
            {"text": "海の恵みを華やかに", "y": 0.84, "size": 15, "color": (220, 220, 220), "spacing": 2, "align": "left"},
        ],
        "text_delay": 0.2,
    },
    {
        "image": "https://github.com/user-attachments/assets/58250abe-6813-4005-9973-aaf2266b4ea6",
        "duration": 2.2,
        "effect": "zoom_tilt",
        "texts": [
            {"text": "煮  物", "y": 0.78, "size": 32, "color": WHITE, "spacing": 6, "align": "left"},
            {"text": "牛肉と春の山菜", "y": 0.84, "size": 15, "color": (220, 220, 220), "spacing": 2, "align": "left"},
        ],
        "text_delay": 0.2,
    },
    {
        "image": "https://github.com/user-attachments/assets/89d7a632-b7be-46f6-b301-5feb0b31991d",
        "duration": 2.0,
        "effect": "zoom_in",
        "texts": [
            {"text": "焼き物", "y": 0.78, "size": 32, "color": WHITE, "spacing": 6, "align": "left"},
            {"text": "香ばしい竹の子と帆立", "y": 0.84, "size": 15, "color": (220, 220, 220), "spacing": 2, "align": "left"},
        ],
        "text_delay": 0.2,
    },
    {
        "image": "https://github.com/user-attachments/assets/34173214-d90e-4556-b22f-75f53e756304",
        "duration": 2.0,
        "effect": "pan_left",
        "texts": [
            {"text": "揚げ物", "y": 0.78, "size": 32, "color": WHITE, "spacing": 6, "align": "left"},
            {"text": "サクサクの食感で心を掴む", "y": 0.84, "size": 15, "color": (220, 220, 220), "spacing": 2, "align": "left"},
        ],
        "text_delay": 0.2,
    },
    {
        "image": "https://github.com/user-attachments/assets/a990a366-4d57-4cdd-8766-0c5d794f5bfc",
        "duration": 1.8,
        "effect": "zoom_out",
        "texts": [
            {"text": "強  肴", "y": 0.78, "size": 32, "color": WHITE, "spacing": 6, "align": "left"},
            {"text": "手まり寿司の贅沢", "y": 0.84, "size": 15, "color": (220, 220, 220), "spacing": 2, "align": "left"},
        ],
        "text_delay": 0.2,
    },
    {
        "image": "https://github.com/user-attachments/assets/d192340c-a5af-4ef6-acd7-56ed93cb771f",
        "duration": 1.8,
        "effect": "zoom_tilt",
        "texts": [
            {"text": "清  湯", "y": 0.78, "size": 32, "color": WHITE, "spacing": 6, "align": "left"},
            {"text": "優雅なフィナーレ", "y": 0.84, "size": 15, "color": (220, 220, 220), "spacing": 2, "align": "left"},
        ],
        "text_delay": 0.2,
    },
    {
        "image": "https://github.com/user-attachments/assets/ee7a5a4a-885d-4f95-b83c-5ee014652a4c",
        "duration": 2.2,
        "effect": "zoom_in",
        "texts": [
            {"text": "ご  飯", "y": 0.78, "size": 32, "color": WHITE, "spacing": 6, "align": "left"},
            {"text": "えびと緑のハーモニー", "y": 0.84, "size": 15, "color": (220, 220, 220), "spacing": 2, "align": "left"},
        ],
        "text_delay": 0.2,
        "fade_in": True,
    },
    {
        "image": "https://github.com/user-attachments/assets/b39bf119-c360-47df-b8b1-5399b4445ab1",
        "duration": 2.2,
        "effect": "zoom_out",
        "texts": [
            {"text": "デザート", "y": 0.78, "size": 32, "color": WHITE, "spacing": 6, "align": "left"},
            {"text": "苺・メロン・マンゴーの甘美", "y": 0.84, "size": 15, "color": (220, 220, 220), "spacing": 2, "align": "left"},
        ],
        "text_delay": 0.2,
    },
    {
        "image": "https://github.com/user-attachments/assets/6e9bb9c1-0ead-47de-b875-ac9dfde0c3b7",
        "duration": 3.0,
        "effect": "zoom_in",
        "texts": [
            {"text": "接待・記念日に", "y": 0.30, "size": 18, "color": WHITE, "spacing": 3},
            {"text": "━━", "y": 0.36, "size": 14, "color": GOLD},
            {"text": "大嵓埜", "y": 0.43, "size": 42, "color": WHITE, "spacing": 10},
            {"text": "06-6341-3535", "y": 0.53, "size": 30, "color": GOLD, "spacing": 4},
            {"text": "北新地 FOODEAR ビル 3F", "y": 0.60, "size": 13, "color": (180, 180, 180), "spacing": 2},
        ],
        "text_delay": 0.25,
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


def apply_ken_burns(img, effect, progress, canvas_w, canvas_h):
    """Ken Burnsエフェクトを適用（progress: 0.0〜1.0）"""
    # 大きめに取って変形後にクロップ
    pad = 1.25  # 25%余分に確保
    base = fit_cover(img, int(canvas_w * pad), int(canvas_h * pad))
    bw, bh = base.size
    t = progress

    if effect == "zoom_in":
        scale = 1.0 + 0.15 * t
        cx, cy = bw / 2, bh / 2
    elif effect == "zoom_out":
        scale = 1.15 - 0.15 * t
        cx, cy = bw / 2, bh / 2
    elif effect == "pan_right":
        scale = 1.1
        cx = bw / 2 + (bw * 0.05) * (2 * t - 1)
        cy = bh / 2
    elif effect == "pan_left":
        scale = 1.1
        cx = bw / 2 - (bw * 0.05) * (2 * t - 1)
        cy = bh / 2
    elif effect == "zoom_tilt":
        scale = 1.0 + 0.1 * t
        cx = bw / 2 + math.sin(t * 0.3) * 5
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


def get_font(size):
    """フォント取得（日本語対応のシステムフォントを検索）"""
    font_paths = [
        "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf",   # IPA Pゴシック（プロポーショナル）
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",    # IPAゴシック
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",   # IPAゴシック（別パス）
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",        # WenQuanYi
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    # フォールバック
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
        y_offset = int(12 * (1 - tp))  # 下からフェードアップ

        font = get_font(t["size"])
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
    crossfade_duration = 0.25  # クロスフェード秒数

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

            # テキスト進捗
            text_prog = []
            for ti in range(len(texts)):
                delay = text_delay + ti * 0.25
                if time_s < delay:
                    text_prog.append(0.0)
                else:
                    text_prog.append(min(1.0, (time_s - delay) / 0.4))

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

    # 6. フルサイズWebP版も生成
    print("\n🎞️  フルサイズWebP生成中...")
    webp_full_path = os.path.join(OUTPUT_DIR, "reels_video_fullsize.webp")
    all_frames[0].save(
        webp_full_path,
        save_all=True,
        append_images=all_frames[1:],
        duration=int(1000 / FPS),
        loop=0,
        quality=60,
        method=4,
    )
    full_size = os.path.getsize(webp_full_path) / (1024 * 1024)
    print(f"  → {webp_full_path} ({full_size:.1f} MB)")

    print(f"\n✅ 完了！")
    print(f"   フレーム数: {len(all_frames)}")
    print(f"   合計秒数:   {len(all_frames)/FPS:.1f}秒")
    print(f"\n📁 出力ファイル:")
    print(f"   {gif_path}             — GIF（SNS共有向け）")
    print(f"   {webp_path}            — WebP（高品質、小サイズ）")
    print(f"   {webp_full_path}  — WebP フルサイズ（540x960）")
    print(f"   {FRAMES_DIR}/              — 全フレーム連番PNG")
    print(f"\n💡 Tips:")
    print(f"   • WebPはブラウザで直接再生可能")
    print(f"   • 連番PNGからFFmpegでMP4変換:")
    print(f"     ffmpeg -framerate {FPS} -i {FRAMES_DIR}/frame_%04d.png -c:v libx264 -pix_fmt yuv420p reels.mp4")


if __name__ == "__main__":
    generate_video()
