"""
Shared helper for generating .excalidraw JSON files programmatically.
Used across all WITrade Quant Platform ADD pages for consistent styling.
"""
import json

COLORS = {
    "blue":   {"stroke": "#1971c2", "bg": "#e7f5ff", "bg2": "#a5d8ff"},
    "yellow": {"stroke": "#f59f00", "bg": "#fff9db", "bg2": "#ffe066"},
    "green":  {"stroke": "#2f9e44", "bg": "#d3f9d8", "bg2": "#8ce99a"},
    "purple": {"stroke": "#862e9c", "bg": "#f3d9fa", "bg2": "#e599f7"},
    "red":    {"stroke": "#c92a2a", "bg": "#ffe3e3", "bg2": "#ffa8a8"},
    "gray":   {"stroke": "#495057", "bg": "#f8f9fa", "bg2": "#dee2e6"},
    "cyan":   {"stroke": "#0c8599", "bg": "#e3fafc", "bg2": "#99e9f2"},
    "orange": {"stroke": "#d9480f", "bg": "#fff4e6", "bg2": "#ffc078"},
}


class Diagram:
    def __init__(self, title=None):
        self.elements = []
        self._counter = 0
        if title:
            self.text(30, 20, 900, title, font_size=34, align="left")

    def _id(self, prefix="el"):
        self._counter += 1
        return f"{prefix}-{self._counter}"

    def rect(self, x, y, w, h, stroke="#1e1e1e", bg="transparent",
             rounded=True, stroke_width=2, dashed=False, fill_style="solid"):
        el = {
            "id": self._id("rect"), "type": "rectangle",
            "x": x, "y": y, "width": w, "height": h, "angle": 0,
            "strokeColor": stroke, "backgroundColor": bg,
            "fillStyle": fill_style, "strokeWidth": stroke_width,
            "strokeStyle": "dashed" if dashed else "solid",
            "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None,
            "roundness": {"type": 3} if rounded else None,
            "boundElements": [], "updated": 1, "link": None, "locked": False,
        }
        self.elements.append(el)
        return el["id"]

    def diamond(self, x, y, w, h, stroke="#1e1e1e", bg="transparent"):
        el = {
            "id": self._id("diamond"), "type": "diamond",
            "x": x, "y": y, "width": w, "height": h, "angle": 0,
            "strokeColor": stroke, "backgroundColor": bg,
            "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
            "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None,
            "roundness": None, "boundElements": [], "updated": 1,
            "link": None, "locked": False,
        }
        self.elements.append(el)
        return el["id"]

    def text(self, x, y, w, text, font_size=16, color="#1e1e1e",
              align="center", font_family=1, height=None):
        if height is None:
            height = font_size * 1.25 * (text.count("\n") + 1)
        el = {
            "id": self._id("text"), "type": "text",
            "x": x, "y": y, "width": w, "height": height, "angle": 0,
            "strokeColor": color, "backgroundColor": "transparent",
            "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
            "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None,
            "roundness": None, "boundElements": [], "updated": 1,
            "link": None, "locked": False,
            "text": text, "fontSize": font_size, "fontFamily": font_family,
            "textAlign": align, "verticalAlign": "top", "containerId": None,
            "originalText": text, "lineHeight": 1.25,
        }
        self.elements.append(el)
        return el["id"]

    def arrow(self, x1, y1, x2, y2, color="#1e1e1e", dashed=False,
              stroke_width=2, points=None):
        if points is None:
            points = [[0, 0], [x2 - x1, y2 - y1]]
        x_vals = [p[0] + x1 for p in points]
        y_vals = [p[1] + y1 for p in points]
        el = {
            "id": self._id("arrow"), "type": "arrow",
            "x": x1, "y": y1,
            "width": max(x_vals) - min(x_vals), "height": max(y_vals) - min(y_vals),
            "angle": 0, "strokeColor": color, "backgroundColor": "transparent",
            "fillStyle": "solid", "strokeWidth": stroke_width,
            "strokeStyle": "dashed" if dashed else "solid",
            "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None,
            "roundness": {"type": 2}, "boundElements": [], "updated": 1,
            "link": None, "locked": False,
            "points": points, "lastCommittedPoint": None,
            "startBinding": None, "endBinding": None,
            "startArrowhead": None, "endArrowhead": "arrow",
        }
        self.elements.append(el)
        return el["id"]

    def labeled_box(self, x, y, w, h, title, subtitle=None, color="gray",
                     title_size=18, subtitle_size=13, bg_variant="bg"):
        c = COLORS[color]
        self.rect(x, y, w, h, stroke=c["stroke"], bg=c[bg_variant])
        self.text(x + 8, y + 8, w - 16, title, font_size=title_size,
                   color="#1e1e1e", align="center")
        if subtitle:
            self.text(x + 8, y + 8 + title_size * 1.4, w - 16, subtitle,
                       font_size=subtitle_size, color="#343a40", align="center")
        return x, y, w, h

    def section(self, x, y, w, h, title, color="gray"):
        """Outer container band with a top-left title label."""
        c = COLORS[color]
        self.rect(x, y, w, h, stroke=c["stroke"], bg=c["bg"], stroke_width=2)
        self.text(x + 16, y + 12, w - 32, title, font_size=22, color=c["stroke"],
                   align="left")
        return x, y, w, h

    def row(self, start_x, y, n, item_w, item_h, gap, titles, subtitles=None,
             color="gray", title_size=15, subtitle_size=11):
        """Place n labeled boxes in a horizontal row. Returns list of (x,y,w,h) rects."""
        subtitles = subtitles or [None] * n
        out = []
        x = start_x
        for i in range(n):
            self.labeled_box(x, y, item_w, item_h, titles[i], subtitles[i],
                              color=color, title_size=title_size,
                              subtitle_size=subtitle_size)
            out.append((x, y, item_w, item_h))
            x += item_w + gap
        return out

    def row_width(self, n, item_w, gap):
        return n * item_w + (n - 1) * gap

    def pipeline(self, x, w, y, stages, color="blue", item_h=55, gap=45,
                  title_size=15, subtitle_size=11, arrow_color=None):
        """Vertical linear pipeline: stage -> arrow -> stage -> arrow -> ...
        stages: list of (title, subtitle) or (title, subtitle, color_override).
        Returns the y-coordinate just below the last stage."""
        cur_y = y
        arrow_color = arrow_color or COLORS[color]["stroke"]
        for i, stage in enumerate(stages):
            title, subtitle = stage[0], stage[1]
            c = stage[2] if len(stage) > 2 else color
            self.labeled_box(x, cur_y, w, item_h, title, subtitle, color=c,
                              title_size=title_size, subtitle_size=subtitle_size)
            cur_y += item_h
            if i < len(stages) - 1:
                self.arrow(x + w / 2, cur_y + 6, x + w / 2, cur_y + gap - 6,
                           color=arrow_color)
                cur_y += gap
        return cur_y

    def save(self, path):
        doc = {
            "type": "excalidraw",
            "version": 2,
            "source": "https://excalidraw.com",
            "elements": self.elements,
            "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
            "files": {},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        print(f"Saved {path} ({len(self.elements)} elements)")
