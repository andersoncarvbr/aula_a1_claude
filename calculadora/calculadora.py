import customtkinter as ctk
import math
from tkinter import StringVar

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DISPLAY_FONT = ("SF Pro Display", 42, "bold")
EXPR_FONT    = ("SF Pro Display", 14)
BTN_FONT     = ("SF Pro Display", 20)
BTN_FONT_SM  = ("SF Pro Display", 16)

COLORS = {
    "bg":        "#1C1C1E",
    "display":   "#2C2C2E",
    "num":       "#3A3A3C",
    "num_hover": "#48484A",
    "op":        "#FF9F0A",
    "op_hover":  "#FFB340",
    "fn":        "#636366",
    "fn_hover":  "#7C7C80",
    "eq":        "#FF9F0A",
    "eq_hover":  "#FFB340",
    "text":      "#FFFFFF",
    "text_dim":  "#8E8E93",
    "accent":    "#0A84FF",
}


class Calculadora(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Calculadora")
        self.geometry("380x620")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg"])

        self._expression = ""
        self._result_shown = False
        self._history = []

        self._current_var = StringVar(value="0")
        self._expr_var    = StringVar(value="")

        self._build_ui()
        self.bind("<Key>", self._on_key)

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        self._build_display()
        self._build_buttons()

    def _build_display(self):
        frame = ctk.CTkFrame(self, fg_color=COLORS["display"],
                             corner_radius=20)
        frame.grid(row=0, column=0, padx=16, pady=(20, 8), sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, textvariable=self._expr_var,
            font=EXPR_FONT, text_color=COLORS["text_dim"],
            anchor="e", wraplength=330,
        ).grid(row=0, column=0, padx=20, pady=(14, 0), sticky="e")

        ctk.CTkLabel(
            frame, textvariable=self._current_var,
            font=DISPLAY_FONT, text_color=COLORS["text"],
            anchor="e", wraplength=330,
        ).grid(row=1, column=0, padx=20, pady=(4, 18), sticky="e")

    def _build_buttons(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=1, column=0, padx=16, pady=(0, 20), sticky="nsew")

        for c in range(4):
            frame.grid_columnconfigure(c, weight=1, uniform="col")
        for r in range(5):
            frame.grid_rowconfigure(r, weight=1, uniform="row")

        layout = [
            # (label, col, row, colspan, type)
            ("AC",  0, 0, 1, "fn"),
            ("+/-", 1, 0, 1, "fn"),
            ("%",   2, 0, 1, "fn"),
            ("÷",   3, 0, 1, "op"),

            ("7",   0, 1, 1, "num"),
            ("8",   1, 1, 1, "num"),
            ("9",   2, 1, 1, "num"),
            ("×",   3, 1, 1, "op"),

            ("4",   0, 2, 1, "num"),
            ("5",   1, 2, 1, "num"),
            ("6",   2, 2, 1, "num"),
            ("−",   3, 2, 1, "op"),

            ("1",   0, 3, 1, "num"),
            ("2",   1, 3, 1, "num"),
            ("3",   2, 3, 1, "num"),
            ("+",   3, 3, 1, "op"),

            ("0",   0, 4, 2, "num"),  # colspan=2
            (".",   2, 4, 1, "num"),
            ("=",   3, 4, 1, "eq"),
        ]

        GAP = 10
        for (label, col, row, span, kind) in layout:
            self._make_button(frame, label, col, row, span, kind, GAP)

    def _make_button(self, parent, label, col, row, span, kind, gap):
        colors = {
            "num": (COLORS["num"],    COLORS["num_hover"]),
            "fn":  (COLORS["fn"],     COLORS["fn_hover"]),
            "op":  (COLORS["op"],     COLORS["op_hover"]),
            "eq":  (COLORS["eq"],     COLORS["eq_hover"]),
        }
        fg, hover = colors[kind]
        txt_color = COLORS["bg"] if kind in ("op", "eq") else COLORS["text"]
        font = BTN_FONT_SM if label in ("+/-", "%") else BTN_FONT

        btn = ctk.CTkButton(
            parent,
            text=label,
            font=font,
            fg_color=fg,
            hover_color=hover,
            text_color=txt_color,
            corner_radius=50,
            border_width=0,
            command=lambda l=label: self._on_button(l),
        )
        btn.grid(
            row=row, column=col, columnspan=span,
            padx=(gap // 2, gap // 2),
            pady=(gap // 2, gap // 2),
            sticky="nsew",
            ipadx=0, ipady=14,
        )

    # ── Logic ────────────────────────────────────────────────────────────────

    def _on_button(self, label: str):
        actions = {
            "AC":  self._clear,
            "+/-": self._toggle_sign,
            "%":   self._percent,
            "=":   self._evaluate,
            ".":   self._dot,
            "÷":   lambda: self._operator("/"),
            "×":   lambda: self._operator("*"),
            "−":   lambda: self._operator("-"),
            "+":   lambda: self._operator("+"),
        }
        if label in actions:
            actions[label]()
        else:
            self._digit(label)

    def _digit(self, d: str):
        if self._result_shown:
            self._expression = ""
            self._result_shown = False

        current = self._current_var.get()
        if current == "0" and d != ".":
            current = d
        else:
            if len(current) >= 12:
                return
            current += d

        self._current_var.set(current)

    def _operator(self, op: str):
        self._flush_current()
        display_op = {"*": "×", "/": "÷", "-": "−", "+": "+"}.get(op, op)

        if self._expression and self._expression[-1] in "+-*/":
            self._expression = self._expression[:-1]
            self._expr_var.set(self._expr_var.get()[:-2] + f" {display_op}")

        self._expression += op
        self._expr_var.set(self._expr_var.get() + f" {display_op}")
        self._current_var.set("0")
        self._result_shown = False

    def _flush_current(self):
        val = self._current_var.get().replace(",", ".")
        self._expression += val
        self._expr_var.set(self._expr_var.get() + val)

    def _evaluate(self):
        self._flush_current()
        expr = self._expression
        display_expr = self._expr_var.get()

        try:
            result = eval(expr)  # noqa: S307 — input is calculator-only
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            formatted = self._fmt(result)
            self._history.append(f"{display_expr} = {formatted}")
            self._current_var.set(formatted)
            self._expr_var.set(display_expr + " =")
        except ZeroDivisionError:
            self._current_var.set("Erro")
            self._expr_var.set("")
        except Exception:
            self._current_var.set("Erro")
            self._expr_var.set("")

        self._expression = ""
        self._result_shown = True

    def _clear(self):
        self._expression = ""
        self._result_shown = False
        self._current_var.set("0")
        self._expr_var.set("")

    def _toggle_sign(self):
        val = self._current_var.get()
        try:
            num = float(val)
            num = -num
            if num == int(num):
                self._current_var.set(str(int(num)))
            else:
                self._current_var.set(str(num))
        except ValueError:
            pass

    def _percent(self):
        val = self._current_var.get()
        try:
            num = float(val) / 100
            if num == int(num):
                self._current_var.set(str(int(num)))
            else:
                self._current_var.set(self._fmt(num))
        except ValueError:
            pass

    def _dot(self):
        current = self._current_var.get()
        if self._result_shown:
            self._expression = ""
            self._current_var.set("0")
            self._result_shown = False
            current = "0"
        if "." not in current:
            self._current_var.set(current + ".")

    @staticmethod
    def _fmt(value) -> str:
        if isinstance(value, int):
            return f"{value:,}".replace(",", ".")
        s = f"{value:.10g}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s

    # ── Keyboard ─────────────────────────────────────────────────────────────

    def _on_key(self, event):
        k = event.keysym
        char = event.char
        mapping = {
            "Return":    "=",
            "KP_Enter":  "=",
            "BackSpace": None,
            "Escape":    "AC",
            "slash":     "÷",
            "asterisk":  "×",
            "minus":     "−",
            "plus":      "+",
            "equal":     "=",
            "percent":   "%",
        }
        if k in mapping:
            target = mapping[k]
            if target is None:
                self._backspace()
            else:
                self._on_button(target)
        elif char.isdigit():
            self._on_button(char)
        elif char == ".":
            self._dot()

    def _backspace(self):
        if self._result_shown:
            self._clear()
            return
        current = self._current_var.get()
        if len(current) > 1:
            self._current_var.set(current[:-1])
        else:
            self._current_var.set("0")


if __name__ == "__main__":
    app = Calculadora()
    app.mainloop()
