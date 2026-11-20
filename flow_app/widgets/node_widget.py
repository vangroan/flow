import logging

from PySide6.QtCore import (
    QPointF,
    QRectF,
    Qt,
)
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsProxyWidget,
)

logger = logging.getLogger(__name__)


class Edge(QGraphicsPathItem):
    def __init__(self, src, dst):
        super().__init__()
        self.src, self.dst = src, dst
        self.setPen(QPen(QColor("#aaa"), 2))
        self.setZValue(-1)  # draw behind nodes
        src.edges.append(self)
        dst.edges.append(self)
        self.update_path()

    def update_path(self):
        a = self.src.scenePos() + self.src.rect().center()
        b = self.dst.scenePos() + self.dst.rect().center()
        dx = abs(b.x() - a.x()) * 0.5
        p = QPainterPath(a)
        p.cubicTo(a + QPointF(dx, 0), b - QPointF(dx, 0), b)
        self.setPath(p)


class Port(QGraphicsEllipseItem):
    def __init__(self, parent):
        super().__init__(-6, -6, 12, 12, parent)
        self.setBrush(QBrush(QColor("#4fc3f7")))
        self.edges = []


class ResizeGrip(QGraphicsItem):
    SIZE = 12

    def __init__(self, node):
        super().__init__(node)
        self.node = node
        self.setCursor(Qt.SizeFDiagCursor)
        self.reposition()

    def reposition(self):
        r = self.node.rect_
        self.setPos(r.width() - self.SIZE, r.height() - self.SIZE)

    def boundingRect(self):
        return QRectF(0, 0, self.SIZE, self.SIZE)

    def paint(self, p, *_):
        p.setBrush(QColor("#888"))
        p.drawRect(self.boundingRect())

    def mousePressEvent(self, e):
        e.accept()  # needed to receive move events

    def mouseMoveEvent(self, e):
        pos = self.node.mapFromScene(e.scenePos())
        self.node.resize(max(80, pos.x()), max(50, pos.y()))


class Node(QGraphicsItem):
    TITLE_HEIGHT = 28
    BODY_MARGIN = 8

    def __init__(self, title, x, y, widget=None):
        super().__init__()
        self.title = title
        self.rect_ = QRectF(0, 0, 160, 90)
        # Optional embedded Qt widget, hosted via a proxy that is a child of the node
        # so it moves/zooms with it.
        self.proxy = None
        if widget is not None:
            self.proxy = QGraphicsProxyWidget(self)
            self.proxy.setWidget(widget)
        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.in_port, self.out_port = Port(self), Port(self)
        self.grip = ResizeGrip(self)
        self._layout()

    def rect(self):
        return self.rect_

    def boundingRect(self):
        return self.rect_.adjusted(-2, -2, 2, 2)

    def resize(self, w, h):
        self.prepareGeometryChange()
        self.rect_.setSize(self.rect_.size().__class__(w, h))
        self._layout()

    def _layout(self):
        self.in_port.setPos(0, self.rect_.height() / 2)
        self.out_port.setPos(self.rect_.width(), self.rect_.height() / 2)
        self.grip.reposition()
        if self.proxy is not None:
            m = self.BODY_MARGIN
            self.proxy.setPos(m, self.TITLE_HEIGHT)
            self.proxy.resize(
                max(0, self.rect_.width() - 2 * m),
                self.proxy.size().height(),  # keep the widget's own height
            )
        self._update_edges()

    def _update_edges(self):
        for e in self.in_port.edges + self.out_port.edges:
            e.update_path()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self._update_edges()
        return super().itemChange(change, value)

    def paint(self, p, option, widget=None):
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor("#37474f"))
        p.setPen(QPen(QColor("#ffb74d") if self.isSelected() else QColor("#222"), 2))
        p.drawRoundedRect(self.rect_, 8, 8)
        p.setPen(Qt.white)
        p.drawText(
            self.rect_.adjusted(8, 6, -8, -6), Qt.AlignTop | Qt.AlignLeft, self.title
        )
