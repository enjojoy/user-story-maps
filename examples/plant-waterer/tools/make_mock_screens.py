#!/usr/bin/env python3
"""Draws simple MOCK UI screens for the fictional 'Plant Waterer' example (Pillow only).
In a real app these files are real screenshots from a simulator / emulator / browser (see SKILL.md)."""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 780, 1688  # 390x844 pt @2x
OUT = os.path.join(os.path.dirname(__file__), "..", "screens")
GREEN, DARK, SOFT, INK, MUT = "#2E9E6B", "#1F5A43", "#E3F5EC", "#202124", "#5F6368"


def F(size, bold=False):
    for n in (["DejaVuSans-Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"] if bold
              else ["DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"]):
        try:
            return ImageFont.truetype(n, size)
        except Exception:
            pass
    return ImageFont.load_default()


def base(title=None, bg="white", back=False):
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    d.text((60, 36), "9:41", font=F(30, True), fill=INK)
    d.rounded_rectangle((650, 44, 720, 72), 8, outline=INK, width=3)
    d.rectangle((654, 48, 700, 68), fill=INK)
    if title:
        if back:
            d.text((40, 130), "<", font=F(56, True), fill=GREEN)
        d.text((100 if back else 50, 130), title, font=F(52, True), fill=INK)
    return im, d


def plant(d, cx, cy, s=1.0):
    d.polygon([(cx - 70 * s, cy), (cx + 70 * s, cy), (cx + 50 * s, cy + 110 * s), (cx - 50 * s, cy + 110 * s)], fill="#C9733E")
    for dx, dy, w, h in [(-60, -90, 70, 130), (0, -140, 70, 150), (60, -90, 70, 130)]:
        d.ellipse((cx + (dx - w / 2) * s, cy + dy * s, cx + (dx + w / 2) * s, cy + (dy + h) * s), fill=GREEN)


def button(d, y, text, primary=True, x0=60, x1=720):
    d.rounded_rectangle((x0, y, x1, y + 110), 30, fill=GREEN if primary else "white", outline=GREEN, width=4)
    f = F(36, True)
    d.text(((x0 + x1) / 2 - d.textlength(text, font=f) / 2, y + 34), text, font=f, fill="white" if primary else GREEN)


def field(d, y, label, value):
    d.text((60, y), label, font=F(26), fill=MUT)
    d.rounded_rectangle((60, y + 40, 720, y + 130), 20, fill="#F1F3F4")
    d.text((90, y + 62), value, font=F(34), fill=INK)


def tabbar(d, active=0):
    d.rectangle((0, H - 170, W, H), fill="white")
    d.line((0, H - 170, W, H - 170), fill="#DADCE0", width=2)
    for i, t in enumerate(["Plants", "Reminders", "Settings"]):
        x = 130 + i * 260
        d.ellipse((x - 20, H - 140, x + 20, H - 100), fill=GREEN if i == active else "#BDC1C6")
        f = F(24, i == active)
        d.text((x - d.textlength(t, font=f) / 2, H - 88), t, font=f, fill=GREEN if i == active else MUT)


def card(d, y, name, sub, chip, chipcol):
    d.rounded_rectangle((50, y, 730, y + 190), 28, fill="white", outline="#DADCE0", width=3)
    d.rounded_rectangle((75, y + 25, 215, y + 165), 24, fill=SOFT)
    plant(d, 145, y + 95, 0.45)
    d.text((245, y + 40), name, font=F(38, True), fill=INK)
    d.text((245, y + 95), sub, font=F(27), fill=MUT)
    f = F(24, True)
    wd = d.textlength(chip, font=f) + 36
    d.rounded_rectangle((245, y + 135, 245 + wd, y + 175), 18, fill=chipcol)
    d.text((263, y + 141), chip, font=f, fill="white")


def save(im, name):
    os.makedirs(OUT, exist_ok=True)
    im.save(os.path.join(OUT, name + ".png"), optimize=True)


# welcome
im, d = base(bg=SOFT)
plant(d, 390, 560, 2.2)
d.text((390 - d.textlength("Plant Waterer", font=F(64, True)) / 2, 840), "Plant Waterer", font=F(64, True), fill=DARK)
t = "Never forget to water again"
d.text((390 - d.textlength(t, font=F(34)) / 2, 940), t, font=F(34), fill=MUT)
button(d, 1230, "Add my first plant")
button(d, 1380, "Skip for now", primary=False)
save(im, "welcome")

# add plant
im, d = base("Add a plant", back=True)
field(d, 260, "Name", "Monty")
field(d, 450, "Species", "Monstera")
d.text((60, 660), "Common houseplants", font=F(28, True), fill=MUT)
for i, n in enumerate(["Monstera", "Pothos", "Snake plant", "Peace lily"]):
    d.rounded_rectangle((60, 720 + i * 120, 720, 820 + i * 120), 20, fill=SOFT if i == 0 else "#F8F9FA")
    d.text((90, 748 + i * 120), n, font=F(34), fill=INK)
button(d, 1380, "Save")
save(im, "add-plant")

# plant list
im, d = base("My plants")
d.ellipse((650, 128, 710, 188), outline=MUT, width=5)
card(d, 260, "Monty", "Monstera  |  every 7 days", "Thirsty today", "#D93025")
card(d, 480, "Ferdinand", "Pothos  |  every 10 days", "Water in 2 days", GREEN)
card(d, 700, "Snek", "Snake plant  |  every 14 days", "Water in 6 days", GREEN)
card(d, 920, "Lily", "Peace lily  |  every 5 days", "Water in 1 day", "#E8A33D")
d.ellipse((600, H - 330, 710, H - 220), fill=GREEN)
d.text((634, H - 322), "+", font=F(90, True), fill="white")
tabbar(d, 0)
save(im, "plant-list")

# plant detail
im, d = base("Monty", back=True)
d.rounded_rectangle((60, 240, 720, 700), 40, fill=SOFT)
plant(d, 390, 480, 1.6)
d.text((60, 740), "Monstera", font=F(40, True), fill=INK)
for i, (a, b) in enumerate([("Water every", "7 days"), ("Next watering", "Today"), ("Light", "Bright, indirect")]):
    y = 830 + i * 100
    d.text((60, y), a, font=F(30), fill=MUT)
    d.text((720 - d.textlength(b, font=F(30, True)), y), b, font=F(30, True), fill=INK)
    d.line((60, y + 60, 720, y + 60), fill="#E8EAED", width=2)
button(d, 1180, "Water now")
button(d, 1320, "History", primary=False, x1=380)
button(d, 1320, "Edit reminder", primary=False, x0=400)
save(im, "plant-detail")

# watered
im, d = base(bg="#7A7F85")
d.rounded_rectangle((90, 430, 690, 1130), 50, fill="white")
d.ellipse((290, 500, 490, 700), fill=GREEN)
d.line((340, 600, 380, 650, 450, 550), fill="white", width=18, joint="curve")
for y, t, f in [(750, "Monty is watered!", F(44, True)), (830, "Next water: in 7 days", F(30))]:
    d.text((390 - d.textlength(t, font=f) / 2, y), t, font=f, fill=INK)
button(d, 960, "Done", x0=140, x1=640)
save(im, "watered")

# reminders
im, d = base("Reminder schedule", back=True)
for i, (a, b) in enumerate([("Remind me", "ON"), ("Repeat", "Every 7 days"), ("Time", "08:00")]):
    y = 270 + i * 130
    d.text((60, y + 20), a, font=F(36), fill=INK)
    if b == "ON":
        d.rounded_rectangle((590, y + 10, 720, y + 80), 35, fill=GREEN)
        d.ellipse((660, y + 14, 716, y + 76), fill="white")
    else:
        d.text((720 - d.textlength(b, font=F(34, True)), y + 20), b, font=F(34, True), fill=GREEN)
    d.line((60, y + 105, 720, y + 105), fill="#E8EAED", width=2)
d.text((60, 700), "Snooze", font=F(36), fill=MUT)
d.text((60, 760), "Not available yet", font=F(28), fill="#9AA0A6")
button(d, 1380, "Turn on reminders")
save(im, "reminders")

# notification permission
im, d = base("Reminder schedule", back=True)
ov = Image.new("RGBA", (W, H), (0, 0, 0, 140))
im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
d = ImageDraw.Draw(im)
d.rounded_rectangle((110, 600, 670, 1020), 40, fill="#F2F2F7")
for i, ln in enumerate(['"Plant Waterer" Would', "Like to Send You", "Notifications"]):
    d.text((390 - d.textlength(ln, font=F(34, True)) / 2, 640 + i * 46), ln, font=F(34, True), fill=INK)
d.line((110, 900, 670, 900), fill="#C6C6C8", width=2)
d.line((390, 900, 390, 1020), fill="#C6C6C8", width=2)
d.text((250 - d.textlength("Don't Allow", font=F(32)) / 2, 940), "Don't Allow", font=F(32), fill="#007AFF")
d.text((530 - d.textlength("Allow", font=F(32, True)) / 2, 940), "Allow", font=F(32, True), fill="#007AFF")
save(im, "notif-permission")

# push (lock screen)
im = Image.new("RGB", (W, H), "#2B4C45")
d = ImageDraw.Draw(im)
d.text((390 - d.textlength("Thursday 15 October", font=F(34)) / 2, 250), "Thursday 15 October", font=F(34), fill="white")
d.text((390 - d.textlength("08:00", font=F(150, True)) / 2, 310), "08:00", font=F(150, True), fill="white")
d.rounded_rectangle((50, 700, 730, 880), 36, fill="#F2F2F7")
d.ellipse((80, 730, 160, 810), fill=GREEN)
d.text((190, 735), "Plant Waterer", font=F(28, True), fill=INK)
d.text((190, 780), "Monty is thirsty - time to water.", font=F(28), fill=MUT)
save(im, "push")

# settings
im, d = base("Settings")
for i, (a, b) in enumerate([("Default reminder time", "08:00"), ("Units", "Metric"), ("Share my garden", ">"),
                            ("Export my data", ">"), ("About", "v1.0")]):
    y = 270 + i * 130
    d.text((60, y + 20), a, font=F(36), fill=INK)
    d.text((720 - d.textlength(b, font=F(32)), y + 20), b, font=F(32), fill=MUT)
    d.line((60, y + 105, 720, y + 105), fill="#E8EAED", width=2)
tabbar(d, 2)
save(im, "settings")
print("mock screens written to", os.path.abspath(OUT))
