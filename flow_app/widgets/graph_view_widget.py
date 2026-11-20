import logging

from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QGraphicsView,
)

logger = logging.getLogger(__name__)



class GraphView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, e):  # zoom
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.scale(f, f)

    def mousePressEvent(self, e):  # middle-drag to pan
        if e.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            e = type(e)(
                e.type(), e.position(), Qt.LeftButton, Qt.LeftButton, e.modifiers()
            )
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        self.setDragMode(QGraphicsView.RubberBandDrag)
