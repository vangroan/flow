import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
)


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
    def __init__(self, title, x, y):
        super().__init__()
        self.title = title
        self.rect_ = QRectF(0, 0, 160, 90)
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


app = QApplication(sys.argv)
scene = QGraphicsScene(-2000, -2000, 4000, 4000)
a, b = Node("Source", 0, 0), Node("Sink", 300, 80)
scene.addItem(a)
scene.addItem(b)
scene.addItem(Edge(a.out_port, b.in_port))
view = GraphView(scene)
view.resize(900, 600)
view.show()
sys.exit(app.exec())
