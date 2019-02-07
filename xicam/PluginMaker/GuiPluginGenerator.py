
import os

from qtpy.QtCore import *
from qtpy.QtWidgets import *

import pyqtgraph as pg


class GuiPluginGenerator(object):

    class QTabBar(QTabBar):

        """QTabBar with double click signal and tab rename behavior."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.__edit = None
            self.__edited_tab = None

        def start_rename(self, tab_index):
            self.__edited_tab = tab_index
            rect = self.tabRect(tab_index)
            top_margin = 3
            left_margin = 6
            self.__edit = QLineEdit(self)
            self.__edit.show()
            self.__edit.move(rect.left() + left_margin, rect.top() + top_margin)
            self.__edit.resize(rect.width() - 2 * left_margin, rect.height() - 2 * top_margin)
            self.__edit.setText(self.tabText(tab_index))
            self.__edit.selectAll()
            self.__edit.setFocus()
            self.__edit.editingFinished.connect(self.finish_rename)

        def finish_rename(self):
            self.setTabText(self.__edited_tab, self.__edit.text())
            self.__edit.deleteLater()

    def __init__(self, result):
        self.parent = result
        self.plugin_name = result.findChild(QLineEdit, "plugin_name")  # type: QLineEdit
        self.plugin_version = result.findChild(QLineEdit, "plugin_version")  # type: QLineEdit
        self.author_name = result.findChild(QLineEdit, "author_name")  # type: QLineEdit
        self.author_url = result.findChild(QLineEdit, "author_url")  # type: QLineEdit
        self.description = result.findChild(QTextEdit, "description")  # type: QTextEdit

        self.num_of_stages = result.findChild(QSpinBox, "stages")  # type: QSpinBox
        self.designer_manager = result.findChild(QStackedWidget, "designer_manager")  # type: QStackedWidget
        self.preview_manager = result.findChild(QTabWidget, "preview_manager")  # type: QTabWidget
        self.preview_manager.setTabBar(GuiPluginGenerator.QTabBar())
        self.preview_manager.tabBar().tabBarDoubleClicked.connect(self.preview_manager.tabBar().start_rename)

        tree_widget = QTreeWidget()
        self.designer_manager.addWidget(tree_widget)

        widget = QMainWindow()
        self.preview_manager.addTab(widget, "Stage 1")
        self.preview_manager.currentChanged.connect(self.tab_changed)

        self.widgets = result.findChild(QComboBox, "widgets")  # type: QComboBox
        self.add_preview = result.findChild(QPushButton, "add")  # type: QPushButton
        self.remove_preview = result.findChild(QPushButton, "remove")  # type: QPushButton

        # handle preview
        self.add_preview.clicked.connect(self.add_preview_clicked)
        self.remove_preview.clicked.connect(self.remove_preview_clicked)
        self.num_of_stages.valueChanged.connect(self.number_of_stages_changed)

    def number_of_stages_changed(self):
        value = int(self.num_of_stages.value())
        current_tab_count = self.preview_manager.count()

        if value == current_tab_count:
            return

        if value > current_tab_count:
            for i in range(value - current_tab_count):
                widget = QMainWindow()
                self.preview_manager.addTab(widget, "Stage " + str(self.preview_manager.count() + 1))
                self.designer_manager.addWidget(QTreeWidget())
        else:
            for i in range(current_tab_count - value):
                self.preview_manager.removeTab(self.preview_manager.count( ) -1)

                removed_widget = self.designer_manager.widget(self.designer_manager.count( ) -1)
                self.designer_manager.removeWidget(removed_widget)
                removed_widget.deleteLater()

    def tab_changed(self):
        self.designer_manager.setCurrentIndex(self.preview_manager.currentIndex())

    def add_preview_clicked(self):

        text = self.widgets.currentText()

        designer = self.designer_manager.currentWidget()
        indices = designer.selectedIndexes()
        model = designer.model()

        if model.hasChildren() is False:
            # layout is not selected
            if text.lower().find("layout") < 0:
                parent = QTreeWidgetItem()
                parent.setText(0, "VerticalLayout")
                item = QTreeWidgetItem(parent)
                item.setText(0, text)
                designer.addTopLevelItem(parent)
            else:
                parent = QTreeWidgetItem()
                parent.setText(0, text)
                designer.addTopLevelItem(parent)
        elif len(indices) > 0:
            item = designer.itemFromIndex(indices[0])  # type: QTreeWidgetItem
            if item.text(0).lower().find("layout") >= 0:
                new_item = QTreeWidgetItem(item)
                new_item.setText(0, text)
            else:
                parent_item = item.parent()
                new_item = QTreeWidgetItem(parent_item)
                new_item.setText(0, text)

        designer.expandAll()
        self.redraw_preview()

    def remove_preview_clicked(self):
        designer = self.designer_manager.currentWidget()  # type: QTreeWidget
        indices = designer.selectedIndexes() # type: QModelIndexList

        for index in indices:
            # print(index.row(), index.parent())
            designer.model().removeRow(index.row(), index.parent())

        designer.expandAll()
        self.redraw_preview()

    def generate_widget(self, layout_item: QTreeWidgetItem):

        layout_type = layout_item.text(0)

        layout_widget = QWidget()
        if layout_type.lower().find("horizontal") >= 0:
            layout = QHBoxLayout()
        else:
            layout = QVBoxLayout()

        layout_widget.setLayout(layout)

        for child_index in range(layout_item.childCount()):
            child_item = layout_item.child(child_index)

            if child_item.text(0).lower().find("layout") >= 0:
                child_layout = self.generate_widget(child_item)
                layout.addWidget(child_layout)
            else:
                child_text = child_item.text(0)

                if child_text.find("PyQtGraph") >= 0:
                    child_widget = pg.ImageView()
                elif child_text.find("Label") >= 0:
                    child_widget = QLabel()
                    child_widget.setText("Enter Label:")
                elif child_text.find("TextBox") >= 0:
                    child_widget = QLineEdit()
                    child_widget.setText("Enter some content...")
                elif child_text.find("Slider") >= 0:
                    child_widget = QSlider()
                    if child_text.find("Horizontal") >= 0:
                        child_widget.setOrientation(Qt.Horizontal)
                    else:
                        child_widget.setOrientation(Qt.Vertical)
                elif child_text.find("PushButton") >= 0:
                    child_widget = QPushButton()
                    child_widget.setText("Press to execute...")
                else:
                    child_widget = QWidget()

                layout.addWidget(child_widget)
        return layout_widget

    def redraw_preview(self):

        designer = self.designer_manager.currentWidget()

        count = designer.topLevelItemCount()

        if count == 0:
            return

        # only process 1
        layout_item = designer.topLevelItem(0)
        preview = self.preview_manager.currentWidget()  # type: QMainWindow

        layout_widget = self.generate_widget(layout_item)

        widget = preview.takeCentralWidget()
        preview.setCentralWidget(layout_widget)

        if widget is not None:
            widget.deleteLater()

    def print_widget(self, layout_item: QTreeWidgetItem, tab_value, master_index):

        output = ""

        layout_type = layout_item.text(0)

        output += "{0}widget_{1} = QWidget()\n".format(tab_value, master_index)
        if layout_type.lower().find("horizontal") >= 0:
            output += "{0}layout_{1} = QHBoxLayout()\n".format(tab_value, master_index+1)
        else:
            output += "{0}layout_{1} = QVBoxLayout()\n".format(tab_value, master_index+1)

        output += "{0}widget_{1}.setLayout(layout_{2})\n".format(tab_value, master_index, master_index+1)

        child_master_index = master_index + 1
        for child_index in range(layout_item.childCount()):
            child_item = layout_item.child(child_index)
            child_master_index = child_master_index+1

            if child_item.text(0).lower().find("layout") >= 0:
                (update_child_master_index, update_output) = self.print_widget(child_item, tab_value, child_master_index)
                output += "\n" + update_output
                output += "{0}layout_{1}.addWidget(widget_{2})\n\n".format(tab_value, master_index+1, child_master_index)
                child_master_index = update_child_master_index
            else:
                child_text = child_item.text(0)

                if child_text.find("PyQtGraph") >= 0:
                    output += "{0}widget_{1} = pg.ImageView()\n".format(tab_value, child_master_index)
                elif child_text.find("Label") >= 0:
                    output += "{0}widget_{1} = QLabel()\n".format(tab_value, child_master_index)
                    output += "{0}widget_{1}.setText(\"Enter Label:\")\n".format(tab_value, child_master_index)
                elif child_text.find("TextBox") >= 0:
                    output += "{0}widget_{1} = QLineEdit()\n".format(tab_value, child_master_index)
                    output += "{0}widget_{1}.setText(\"Enter some content...:\")\n".format(tab_value, child_master_index)
                elif child_text.find("Slider") >= 0:
                    output += "{0}widget_{1} = QSlider()\n".format(tab_value, child_master_index)
                    if child_text.find("Horizontal") >= 0:
                        output += "{0}widget_{1}.setOrientation(Qt.Horizontal)\n".format(tab_value, child_master_index)
                    else:
                        output += "{0}widget_{1}.setOrientation(Qt.Vertical)\n".format(tab_value, child_master_index)
                elif child_text.find("PushButton") >= 0:
                    output += "{0}widget_{1} = QPushButton()\n".format(tab_value, child_master_index)
                    output += "{0}widget_{1}.setText(\"Press to Execute...:\")\n".format(tab_value, child_master_index)
                else:
                    output += "{0}widget_{1} = QWidget()\n".format(tab_value, child_master_index)

                output += "{0}layout_{1}.addWidget(widget_{2})\n".format(tab_value, master_index+1, child_master_index)
        return child_master_index, output

    def generate_stream_output(self):

        tab_value = "        "

        output_template = """
    def stage_{0}(self):
        main_window = QMainWindow()
{1}
        {2}
        return main_window
        """
        output_stream = []
        for designer_index in range(self.designer_manager.count()):
            designer = self.designer_manager.widget(designer_index)
            count = designer.topLevelItemCount()

            if count == 0:
                output_stream.append(output_template.format(designer_index, "", ""))
                continue

            # only process 1
            layout_item = designer.topLevelItem(0)

            final_index, layout_str = self.print_widget(layout_item, tab_value, 0)

            output_stream.append(output_template.format(designer_index,
                                                        layout_str,
                                                        "main_window.setCentralWidget(widget_0)"))

        return "\n".join(output_stream)

    def generate_stream_stages(self):

        output = "{"

        for preview_index in range(self.preview_manager.count()):
            preview_header = self.preview_manager.tabText(preview_index)

            output += "\"{0}\": GUILayout(self.stage_{1}()),".format(preview_header, preview_index)
        output += "}"

        return output

