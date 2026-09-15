"""Generate high-resolution ChordScout application icons (.ico and .png)."""

from pathlib import Path
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)


def create_chordscout_icon(size: int = 256) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    scale = size / 256.0

    # 1. Guitar Pick / Shield Outline
    path = QPainterPath()
    # Curved pick shape
    path.moveTo(128 * scale, 240 * scale)
    path.cubicTo(
        60 * scale, 180 * scale,
        20 * scale, 110 * scale,
        28 * scale, 48 * scale,
    )
    path.cubicTo(
        36 * scale, 20 * scale,
        70 * scale, 16 * scale,
        128 * scale, 16 * scale,
    )
    path.cubicTo(
        186 * scale, 16 * scale,
        220 * scale, 20 * scale,
        228 * scale, 48 * scale,
    )
    path.cubicTo(
        236 * scale, 110 * scale,
        196 * scale, 180 * scale,
        128 * scale, 240 * scale,
    )

    # Gradient fill for pick
    pick_grad = QLinearGradient(0, 0, size, size)
    pick_grad.setColorAt(0.0, QColor("#1e293b"))
    pick_grad.setColorAt(0.5, QColor("#0f172a"))
    pick_grad.setColorAt(1.0, QColor("#090d16"))

    painter.setPen(QPen(QColor("#38bdf8"), 5.0 * scale))
    painter.setBrush(QBrush(pick_grad))
    painter.drawPath(path)

    # 2. Soundwave frequency bars in background
    bar_heights = [24, 40, 65, 90, 110, 85, 60, 35, 20]
    bar_w = 6.0 * scale
    gap = 6.0 * scale
    total_w = len(bar_heights) * (bar_w + gap)
    start_x = (size - total_w) / 2.0
    mid_y = 100.0 * scale

    wave_grad = QLinearGradient(0, 50 * scale, 0, 150 * scale)
    wave_grad.setColorAt(0.0, QColor(56, 189, 248, 140))
    wave_grad.setColorAt(1.0, QColor(2, 132, 199, 220))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(wave_grad))

    for i, bh in enumerate(bar_heights):
        bx = start_x + (i * (bar_w + gap))
        h_scaled = bh * scale
        painter.drawRoundedRect(
            QRectF(bx, mid_y - (h_scaled / 2.0), bar_w, h_scaled),
            3 * scale,
            3 * scale,
        )

    # 3. Acoustic Guitar Soundhole & Bridge
    soundhole_center = QPointF(128 * scale, 120 * scale)
    hole_radius = 28 * scale
    hole_grad = QRadialGradient(soundhole_center, hole_radius)
    hole_grad.setColorAt(0.0, QColor("#000000"))
    hole_grad.setColorAt(0.8, QColor("#111111"))
    hole_grad.setColorAt(1.0, QColor("#222222"))
    painter.setPen(QPen(QColor("#f59e0b"), 3.0 * scale))
    painter.setBrush(QBrush(hole_grad))
    painter.drawEllipse(soundhole_center, hole_radius, hole_radius)

    # 4. Strings over soundhole
    painter.setPen(QPen(QColor(255, 255, 255, 180), 1.5 * scale))
    for s_offset in range(-18, 22, 7):
        sx = 128 * scale + (s_offset * scale)
        painter.drawLine(int(sx), int(60 * scale), int(sx), int(185 * scale))

    # 5. Glowing Musical Note / Chord 'C' badge
    c_rect = QRectF(108 * scale, 100 * scale, 40 * scale, 40 * scale)
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Segoe UI", int(20 * scale), QFont.Weight.Black))
    painter.drawText(c_rect, Qt.AlignmentFlag.AlignCenter, "C")

    painter.end()
    return img


def main():
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QGuiApplication([])
    out_dir = Path("assets")
    out_dir.mkdir(exist_ok=True)

    img_256 = create_chordscout_icon(256)
    img_256.save(str(out_dir / "chordscout.png"), "PNG")
    img_256.save(str(out_dir / "chordscout.ico"), "ICO")
    print(f"Generated {out_dir / 'chordscout.ico'} and {out_dir / 'chordscout.png'}")


if __name__ == "__main__":
    main()
