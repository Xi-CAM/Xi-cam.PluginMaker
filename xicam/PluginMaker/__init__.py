import os
import sys
import logging

from qtpy.QtCore import *
from qtpy.QtWidgets import *
from qtpy import uic

from xicam.plugins import GUIPlugin, GUILayout

from cookiecutter.main import cookiecutter

from .PluginDependencyGenerator import PluginDependencyGenerator
from .GuiPluginGenerator import GuiPluginGenerator

# from pyqode.core.widgets import InteractiveConsole
# from .PyCodeEditor import MyPythonCodeEdit

# from pyqode.python.widgets import PyConsole
# from pyqode.python.widgets import PyInteractiveConsole

logger = logging.getLogger("pyqode.core.modes.autocomplete")


class MyCustomClass(QWidget):

    class Spoiler(QWidget):
        def __init__(self, *args, **kwargs):
            """
            References:
                # Adapted from c++ version
                http://stackoverflow.com/questions/32476006/how-to-make-an-expandable-collapsable-section-widget-in-qt
            """
            super().__init__(*args, **kwargs)

            self.animationDuration = 300
            self.toggleAnimation = QParallelAnimationGroup()
            self.contentArea = QScrollArea()
            self.headerLine = QFrame()
            self.toggleButton = QToolButton()
            self.mainLayout = QGridLayout()

            toggleButton = self.toggleButton
            toggleButton.setStyleSheet("QToolButton { border: none; }")
            toggleButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            toggleButton.setArrowType(Qt.RightArrow)
            toggleButton.setText(str("==title=="))
            toggleButton.setCheckable(True)
            toggleButton.setChecked(False)

            headerLine = self.headerLine
            headerLine.setFrameShape(QFrame.HLine)
            headerLine.setFrameShadow(QFrame.Sunken)
            headerLine.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

            self.contentArea.setStyleSheet("QScrollArea { background-color: white; border: none; }")
            self.contentArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            # start out collapsed
            self.contentArea.setMaximumHeight(0)
            self.contentArea.setMinimumHeight(0)
            # let the entire widget grow and shrink with its content
            toggleAnimation = self.toggleAnimation
            toggleAnimation.addAnimation(QPropertyAnimation(self, b"minimumHeight"))
            toggleAnimation.addAnimation(QPropertyAnimation(self, b"maximumHeight"))
            toggleAnimation.addAnimation(QPropertyAnimation(self.contentArea, b"maximumHeight"))
            # don't waste space
            mainLayout = self.mainLayout
            mainLayout.setVerticalSpacing(0)
            mainLayout.setContentsMargins(0, 0, 0, 0)
            row = 0
            mainLayout.addWidget(self.toggleButton, row, 0, 1, 1, Qt.AlignLeft)
            mainLayout.addWidget(self.headerLine, row, 2, 1, 1)
            row += 1
            mainLayout.addWidget(self.contentArea, row, 0, 1, 3)
            self.setLayout(self.mainLayout)

            def start_animation(checked):
                arrow_type = Qt.DownArrow if checked else Qt.RightArrow
                direction = QAbstractAnimation.Forward if checked else QAbstractAnimation.Backward
                toggleButton.setArrowType(arrow_type)
                self.toggleAnimation.setDirection(direction)
                self.toggleAnimation.start()

            self.toggleButton.clicked.connect(start_animation)

        def setContentLayout(self, contentLayout):
            # Not sure if this is equivalent to self.contentArea.destroy()
            self.contentArea.destroy()
            self.contentArea.setLayout(contentLayout)
            collapsedHeight = self.sizeHint().height() - self.contentArea.maximumHeight()
            contentHeight = contentLayout.sizeHint().height()
            for i in range(self.toggleAnimation.animationCount() - 1):
                spoilerAnimation = self.toggleAnimation.animationAt(i)
                spoilerAnimation.setDuration(self.animationDuration)
                spoilerAnimation.setStartValue(collapsedHeight)
                spoilerAnimation.setEndValue(collapsedHeight + contentHeight)
            contentAnimation = self.toggleAnimation.animationAt(self.toggleAnimation.animationCount() - 1)
            contentAnimation.setDuration(self.animationDuration)
            contentAnimation.setStartValue(0)
            contentAnimation.setEndValue(contentHeight)

    class SpoilerWidget(QGroupBox):
        def __init__(self, *args, **kwargs):
            super(MyCustomClass.SpoilerWidget, self).__init__(*args, **kwargs)

        def modify(self):
            my_widget = MyCustomClass.Spoiler()
            my_widget.toggleButton.setText(self.title())
            self.setTitle("")
            my_layout = QVBoxLayout()

            my_widget.setContentLayout(self.layout())
            my_widget.toggleButton.click()

            my_layout.addWidget(my_widget)
            self.setLayout(my_layout)


sys.modules["MyCustomClass"] = MyCustomClass


class PluginMaker(QWidget, GUIPlugin):
    name = 'Plugin Maker'

    def generate_output(self):

        if len(self.plugin_name.text()) == 0:
            QMessageBox.information(self.plugin_maker, "Please enter plugin name", "Please enter a plugin name")
            return

        path = str(QFileDialog.getExistingDirectory(self.plugin_maker, "Select Directory"))
        print("PATH", path)

        plugin_name = self.plugin_name
        plugin_type = self.plugin_type.currentText()

        extra_content = dict()

        extra_content["core_name"] = "xicam"
        extra_content["project_name"] = "Xi-cam.plugins." + plugin_name.text()
        extra_content["app_name"] = "xicam." + plugin_name.text()
        extra_content["plugin_name"] = plugin_name.text()
        extra_content["plugin_version"] = self.plugin_generator.plugin_version.text()
        extra_content["plugin_file_name"] = "__init__.py"
        extra_content["author_name"] = self.plugin_generator.author_name.text()
        extra_content["author_email"] = self.plugin_generator.author_email.text()
        extra_content["author_url"] = self.plugin_generator.author_url.text()
        extra_content["description"] = self.plugin_generator.description.toPlainText()
        extra_content["keywords"] = self.plugin_generator.keywords.text()

        dep_list = []
        for dep_index in range(self.plugin_generator.dependency_list.count()):
            dep_list.append(self.plugin_generator.dependency_list.item(dep_index).text())

        extra_content["dependencies"] = "\n".join(dep_list)

        extra_content["plugin_code"] = self.gui_generator.generate_stream_output()
        extra_content["stages_code"] = self.gui_generator.generate_stream_stages()
        extra_content["yapsy_ext"] = "yapsy-plugin"

        print(extra_content)

        # my_path = os.path.dirname(os.path.realpath(__file__)) + os.path.sep + "cookiecutter-pipproject"
        my_path = "https://github.com/lbl-camera/Xi-cam.templates.GuiPlugin"

        cookiecutter(my_path,
                     no_input=True, overwrite_if_exists=True,
                     output_dir=path, extra_context=extra_content)

        from xicam.plugins import manager

        manager.collectPlugins()

    def __init__(self, *args, **kwargs):
        self.plugin_maker = QMainWindow()
        self.uic_file = os.path.dirname(os.path.realpath(__file__)) + os.path.sep + "ui" + os.path.sep + "main.ui"

        result = uic.loadUi(self.uic_file, MyCustomClass())

        spoiler_widgets = result.findChildren(MyCustomClass.SpoilerWidget)
        for spoiler in spoiler_widgets:
            spoiler.modify()

        self.plugin_type = result.findChild(QComboBox, "plugin_type")  # type: QComboBox
        self.plugin_name = result.findChild(QLineEdit, "plugin_name")  # type: QLineEdit
        self.pyqode_root = result.findChild(QWidget, "pyqode_root")  # type: QWidget
        self.pyqode_root.setLayout(QVBoxLayout())
        # self.pyqode_root.layout().addWidget(MyPythonCodeEdit())
        self.pyqode_root.layout().addWidget(QTextEdit())

        self.plugin_generator = PluginDependencyGenerator(result)
        self.gui_generator = GuiPluginGenerator(result)

        self.generate = result.findChild(QPushButton, "generate")  # type: QPushButton
        self.generate.clicked.connect(self.generate_output)

        self.plugin_maker.setCentralWidget(result)
        self.stages = {'PluginMaker': GUILayout(self.plugin_maker)}

        super(PluginMaker, self).__init__(*args, **kwargs)

