import os

from PyQt5.QtWidgets import QListWidget
from qtpy.QtCore import *
from qtpy.QtWidgets import *

from pip import _internal


class PluginDependencyGenerator(object):

    dependency_list: QListWidget

    def __init__(self, result):
        self.parent = result
        self.plugin_name = result.findChild(QLineEdit, "plugin_name")  # type: QLineEdit
        self.plugin_version = result.findChild(QLineEdit, "plugin_version")  # type: QLineEdit
        self.author_email = result.findChild(QLineEdit, "author_email")  # type: QLineEdit
        self.author_name = result.findChild(QLineEdit, "author_name")  # type: QLineEdit
        self.author_url = result.findChild(QLineEdit, "author_url")  # type: QLineEdit
        self.keywords = result.findChild(QLineEdit, "keywords")  # type: QLineEdit
        self.description = result.findChild(QTextEdit, "description")  # type: QTextEdit

        self.dependency = result.findChild(QLineEdit, "dependency")  # type: QLineEdit
        self.dependency_list = result.findChild(QListWidget, "dependency_list")  # type: QListWidget

        self.add_dependency = result.findChild(QPushButton, "add_dependency")  # type: QPushButton
        self.dependency_table = result.findChild(QTableWidget, "dependency_table")  # type: QTableWidget

        self.search_command = _internal.commands.SearchCommand()
        self.dv = self.search_command.cmd_opts.parser.get_default_values()
        self.changed_text = ""

        self.model_timer = QTimer()
        self.model_timer.setSingleShot(True)
        self.model_timer.timeout.connect(self.dependency_list_edited)
        self.dependency.textChanged.connect(self.dependency_list_text_changed)
        self.add_dependency.clicked.connect(self.add_dependency_clicked)

    def get_dependency_list(self, text):
        try:
            results = self.search_command.search(text, self.dv)
            return results
        except:
            pass
        return []

    def dependency_list_text_changed(self, text: str):
        self.changed_text = text
        self.model_timer.start(300)

    def dependency_list_edited(self):
        text = self.changed_text
        deps = self.get_dependency_list(text)

        model = self.dependency_table.model()

        self.dependency_table.setRowCount(0)
        for dep in deps:
            model.insertRow(0)
            model.setData(model.index(0,0), dep["name"])
            model.setData(model.index(0,1), dep["version"])
            model.setData(model.index(0,2), dep["summary"])

    def add_dependency_clicked(self):
        selected = self.dependency_table.selectedIndexes()  # type: QModelIndexList

        if len(selected) == 0:
            self.dependency_list.insertItem(0, self.dependency.text())
        for selected_item in selected:
            if selected_item.column() == 0:
                self.dependency_list.insertItem(0, self.dependency_table.itemFromIndex(selected_item).text())

    def write_setup_py(self, path):

        output_template = """
from setuptools import setup

setup(
name='{0}',

# Versions should comply with PEP440.  For a discussion on single-sourcing
# the version across setup.py and the project code, see
# https://packaging.python.org/en/latest/single_source_version.html
version='{1}',

description='{2}'

# The project's main homepage.
url='{3}',

# Author details
author='{4}',
author_email='{5}',

# Choose your license
license='BSD',

# See https://pypi.python.org/pypi?%3Aaction=list_classifiers
classifiers=[
    # How mature is this project? Common values are
    #   3 - Alpha
    #   4 - Beta
    #   5 - Production/Stable
    'Development Status :: 4 - Beta',

    # Indicate who your project is intended for
    'Intended Audience :: Science/Research',
    'Topic :: Scientific/Engineering :: Physics',

    # Pick your license as you wish (should match "license" above)
    'License :: OSI Approved :: BSD License',

    # Specify the Python versions you support here. In particular, ensure
    # that you indicate whether you support Python 2, Python 3 or both.
    'Programming Language :: Python :: 3.6'
],

# What does your project relate to?
keywords='{6}',

# You can just specify the packages manually here if your project is
# simple. Or you can use find_packages().
packages=['{0}'],

package_dir={{}},

# Alternatively, if you want to distribute just a my_module.py, uncomment
# this:
# py_modules=["__init__"],

# List run-time dependencies here.  These will be installed by pip when
# your project is installed. For an analysis of "install_requires" vs pip's
# requirements files see:
# https://packaging.python.org/en/latest/requirements.html
install_requires=[{7}],

setup_requires=[],

# List additional groups of dependencies here (e.g. development
# dependencies). You can install these using the following syntax,
# for example:
# $ pip install -e .[dev,tests]
#extras_require={{
#    # 'dev': ['check-manifest'],
#    'tests': ['pytest', 'coverage'],
#}},

# If there are data files included in your packages that need to be
# installed, specify them here.  If using Python 2.6 or less, then these
# have to be included in MANIFEST.in as well.
package_data={{'{0}': ['*.yapsy-plugin', '*.yml']}},

# To provide executable scripts, use entry points in preference to the
# "scripts" keyword. Entry points provide cross-platform support and allow
# pip to create the appropriate form of executable for the target platform.
entry_points={{}},

ext_modules=[],
include_package_data=True
)
        """

        name = "xicam." + self.plugin_name.text()
        version = self.plugin_version.text()
        description = self.description.toPlainText()
        url = self.author_url.text()
        author = self.author_name.text()
        author_email = self.author_email.text()
        keywords = self.keywords.text()

        deps = []

        for item_index in range(self.dependency_list.count()):
            deps.append(self.dependency_list.item(item_index).text())

        deps_str = ",".join(["\"" + dep + "\"" for dep in deps])

        output = output_template.format(name, version, description, url, author, author_email, keywords, deps_str)

        setup_py = path + os.sep + "setup.py"
        with open(setup_py, "w") as setup_file:
            setup_file.writelines(output)

    def generate_output(self, path):
        # create setup.py

        core_dir = path + os.path.sep + "xicam"
        os.mkdir(core_dir)

        plugin_dir = core_dir + os.path.sep + self.plugin_name.text()
        os.mkdir(plugin_dir)

        self.write_setup_py(path)

        return plugin_dir
