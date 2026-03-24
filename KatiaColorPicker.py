import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import pyperclip
import mss
from pynput.mouse import Controller
import json, os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "dark_mode": True,
    "pro_mode": True
}

ACCENT = "#4cc2ff"


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            return json.load(open(CONFIG_FILE))
        except:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG


def save_config(cfg):
    json.dump(cfg, open(CONFIG_FILE, "w"), indent=4)


# -------------------------
# ROUNDED CARD
# -------------------------
def rounded_frame(parent, bg):
    frame = tk.Frame(parent, bg=bg)
    frame.pack(pady=8, fill="x")
    return frame


class ColorPicker:
    def __init__(self, root):
        self.root = root
        self.config = load_config()

        self.mouse = Controller()
        self.zoom = 6
        self.history = []

        self.apply_theme()

        # -------- MAIN CARD --------
        self.card = rounded_frame(root, self.bg)

        self.color_display = tk.Label(self.card, height=4, bg="#ff0000")
        self.color_display.pack(fill="x", pady=6)

        self.hex_entry = tk.Entry(self.card, justify="center", font=("Segoe UI", 11))
        self.hex_entry.pack(fill="x", pady=4)

        self.button("🎯 Pick Color", self.start_picker)
        self.button("📋 Copy HEX", self.copy_hex)
        self.button("📋 Copy RGB", self.copy_rgb)
        self.button("🎨 Save Palette", self.save_palette)

        # PRO feature
        if self.config.get("pro_mode"):
            self.button("📦 Export CSS", self.export_css)

        self.palette_frame = tk.Frame(self.card, bg=self.bg)
        self.palette_frame.pack(pady=6)

        self.update_color(255, 0, 0)

    # -------------------------
    def apply_theme(self):
        if self.config["dark_mode"]:
            self.bg = "#0f0f0f"
            self.fg = "white"
        else:
            self.bg = "white"
            self.fg = "black"

        self.root.configure(bg=self.bg)

    # -------------------------
    def button(self, text, cmd):
        b = tk.Label(self.card, text=text, bg="#1f1f1f", fg="white",
                     padx=10, pady=6, cursor="hand2")
        b.pack(fill="x", pady=2)

        b.bind("<Enter>", lambda e: b.config(bg=ACCENT))
        b.bind("<Leave>", lambda e: b.config(bg="#1f1f1f"))
        b.bind("<Button-1>", lambda e: cmd())

    # -------------------------
    def update_color(self, r, g, b):
        self.r, self.g, self.b = r, g, b
        self.hex = f"#{r:02x}{g:02x}{b:02x}".upper()

        self.color_display.config(bg=self.hex)
        self.hex_entry.delete(0, tk.END)
        self.hex_entry.insert(0, self.hex)

    def copy_hex(self):
        pyperclip.copy(self.hex)

    def copy_rgb(self):
        pyperclip.copy(f"rgb({self.r},{self.g},{self.b})")

    # -------------------------
    # PICKER (FAST + FIXED)
    # -------------------------
    def start_picker(self):
        try:
            self.root.withdraw()

            self.overlay = tk.Toplevel()
            self.overlay.overrideredirect(True)
            self.overlay.attributes("-topmost", True)
            self.overlay.geometry(
                f"{self.overlay.winfo_screenwidth()}x{self.overlay.winfo_screenheight()}+0+0"
            )

            self.overlay.attributes("-alpha", 0.01)
            self.overlay.config(cursor="crosshair")

            self.zoom_win = tk.Toplevel()
            self.zoom_win.overrideredirect(True)
            self.zoom_win.attributes("-topmost", True)

            self.canvas = tk.Canvas(self.zoom_win, width=120, height=120)
            self.canvas.pack()

            self.label = tk.Label(self.zoom_win, bg="black", fg="white")
            self.label.pack()

            self.update_preview()

            self.overlay.bind("<Button-1>", self.pick)
            self.overlay.bind("<MouseWheel>", self.scroll)

        except Exception as e:
            print("Picker error:", e)
            self.root.deiconify()

    def scroll(self, e):
        self.zoom = max(2, min(20, self.zoom - 1 if e.delta > 0 else self.zoom + 1))

    def update_preview(self):
        if not hasattr(self, "overlay"):
            return

        x, y = self.mouse.position
        z = self.zoom

        with mss.mss() as sct:
            monitor = {"left": x - z, "top": y - z, "width": z*2, "height": z*2}
            img = sct.grab(monitor)

        image = Image.frombytes("RGB", img.size, img.rgb)
        image = image.resize((120, 120), Image.NEAREST)

        self.tk_img = ImageTk.PhotoImage(image)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        self.canvas.create_line(60, 0, 60, 120, fill="red")
        self.canvas.create_line(0, 60, 120, 60, fill="red")

        self.zoom_win.geometry(f"+{x+20}+{y+20}")

        r, g, b = img.pixel(z, z)
        self.update_color(r, g, b)

        self.label.config(text=f"{self.hex} | Z:{self.zoom}")

        self.overlay.after(16, self.update_preview)

    def pick(self, e):
        self.add_palette(self.hex)
        self.cleanup()

    def cleanup(self):
        self.overlay.destroy()
        self.zoom_win.destroy()
        self.root.deiconify()

    # -------------------------
    # PALETTE (PRO READY)
    # -------------------------
    def add_palette(self, c):
        if c not in self.history:
            self.history.insert(0, c)
        self.history = self.history[:10]
        self.refresh_palette()

    def refresh_palette(self):
        for w in self.palette_frame.winfo_children():
            w.destroy()

        for c in self.history:
            tk.Label(self.palette_frame, bg=c, width=4, height=2).pack(side="left", padx=2)

    def save_palette(self):
        img = Image.new("RGB", (50 * len(self.history), 50))
        draw = ImageDraw.Draw(img)

        for i, c in enumerate(self.history):
            draw.rectangle([i*50, 0, (i+1)*50, 50], fill=c)

        img.save("palette.png")

    # -------------------------
    # PRO FEATURE
    # -------------------------
    def export_css(self):
        with open("palette.css", "w") as f:
            for i, c in enumerate(self.history):
                f.write(f"--color{i}: {c};\n")


# -------------------------
# SAFE START (FIXES LAUNCH)
# -------------------------
if __name__ == "__main__":
    try:
        root = tk.Tk()
        root.title("Katia Picker Pro")
        app = ColorPicker(root)
        root.mainloop()
    except Exception as e:
        with open("error_log.txt", "w") as f:
            f.write(str(e))