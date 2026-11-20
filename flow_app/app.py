import logging
import sys

from PySide6.QtCore import (
    QtMsgType,
    qInstallMessageHandler,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGraphicsScene,
    QLineEdit,
)

from flow_app.widgets.graph_view_widget import GraphView
from flow_app.widgets.node_widget import Edge, Node

logger = logging.getLogger(__name__)



def create_application() -> QApplication:
    logger.info("Creating Qt Application")
    app = QApplication(sys.argv)
    scene = QGraphicsScene(-2000, -2000, 4000, 4000)
    name_edit = QLineEdit()
    name_edit.setPlaceholderText("name")
    name_edit.textChanged.connect(lambda text: print("name:", text))

    mode_box = QComboBox()
    mode_box.addItems(["Add", "Multiply", "Divide"])
    mode_box.currentTextChanged.connect(lambda text: print("mode:", text))

    a = Node("Source", 0, 0, widget=name_edit)
    b = Node("Sink", 300, 80, widget=mode_box)
    scene.addItem(a)
    scene.addItem(b)
    scene.addItem(Edge(a.out_port, b.in_port))
    view = GraphView(scene)
    view.resize(900, 600)
    view.show()

    # Keep Python references alive: a QGraphicsView doesn't own its scene, and
    # nothing owns the top-level view, so both could be garbage collected once
    # this function returns (intermittently closing the window).
    return app, view, scene


def install_qt_logging():
    """Route Qt's own messages (qWarning, qCritical, ...) into Python logging."""
    levels = {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }
    qt_logger = logging.getLogger("qt")

    def handler(msg_type, context, message):
        qt_logger.log(levels.get(msg_type, logging.INFO), message)

    qInstallMessageHandler(handler)


def main():
    logging.basicConfig(level="DEBUG")
    install_qt_logging()

    # Views need to stay on the stack to prevent garbage collection.
    app, view, scene = create_application()

    logger.info("Entering application loop.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()