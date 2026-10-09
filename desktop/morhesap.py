#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MorHesap — bilimsel hesap makinesi + ağırlıklı not ortalaması hesaplayıcı.

Çalıştırmak için:  python morhesap.py
Ek kütüphane gerekmez (yalnızca Python 3.8+ ile gelen tkinter kullanılır).
"""
import math
import sys
import tkinter as tk
import tkinter.font as tkfont

# ───────────────────────────── Tema (siyah + mor) ─────────────────────────────
BG = "#09070f"          # ana arka plan
SURFACE = "#14101f"     # kartlar
SURFACE2 = "#1d1730"    # sayı tuşları / giriş kutuları
SURFACE3 = "#2a2046"    # işlem tuşları
HOVER = "#33275a"
ACCENT = "#8b5cf6"      # ana mor
ACCENT_HI = "#a78bfa"
ACCENT_SOFT = "#c4b5fd"
PINK = "#e879f9"
TEXT = "#f3f0ff"
MUTED = "#8f86ad"
FAINT = "#5b5378"
GOOD = "#a3e635"
BAD = "#fb7185"
WARN = "#fbbf24"


# ───────────────────────────── Hesaplama motoru ─────────────────────────────
class CalcError(Exception):
    pass


FUNCS = ["asin", "acos", "atan", "sqrt", "sin", "cos", "tan", "abs", "log", "ln"]
CONSTS = {"pi": math.pi, "π": math.pi, "e": math.e}


def tokenize(s):
    s = (s.replace("sin⁻¹", "asin").replace("cos⁻¹", "acos").replace("tan⁻¹", "atan")
          .replace("×", "*").replace("÷", "/").replace("−", "-").replace("√", "sqrt")
          .replace(" ", ""))
    out, i, n = [], 0, len(s)
    while i < n:
        ch = s[i]
        if ch.isdigit() or ch in ".,":
            j = i
            while j < n and (s[j].isdigit() or s[j] in ".,"):
                j += 1
            txt = s[i:j].replace(",", ".")
            if txt.count(".") > 1 or txt == ".":
                raise CalcError("Hata")
            out.append(("num", float(txt)))
            i = j
            continue
        if ch in "+-*/^()!%":
            out.append((ch, ch))
            i += 1
            continue
        for name in FUNCS:
            if s.startswith(name, i):
                out.append(("func", name))
                i += len(name)
                break
        else:
            for name, val in CONSTS.items():
                if s.startswith(name, i):
                    out.append(("num", val))
                    i += len(name)
                    break
            else:
                raise CalcError("Hata")
    return out


class Parser:
    """Özyinelemeli iniş ayrıştırıcısı — eval() kullanılmaz."""

    def __init__(self, tokens, degrees=True):
        self.t, self.i, self.deg = tokens, 0, degrees

    def peek(self):
        return self.t[self.i][0] if self.i < len(self.t) else None

    def take(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def parse(self):
        if not self.t:
            raise CalcError("Hata")
        v = self.expr()
        if self.i != len(self.t):
            raise CalcError("Hata")
        return v

    def expr(self):
        v = self.term()
        while self.peek() in ("+", "-"):
            if self.take()[0] == "+":
                v += self.term()
            else:
                v -= self.term()
        return v

    def term(self):
        v = self.unary()
        while True:
            p = self.peek()
            if p == "*":
                self.take()
                v *= self.unary()
            elif p == "/":
                self.take()
                d = self.unary()
                if d == 0:
                    raise CalcError("Sıfıra bölünemez")
                v /= d
            elif p in ("num", "func", "("):      # örtük çarpma: 2π, 3(4+1), 2sin(30)
                v *= self.power()
            else:
                return v

    def unary(self):
        p = self.peek()
        if p == "-":
            self.take()
            return -self.unary()
        if p == "+":
            self.take()
            return self.unary()
        return self.power()

    def power(self):
        base = self.postfix()
        if self.peek() == "^":
            self.take()
            exp = self.unary()
            try:
                return math.pow(base, exp)
            except OverflowError:
                raise CalcError("Sonuç çok büyük")
            except (ValueError, ZeroDivisionError):
                raise CalcError("Tanımsız")
        return base

    def postfix(self):
        v = self.primary()
        while self.peek() in ("!", "%"):
            if self.take()[0] == "%":
                v /= 100.0
            else:
                if v < 0 or abs(v - round(v)) > 1e-9:
                    raise CalcError("Tanımsız")
                if v > 170:
                    raise CalcError("Sonuç çok büyük")
                v = float(math.factorial(int(round(v))))
        return v

    def primary(self):
        p = self.peek()
        if p == "num":
            return self.take()[1]
        if p == "(":
            self.take()
            v = self.expr()
            if self.peek() == ")":
                self.take()
            elif self.peek() is not None:
                raise CalcError("Hata")
            return v                      # eksik ")" sonda otomatik kapanır
        if p == "func":
            name = self.take()[1]
            if self.peek() != "(":
                raise CalcError("Hata")
            return self.call(name, self.primary())
        raise CalcError("Hata")

    def call(self, name, x):
        try:
            if name in ("sin", "cos", "tan"):
                r = math.radians(x) if self.deg else x
                if name == "sin":
                    return math.sin(r)
                if name == "cos":
                    return math.cos(r)
                if abs(math.cos(r)) < 1e-12:
                    raise CalcError("Tanımsız")
                return math.tan(r)
            if name in ("asin", "acos", "atan"):
                r = {"asin": math.asin, "acos": math.acos, "atan": math.atan}[name](x)
                return math.degrees(r) if self.deg else r
            if name == "sqrt":
                return math.sqrt(x)
            if name == "abs":
                return abs(x)
            if name == "log":
                return math.log10(x)
            if name == "ln":
                return math.log(x)
        except ValueError:
            raise CalcError("Tanımsız")
        raise CalcError("Hata")


def evaluate(expr, degrees=True):
    v = Parser(tokenize(expr), degrees).parse()
    if isinstance(v, complex) or math.isnan(v):
        raise CalcError("Tanımsız")
    if math.isinf(v):
        raise CalcError("Sonuç çok büyük")
    return v


def fmt(v):
    """Sonucu okunaklı biçimde yaz (kayan nokta kirini temizler)."""
    if abs(v) < 1e-12:
        return "0"
    v = float("%.12g" % v)
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    s = "%.10g" % v
    if "e" in s:
        mant, exp = s.split("e")
        return "%s×10^%d" % (mant, int(exp))
    return s


def fmt_grade(v):
    s = "%.2f" % v
    return s.rstrip("0").rstrip(".") if "." in s else s


# ───────────────────────────── Arayüz parçaları ─────────────────────────────
def rrect(c, x1, y1, x2, y2, r, **kw):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


class RoundButton(tk.Canvas):
    def __init__(self, parent, text, command, bg=SURFACE2, fg=TEXT, hover=HOVER,
                 font=None, radius=18, parent_bg=BG, width=60, height=48):
        super().__init__(parent, bg=parent_bg, highlightthickness=0, bd=0,
                         width=width, height=height, cursor="hand2")
        self.text, self.command = text, command
        self.c_bg, self.c_fg, self.c_hover = bg, fg, hover
        self.font, self.radius = font, radius
        self._state = "normal"
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Enter>", lambda e: self._set("hover"))
        self.bind("<Leave>", lambda e: self._set("normal"))
        self.bind("<ButtonPress-1>", lambda e: self._set("down"))
        self.bind("<ButtonRelease-1>", self._release)

    def configure_look(self, text=None, bg=None, fg=None):
        if text is not None:
            self.text = text
        if bg is not None:
            self.c_bg = bg
        if fg is not None:
            self.c_fg = fg
        self.draw()

    def _set(self, state):
        self._state = state
        self.draw()

    def _release(self, e):
        inside = 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height()
        self._set("hover" if inside else "normal")
        if inside and self.command:
            self.command()

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        fill = self.c_bg if self._state == "normal" else self.c_hover
        if self.c_bg == ACCENT and self._state != "normal":
            fill = ACCENT_HI
        inset = 2 if self._state == "down" else 0
        rrect(self, 1 + inset, 1 + inset, w - 1 - inset, h - 1 - inset, self.radius, fill=fill)
        self.create_text(w / 2, h / 2, text=self.text, fill=self.c_fg, font=self.font)


class Card(tk.Canvas):
    """Yuvarlak köşeli kart; içerik self.body içine yerleştirilir."""

    def __init__(self, parent, fill=SURFACE, pad=16, radius=22, parent_bg=BG):
        super().__init__(parent, bg=parent_bg, highlightthickness=0, bd=0, height=10)
        self.fill, self.pad, self.radius = fill, pad, radius
        self.body = tk.Frame(self, bg=fill)
        self.win = self.create_window(pad, pad, window=self.body, anchor="nw")
        self.bind("<Configure>", self._layout)
        self.body.bind("<Configure>", self._fit)

    def _fit(self, _e=None):
        self.after_idle(self.fit)

    def _layout(self, _e=None):
        w, h = self.winfo_width(), self.winfo_height()
        self.delete("bg")
        rrect(self, 0, 0, w, h, self.radius, fill=self.fill, tags="bg")
        self.tag_lower("bg")
        self.itemconfigure(self.win, width=max(10, w - 2 * self.pad))
        self.after_idle(self.fit)

    def fit(self):
        """Kart yüksekliğini içeriğe göre ayarla."""
        try:
            self.body.update_idletasks()
            want = self.body.winfo_reqheight() + 2 * self.pad
            if int(self.cget("height")) != want:
                self.configure(height=want)
        except tk.TclError:
            pass


# ───────────────────────────── Uygulama ─────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MorHesap")
        self.configure(bg=BG)
        self.geometry("420x760")
        self.minsize(380, 700)

        fams = set(tkfont.families(self))
        self.fam = next((f for f in ("Segoe UI", "Inter", "SF Pro Display", "Helvetica Neue",
                                     "Noto Sans", "DejaVu Sans") if f in fams), "TkDefaultFont")
        self.F = lambda size, weight="normal": (self.fam, size, weight)

        self.expr = ""
        self.history = ""
        self.just_evaluated = False
        self.degrees = True
        self.second = False
        self.rows = []
        self.cards = []
        self.current = None

        # alt sekme çubuğu
        self.tabbar = tk.Canvas(self, bg=SURFACE, height=68, highlightthickness=0, bd=0)
        self.tabbar.pack(side="bottom", fill="x")
        self.tabbar.bind("<Configure>", lambda e: self.draw_tabs())
        self.tabbar.bind("<Button-1>", self.on_tab_click)

        self.pages = {"calc": tk.Frame(self, bg=BG), "grade": tk.Frame(self, bg=BG)}
        self.build_calc(self.pages["calc"])
        self.build_grade(self.pages["grade"])
        self.show("calc")

        self.bind("<Key>", self.on_key)
        self.after(50, self.dark_titlebar)

    # ── pencere başlığını koyu yap (yalnızca Windows 10/11) ──
    def dark_titlebar(self):
        if not sys.platform.startswith("win"):
            return
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            val = ctypes.c_int(1)
            for attr in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val),
                                                           ctypes.sizeof(val))
        except Exception:
            pass

    # ── sekmeler ──
    def show(self, name):
        if self.current == name:
            return
        for p in self.pages.values():
            p.pack_forget()
        self.pages[name].pack(side="top", fill="both", expand=True)
        self.current = name
        self.focus_set()
        self.draw_tabs()

    def on_tab_click(self, e):
        self.show("calc" if e.x < self.tabbar.winfo_width() / 2 else "grade")

    def draw_tabs(self):
        c = self.tabbar
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        c.create_line(0, 0, w, 0, fill=SURFACE3)
        for idx, (name, label) in enumerate((("calc", "Hesap Makinesi"), ("grade", "Not Ortalaması"))):
            cx = w * (0.25 + 0.5 * idx)
            active = self.current == name
            col = ACCENT_SOFT if active else FAINT
            if active:
                rrect(c, cx - 34, 8, cx + 34, 38, 15, fill=SURFACE3)
            if name == "calc":          # küçük hesap makinesi simgesi
                rrect(c, cx - 8, 13, cx + 8, 33, 4, fill="", outline=col, width=2)
                c.create_line(cx - 4, 18, cx + 4, 18, fill=col, width=2)
                for dx in (-4, 0, 4):
                    for dy in (23, 28):
                        c.create_rectangle(cx + dx - 1, dy - 1, cx + dx + 1, dy + 1, fill=col, outline=col)
            else:                       # küçük çubuk grafik simgesi
                for dx, top in ((-8, 26), (-2, 20), (4, 14)):
                    c.create_rectangle(cx + dx, top, cx + dx + 4, 32, fill=col, outline=col)
            c.create_text(cx, 52, text=label, fill=TEXT if active else MUTED,
                          font=self.F(9, "bold" if active else "normal"))

    # ═════════════════════════ Hesap makinesi ═════════════════════════
    def build_calc(self, page):
        disp = Card(page, pad=18)
        disp.pack(side="top", fill="x", padx=14, pady=(14, 6))
        b = disp.body
        top = tk.Frame(b, bg=SURFACE)
        top.pack(fill="x")
        self.mode_lbl = tk.Label(top, text="DEG", bg=SURFACE3, fg=ACCENT_SOFT, font=self.F(8, "bold"),
                                 padx=8, pady=2)
        self.mode_lbl.pack(side="left")
        self.hist_lbl = tk.Label(top, text="", bg=SURFACE, fg=MUTED, font=self.F(11), anchor="e")
        self.hist_lbl.pack(side="right", fill="x", expand=True)
        self.expr_lbl = tk.Label(b, text="0", bg=SURFACE, fg=TEXT, font=self.F(34, "bold"), anchor="e",
                                 height=1)
        self.expr_lbl.pack(fill="x", pady=(18, 0))
        self.prev_lbl = tk.Label(b, text=" ", bg=SURFACE, fg=ACCENT_HI, font=self.F(14), anchor="e")
        self.prev_lbl.pack(fill="x", pady=(2, 0))

        grid = tk.Frame(page, bg=BG)
        grid.pack(side="top", fill="both", expand=True, padx=10, pady=(4, 10))
        for col in range(5):
            grid.columnconfigure(col, weight=1, uniform="k")
        layout = [
            ["2nd", "mode", "sin", "cos", "tan"],
            ["xʸ", "log", "ln", "(", ")"],
            ["√", "AC", "⌫", "%", "÷"],
            ["x!", "7", "8", "9", "×"],
            ["1/x", "4", "5", "6", "−"],
            ["π", "1", "2", "3", "+"],
            ["|x|", "e", "0", ".", "="],
        ]
        self.keys = {}
        for r, row in enumerate(layout):
            grid.rowconfigure(r, weight=1, uniform="k")
            for col, key in enumerate(row):
                if key.isdigit() or key == ".":
                    bg, fg, font = SURFACE2, TEXT, self.F(17, "bold")
                elif key == "=":
                    bg, fg, font = ACCENT, "#ffffff", self.F(20, "bold")
                elif key in "÷×−+":
                    bg, fg, font = SURFACE3, ACCENT_SOFT, self.F(19, "bold")
                elif key in ("AC", "⌫"):
                    bg, fg, font = SURFACE3, PINK, self.F(14, "bold")
                else:
                    bg, fg, font = SURFACE, ACCENT_HI, self.F(12, "bold")
                btn = RoundButton(grid, "DEG" if key == "mode" else key,
                                  lambda k=key: self.press(k), bg=bg, fg=fg, font=font)
                btn.grid(row=r, column=col, sticky="nsew", padx=4, pady=4)
                self.keys[key] = btn

    SECOND = {"sin": "sin⁻¹", "cos": "cos⁻¹", "tan": "tan⁻¹", "log": "10ˣ", "ln": "eˣ", "√": "x²"}
    INSERT = {"sin": "sin(", "cos": "cos(", "tan": "tan(", "log": "log(", "ln": "ln(", "√": "√(",
              "sin⁻¹": "sin⁻¹(", "cos⁻¹": "cos⁻¹(", "tan⁻¹": "tan⁻¹(", "10ˣ": "10^(", "eˣ": "e^(",
              "x²": "^2", "xʸ": "^", "x!": "!", "1/x": "^(-1)", "|x|": "abs(", "π": "π", "e": "e"}
    CHUNKS = ["sin⁻¹(", "cos⁻¹(", "tan⁻¹(", "sin(", "cos(", "tan(", "log(", "abs(", "ln(", "√("]

    def press(self, key):
        if key == "2nd":
            self.second = not self.second
            self.keys["2nd"].configure_look(bg=ACCENT if self.second else SURFACE,
                                            fg="#ffffff" if self.second else ACCENT_HI)
            for k, alt in self.SECOND.items():
                self.keys[k].configure_look(text=alt if self.second else k)
            return
        if key == "mode":
            self.degrees = not self.degrees
            name = "DEG" if self.degrees else "RAD"
            self.keys["mode"].configure_look(text=name)
            self.mode_lbl.configure(text=name)
            self.refresh()
            return
        if key == "AC":
            self.expr, self.history, self.just_evaluated = "", "", False
        elif key == "⌫":
            if self.just_evaluated:
                self.expr, self.just_evaluated = "", False
            else:
                for ch in self.CHUNKS:
                    if self.expr.endswith(ch):
                        self.expr = self.expr[:-len(ch)]
                        break
                else:
                    self.expr = self.expr[:-1]
        elif key == "=":
            self.equals()
            return
        else:
            if self.second and key in self.SECOND:
                key = self.SECOND[key]
            text = self.INSERT.get(key, key)
            continues = text[0] in "+−×÷^!%"
            if self.just_evaluated and not continues:
                self.expr = ""              # yeni sayı/fonksiyon → yeni işlem
            self.just_evaluated = False
            self.expr += text
        self.refresh()

    def equals(self):
        if not self.expr:
            return
        try:
            res = fmt(evaluate(self.expr, self.degrees))
        except CalcError as e:
            self.prev_lbl.configure(text=str(e), fg=BAD)
            return
        except Exception:
            self.prev_lbl.configure(text="Hata", fg=BAD)
            return
        self.history = self.expr + " ="
        self.expr = res.replace("-", "−")
        self.just_evaluated = True
        self.refresh()

    def refresh(self):
        shown = self.expr or "0"
        size = 34 if len(shown) <= 11 else 26 if len(shown) <= 15 else 19 if len(shown) <= 21 else 15
        if len(shown) > 28:
            shown = "…" + shown[-27:]
        self.expr_lbl.configure(text=shown, font=self.F(size, "bold"))
        hist = self.history if len(self.history) <= 30 else "…" + self.history[-29:]
        self.hist_lbl.configure(text=hist)
        preview = " "
        if self.expr and not self.just_evaluated:
            try:
                res = fmt(evaluate(self.expr, self.degrees)).replace("-", "−")
                if res != self.expr:
                    preview = "= " + res
            except Exception:
                pass
        self.prev_lbl.configure(text=preview, fg=ACCENT_HI)

    def on_key(self, e):
        if self.current != "calc" or isinstance(self.focus_get(), tk.Entry):
            return
        ks, ch = e.keysym, e.char
        table = {"Return": "=", "KP_Enter": "=", "BackSpace": "⌫", "Escape": "AC", "Delete": "AC"}
        chars = {"*": "×", "/": "÷", "-": "−", "+": "+", "=": "=", ",": ".", ".": ".", "(": "(",
                 ")": ")", "%": "%", "^": "xʸ", "!": "x!", "p": "π", "e": "e"}
        if ks in table:
            self.press(table[ks])
        elif ch and ch.isdigit():
            self.press(ch)
        elif ch in chars:
            key = chars[ch]
            if key == "xʸ" or key == "x!":      # 2nd açıkken de doğru karakteri ekle
                self.just_evaluated = False
                self.expr += self.INSERT[key]
                self.refresh()
            else:
                self.press(key)

    # ═════════════════════════ Not ortalaması ═════════════════════════
    def build_grade(self, page):
        head = tk.Frame(page, bg=BG)
        head.pack(fill="x", padx=18, pady=(18, 8))
        tk.Label(head, text="Not Ortalaması", bg=BG, fg=TEXT, font=self.F(20, "bold")).pack(anchor="w")
        tk.Label(head, text="Sınav notlarını ve ağırlıklarını gir, ortalaman anında hesaplansın.",
                 bg=BG, fg=MUTED, font=self.F(10), wraplength=370, justify="left").pack(anchor="w")

        # sonuç kartı
        res = Card(page, pad=18)
        res.pack(fill="x", padx=14, pady=6)
        self.cards.append(res)
        rb = res.body
        row = tk.Frame(rb, bg=SURFACE)
        row.pack(fill="x")
        left = tk.Frame(row, bg=SURFACE)
        left.pack(side="left")
        tk.Label(left, text="AĞIRLIKLI ORTALAMA", bg=SURFACE, fg=MUTED, font=self.F(8, "bold")).pack(anchor="w")
        self.avg_lbl = tk.Label(left, text="—", bg=SURFACE, fg=TEXT, font=self.F(38, "bold"))
        self.avg_lbl.pack(anchor="w")
        right = tk.Frame(row, bg=SURFACE)
        right.pack(side="right", anchor="n")
        tk.Label(right, text="GEÇME NOTU", bg=SURFACE, fg=MUTED, font=self.F(8, "bold")).pack(anchor="e")
        self.pass_var = tk.StringVar(value="50")
        self.entry(right, self.pass_var, width=5, justify="center").pack(anchor="e", pady=(6, 0), ipady=5)
        self.status_lbl = tk.Label(rb, text="", bg=SURFACE, fg=MUTED, font=self.F(11, "bold"),
                                   anchor="nw", justify="left", wraplength=340, height=2)
        self.status_lbl.pack(fill="x", pady=(4, 10))
        self.bar = tk.Canvas(rb, bg=SURFACE, height=8, highlightthickness=0, bd=0)
        self.bar.pack(fill="x")
        self.bar.bind("<Configure>", lambda e: self.recalc())
        self.weight_lbl = tk.Label(rb, text="", bg=SURFACE, fg=MUTED, font=self.F(9), anchor="w")
        self.weight_lbl.pack(fill="x", pady=(6, 0))

        # sınav satırları
        card = Card(page, pad=14)
        card.pack(fill="x", padx=14, pady=6)
        self.cards.append(card)
        cb = card.body
        hdr = tk.Frame(cb, bg=SURFACE)
        hdr.pack(fill="x", pady=(0, 4))
        self.cols(hdr)
        for col, txt in enumerate(("SINAV", "NOT", "AĞIRLIK %")):
            tk.Label(hdr, text=txt, bg=SURFACE, fg=MUTED, font=self.F(8, "bold"),
                     anchor="w").grid(row=0, column=col, sticky="w", padx=4)
        self.rows_box = tk.Frame(cb, bg=SURFACE)
        self.rows_box.pack(fill="x")

        btns = tk.Frame(page, bg=BG)
        btns.pack(fill="x", padx=14, pady=6)
        btns.columnconfigure(0, weight=3, uniform="b")
        btns.columnconfigure(1, weight=2, uniform="b")
        RoundButton(btns, "+  Sınav ekle", self.add_row, bg=ACCENT, fg="#ffffff",
                    font=self.F(11, "bold"), radius=16, height=46).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        RoundButton(btns, "Temizle", self.clear_rows, bg=SURFACE3, fg=PINK,
                    font=self.F(11, "bold"), radius=16, height=46).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.pass_var.trace_add("write", lambda *a: self.recalc())
        self.add_row("Vize", "", "40")
        self.add_row("Final", "", "60")

    @staticmethod
    def cols(frame):
        frame.columnconfigure(0, weight=5, uniform="c")
        frame.columnconfigure(1, weight=3, uniform="c")
        frame.columnconfigure(2, weight=3, uniform="c")
        frame.columnconfigure(3, minsize=34)

    def entry(self, parent, var, width=6, justify="left"):
        return tk.Entry(parent, textvariable=var, width=width, justify=justify, bg=SURFACE2, fg=TEXT,
                        insertbackground=ACCENT_SOFT, relief="flat", bd=0, font=self.F(13),
                        highlightthickness=2, highlightbackground=SURFACE2, highlightcolor=ACCENT,
                        selectbackground=ACCENT, selectforeground="#ffffff")

    MAX_ROWS = 6

    def add_row(self, name=None, grade="", weight=""):
        if len(self.rows) >= self.MAX_ROWS:
            return
        if name is None:
            name = "Sınav %d" % (len(self.rows) + 1)
        fr = tk.Frame(self.rows_box, bg=SURFACE)
        fr.pack(fill="x", pady=3)
        self.cols(fr)
        row = {"frame": fr, "name": tk.StringVar(value=name), "grade": tk.StringVar(value=grade),
               "weight": tk.StringVar(value=weight)}
        self.entry(fr, row["name"]).grid(row=0, column=0, sticky="ew", padx=3, ipady=6)
        self.entry(fr, row["grade"], justify="center").grid(row=0, column=1, sticky="ew", padx=3, ipady=6)
        self.entry(fr, row["weight"], justify="center").grid(row=0, column=2, sticky="ew", padx=3, ipady=6)
        RoundButton(fr, "✕", lambda r=row: self.del_row(r), bg=SURFACE, fg=FAINT, hover=SURFACE3,
                    font=self.F(10, "bold"), radius=10, parent_bg=SURFACE, width=30,
                    height=30).grid(row=0, column=3, padx=(2, 0))
        for k in ("name", "grade", "weight"):
            row[k].trace_add("write", lambda *a: self.recalc())
        self.rows.append(row)
        self.recalc()

    def del_row(self, row):
        if len(self.rows) <= 1:
            return
        row["frame"].destroy()
        self.rows.remove(row)
        self.recalc()

    def clear_rows(self):
        for r in self.rows:
            r["grade"].set("")
        self.recalc()

    @staticmethod
    def num(text):
        text = text.strip().replace(",", ".").replace("%", "")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return "bad"

    def recalc(self):
        if not hasattr(self, "weight_lbl"):
            return
        self._recalc()
        for card in self.cards:
            card.after_idle(card.fit)

    def _recalc(self):
        target = self.num(self.pass_var.get())
        if target in (None, "bad"):
            target = 50.0
        data, bad = [], None
        for r in self.rows:
            g, w = self.num(r["grade"].get()), self.num(r["weight"].get())
            name = r["name"].get().strip() or "Sınav"
            if g == "bad" or w == "bad":
                bad = "“%s” satırında geçersiz değer var." % name
            elif g is not None and not 0 <= g <= 100:
                bad = "“%s” notu 0 ile 100 arasında olmalı." % name
            elif w is not None and w < 0:
                bad = "“%s” ağırlığı negatif olamaz." % name
            data.append((name, g, w or 0.0))

        total = sum(w for _, _, w in data if isinstance(w, float))
        # ağırlık çubuğu
        self.bar.delete("all")
        bw = self.bar.winfo_width()
        rrect(self.bar, 0, 0, bw, 8, 4, fill=SURFACE2)
        ok100 = abs(total - 100) < 1e-9
        if total > 0:
            rrect(self.bar, 0, 0, max(8, bw * min(total, 100) / 100), 8, 4,
                  fill=ACCENT if ok100 else WARN)
        self.weight_lbl.configure(
            text="Ağırlık toplamı: %%%s" % fmt_grade(total) + ("" if ok100 else "  —  %100 olmalı"),
            fg=MUTED if ok100 else WARN)

        def out(avg, msg, color, avg_color=TEXT):
            self.avg_lbl.configure(text=avg, fg=avg_color)
            self.status_lbl.configure(text=msg, fg=color)

        if bad:
            return out("—", bad, BAD)
        if total <= 0:
            return out("—", "Ağırlıkları gir.", MUTED)
        filled = [(n, g, w) for n, g, w in data if g is not None and w > 0]
        empty = [(n, g, w) for n, g, w in data if g is None and w > 0]
        if not filled:
            return out("—", "Notlarını gir, ortalaman burada görünsün.", MUTED)
        earned = sum(g * w for _, g, w in filled) / 100.0
        if not ok100:
            avg = sum(g * w for _, g, w in filled) / sum(w for _, _, w in filled)
            return out(fmt_grade(avg), "Ağırlıklar %100 etmiyor; girilen ağırlıklara oranlanmış "
                       "ortalama gösteriliyor.", WARN)
        if not empty:
            passed = earned >= target - 1e-9
            return out(fmt_grade(earned), "Geçtin  ✓" if passed else
                       "Kaldın — geçme notuna %s puan eksik." % fmt_grade(target - earned),
                       GOOD if passed else BAD, GOOD if passed else BAD)
        if len(empty) == 1:
            n, _, w = empty[0]
            need = (target - earned) / (w / 100.0)
            if need <= 0:
                msg, col = "%s sınavından 0 alsan bile geçiyorsun." % n, GOOD
            elif need > 100:
                msg, col = "%s sınavından 100 alsan bile geçme notuna ulaşılamıyor." % n, BAD
            else:
                msg, col = "Geçmek için %s sınavından en az %s almalısın." % (n, fmt_grade(need)), ACCENT_SOFT
            return out(fmt_grade(earned), "Şu ana kadar toplanan puan.  " + msg, col)
        return out(fmt_grade(earned), "Şu ana kadar toplanan puan. Kalan %d sınavın notunu gir."
                   % len(empty), MUTED)


if __name__ == "__main__":
    App().mainloop()
