import sys

from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2.QtCore import *

import json


class UserField(QWidget):
    """
    This widget defines a user field, that can have any widget layout
    The only required method when inheriting UserField is data, that should return a string
    representing the data that the user entered in the field
    """
    def __init__(self,parent:QWidget,name):
        super().__init__(parent)
        self._name = name

    def data(self):
        raise NotImplementedError()

class LineEditField(UserField):
    """
    Simple LineEdit widget, returning LineEdit's text as data
    """
    def __init__(self,parent,name):
        super().__init__(parent,name)
        self._le = QLineEdit(self)
        layout = QVBoxLayout(self)
        layout.setMargin(0)
        layout.addWidget(self._le)
        self._le.show()
        self._le.setPlaceholderText(self._name)
        self.setLayout(layout)

    def data(self):
        return self._le.text()

class MultipleTextEdit(UserField):
    """
    TextEdit widget, with data returning every line entered by the user, but comma-separated
    """
    def __init__(self,parent,name):
        super().__init__(parent,name)
        self._te = QTextEdit(self)
        layout = QVBoxLayout(self)
        layout.setMargin(0)
        layout.addWidget(self._te)
        self._te.show()
        self._te.setPlaceholderText(self._name)
        self.setLayout(layout)

    def data(self):
        return ", ".join(self._te.toPlainText().split("\n"))

class MultipleFilesEdit(UserField):
    """
    Allows the user to browse several files, the returned data 
    is a comma-separated list of relative paths of the selected files
    """

class AdaptiveTreeNode(QWidget):
    """
    The key component of an adaptive tree form.
    """

    # Mapping a field info into its corresponding editor
    SUPPORTED_USER_FIELD_TYPES = {
        "LineEdit" : LineEditField,
        "MultipleTextEdit" : MultipleTextEdit,
        "MultipleFilesEdit" : MultipleTextEdit
    }

    def __init__(self,parent : QWidget=None,tree: dict=None):
        """
        Create a widget with a combobox that allows choosing the next widget in the form
        tree_part is a part of the whole tree dictionnary. Something like:
        {
            "subwidgets":
            [
                {
                    "name" : "Issue",
                    "properties":
                    [
                        {
                            "name" : "issue_number",
                            "field" : "LineEdit"
                        }
                    ],
                    "subwidgets":
                    [
                        {
                            "name" : "In file(s)",
                            "properties":
                            [
                                {
                                    "name" : "file_names",
                                    "field" : "MultipleFilesEdit"
                                }
                            ]
                        },
                        {
                            "name" : "In class",
                            "properties":
                            [
                                {
                                    "name" : "class_names",
                                    "field" : "MultipleTextEdit"
                                }
                            ]
                        },
                        {
                            "name" : ""
                        }
                    ]
                }
            ]
        }
        will recursively add new adaptive tree nodes for each subwidgets item...
        ... and recursively add the appropriate properties
        """
        super().__init__(parent)

        self._subwidgets = {}
        self._properties_widgets = {}
        self._name = tree["name"]
        self._select_combo = None
        self._label_name = None
        self._selected_widget = None
        
        layout = QVBoxLayout(self)
        layout.setMargin(0)

        # For debugging purpose only
        if isinstance(parent,AdaptiveTreeNode):
            self._label_name = QLabel(self._name + " " + parent._name,self)
            layout.insertWidget(0,self._label_name)

        if "subwidgets" in tree:
            for subwidget_info in tree["subwidgets"]:
                subwidget = AdaptiveTreeNode(self,subwidget_info)
                self._subwidgets[subwidget_info["name"]]=subwidget
        if "properties" in tree:
            properties_dicts = tree["properties"] # A list holding properties info
            for properties_info in properties_dicts:
                user_field = AdaptiveTreeNode.SUPPORTED_USER_FIELD_TYPES[properties_info["field"]](self,properties_info["name"])
                self._properties_widgets[properties_info["name"]] = user_field
        
        for prop_widget in self._properties_widgets.values():
            layout.insertWidget(-1,prop_widget)
        
        # If this node has subwidgets
        if self._subwidgets.keys():
            self._select_combo = QComboBox()
            self._select_combo.clear()
            self._select_combo.addItems(self._subwidgets.keys())
            self._select_combo.currentTextChanged.connect(self.on_selection_changed)

            self.update_subwidgets(self._select_combo.currentText())

            layout.addWidget(self._select_combo)

            for subwidget in self._subwidgets.values():
                layout.insertWidget(-1,subwidget)
        
        self.setLayout(layout)

    def update_subwidgets(self,name:str):
        """
        Of all the subwidget self is responsible for, only show the one selected
        """
        for widget_name,widget in self._subwidgets.items():
            if widget_name == name:
                widget.show()
                self._selected_widget = widget
            else:
                widget.hide()
    
    def on_selection_changed(self,text:str):
        self.update_subwidgets(text)

    def showEvent(self,event:QShowEvent):
        for prop in self._properties_widgets.values():
            prop.show()

    def data(self):
        """
        Recursively returns self data, propertie's data and subwidget's data
        """

        # Self's parent is already a TreeNode, so this method was called by it. Let's return self's children data (properties and selected subwidget)
        if isinstance(self.parent(),AdaptiveTreeNode):
            result = self._name
            if self._properties_widgets:
                result += " " + ", ".join([prop.data() for prop in self._properties_widgets.values()])
            if self._subwidgets:
                result += " " + self._selected_widget.data()
        else:
            result = self._subwidgets[self._select_combo.currentText()].data()
        return result


class AdaptiveTreeForm(QWidget):
    def __init__(self,parent):
        super().__init__(parent)
        self._root = None

    def load_from_file(self,file_name):
        tree = json.load(open(file_name))
        self._root = AdaptiveTreeNode(self,tree)
        self._root.show()
        layout = QVBoxLayout(self)
        layout.addWidget(self._root)
        layout.addStretch(0)
        self.setLayout(layout)

    def data(self):
        if self._root:
            return self._root.data()

class MainWindow(QMainWindow):

    def __init__(self,parent=None):
        super().__init__(parent)
        menu_bar = QMenuBar(self)
        file_menu = menu_bar.addMenu("File")
        openAction = file_menu.addAction("Open model")
        openAction.triggered.connect(self.on_open_model)
        self.setMenuBar(menu_bar)
        

    def on_open_model(self):
        model_file_name = QFileDialog.getOpenFileName(self,"Please chose a model file (must be json)")[0]
        if model_file_name:
            self.adaptive_form = AdaptiveTreeForm(self)
            self.adaptive_form.load_from_file(model_file_name)
            self.adaptive_form.show()
            self.setCentralWidget(self.adaptive_form)
            self.centralWidget().setLayout(QVBoxLayout())
            
            self._button_copy_data = QPushButton("Copy data to clipboard",self)
            self.centralWidget().layout().insertWidget(-1,self._button_copy_data)
            self._button_copy_data.clicked.connect(lambda: QApplication.clipboard().setText(self.adaptive_form.data()))

def main(argv):
    application = QApplication(argv)
    main_window = MainWindow()
    main_window.show()
    return application.exec_()

if __name__ == "__main__":
    main(sys.argv)
