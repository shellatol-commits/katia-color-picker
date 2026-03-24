import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import pyperclip
from pynput.mouse import Controller
import mss
import json, os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "dark_mode": True,
    "pro_mode": True
}

ACCENT = "#4cc2ff"
ZOOM_SIZE = 120


# -------------------------
# CONFIG
# -------------------------
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
# APP
# -------------------------
class ColorPicker:
    def __init__(self, root):
        self.root = root
        self.config = load_config()

        self.mouse = Controller()
        self.zoom = 6
        self.history = []
        self.frozen = False

        self.apply_theme()

        # -------- MAIN CARD --------
        self.card = tk.Frame(root, bg=self.bg)
        self.card.pack(padx=12, pady=12)

        self.color_display = tk.Label(self.card, height=4, bg="#ff0000")
        self.color_display.pack(fill="x", pady=6)

        self.hex_entry = tk.Entry(self.card, justify="center", font=("Segoe UI", 11))
        self.hex_entry.pack(fill="x", pady=4)

        self.make_btn("🎯 Pick Color", self.start_picker)
        self.make_btn("📋 Copy HEX", self.copy_hex)
        self.make_btn("📋 Copy RGB", self.copy_rgb)
        self.make_btn("🎨 Save Palette", self.save_palette)

        if self.config.get("pro_mode"):
            self.make_btn("📦 Export CSS", self.export_css)

        self.make_btn("⚙ Settings", self.open_settings)

        # ---------- SLIDERS ----------
        self.slider_frame = tk.Frame(self.card, bg=self.bg)
        self.slider_frame.pack(pady=8, fill="x")

        self.r_var = tk.IntVar(value=255)
        self.g_var = tk.IntVar(value=0)
        self.b_var = tk.IntVar(value=0)

        self.create_slider("R", self.r_var)
        self.create_slider("G", self.g_var)
        self.create_slider("B", self.b_var)

        # ---------- PALETTE ----------
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
    def make_btn(self, text, cmd):
        b = tk.Label(self.card, text=text, bg="#1f1f1f", fg="white",
                     padx=10, pady=6, cursor="hand2")
        b.pack(fill="x", pady=2)

        b.bind("<Enter>", lambda e: b.config(bg=ACCENT))
        b.bind("<Leave>", lambda e: b.config(bg="#1f1f1f"))
        b.bind("<Button-1>", lambda e: cmd())

    # -------------------------
    def create_slider(self, label, var):
        row = tk.Frame(self.slider_frame, bg=self.bg)
        row.pack(fill="x", pady=2)

        tk.Label(row, text=label, width=2, fg=self.fg, bg=self.bg).pack(side="left")

        tk.Scale(
            row,
            from_=0,
            to=255,
            orient="horizontal",
            variable=var,
            showvalue=0,
            command=lambda e: self.update_from_sliders(),
            highlightthickness=0,
            bd=0,
            troughcolor="#2b2b2b",
            bg=self.bg,
            fg=self.fg
        ).pack(side="left", fill="x", expand=True)

    def update_from_sliders(self):
        self.update_color(
            self.r_var.get(),
            self.g_var.get(),
            self.b_var.get()
        )

    # -------------------------
    def update_color(self, r, g, b):
        self.r, self.g, self.b = r, g, b
        self.hex = f"#{r:02x}{g:02x}{b:02x}".upper()

        self.r_var.set(r)
        self.g_var.set(g)
        self.b_var.set(b)

        self.color_display.config(bg=self.hex)
        self.hex_entry.delete(0, tk.END)
        self.hex_entry.insert(0, self.hex)

    def copy_hex(self):
        pyperclip.copy(self.hex)

    def copy_rgb(self):
        pyperclip.copy(f"rgb({self.r},{self.g},{self.b})")

    # -------------------------
    # PICKER
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

            self.overlay.bind("<Button-1>", self.pick)
            self.overlay.bind("<MouseWheel>", self.scroll)

            self.update_preview()

        except Exception as e:
            print("Picker error:", e)
            self.root.deiconify()

    def scroll(self, e):
        self.zoom = max(2, min(20, self.zoom - 1 if e.delta > 0 else self.zoom + 1))

    def update_preview(self):
        try:
            if not hasattr(self, "overlay"):
                return

            x, y = self.mouse.position
            z = self.zoom

            with mss.mss() as sct:
                monitor = {"left": x - z, "top": y - z, "width": z*2, "height": z*2}
                img = sct.grab(monitor)

            image = Image.frombytes("RGB", img.size, img.rgb)
            image = image.resize((ZOOM_SIZE, ZOOM_SIZE), Image.NEAREST)

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

        except Exception as e:
            print("Preview error:", e)

    def pick(self, e):
        self.add_palette(self.hex)
        self.cleanup()

    def cleanup(self):
        try:
            if hasattr(self, "overlay"):
                self.overlay.destroy()
            if hasattr(self, "zoom_win"):
                self.zoom_win.destroy()
        except:
            pass

        self.root.deiconify()

    # -------------------------
    # PALETTE
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
        try:
            if not self.history:
                print("No colors to save")
                return

            img = Image.new("RGB", (50 * len(self.history), 50))
            draw = ImageDraw.Draw(img)

            for i, c in enumerate(self.history):
                draw.rectangle([i*50, 0, (i+1)*50, 50], fill=c)

            img.save("palette.png")
            print("Saved palette.png")

        except Exception as e:
            print("Save error:", e)

    def export_css(self):
        try:
            if not self.history:
                print("No colors to export")
                return

            with open("palette.css", "w") as f:
                for i, c in enumerate(self.history):
                    f.write(f"--color{i}: {c};\n")

            print("Exported palette.css")

        except Exception as e:
            print("Export error:", e)

    # -------------------------
    # SETTINGS
    # -------------------------
    def open_settings(self):
        win = tk.Toplevel(self.root)

        dark = tk.IntVar(value=self.config.get("dark_mode", True))

        tk.Checkbutton(win, text="Dark Mode", variable=dark).pack(anchor="w")

        def save():
            self.config["dark_mode"] = bool(dark.get())
            save_config(self.config)
            self.apply_theme()
            win.destroy()

        tk.Button(win, text="Save", command=save).pack(pady=10)


# -------------------------
# SAFE START
# -------------------------
if __name__ == "__main__":
    try:
        root = tk.Tk()
        root.title("Katia Color Picker PRO")
        app = ColorPicker(root)
        root.mainloop()
    except Exception as e:
        with open("error_log.txt", "w") as f:
            f.write(str(e))