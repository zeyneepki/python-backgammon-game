from PyQt6 import QtCore, QtWidgets


class Ui_StartScreen(object):
    def setupUi(self, StartScreen):
        StartScreen.setObjectName("StartScreen")
        StartScreen.setWindowTitle("Tavla Oyununa Hoş Geldiniz")
        StartScreen.setMinimumSize(470, 300)
        self.rootLayout = QtWidgets.QVBoxLayout(StartScreen)
        self.rootLayout.setContentsMargins(28, 24, 28, 24)
        self.rootLayout.setSpacing(14)

        self.lbl_title = QtWidgets.QLabel(parent=StartScreen)
        self.lbl_title.setText("Tavla Oyununa Hoş Geldiniz")
        self.lbl_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet("font-size: 22px; font-weight: bold;")
        self.rootLayout.addWidget(self.lbl_title)

        self.formLayout = QtWidgets.QFormLayout()
        self.host_edit = QtWidgets.QLineEdit(parent=StartScreen)
        self.port_edit = QtWidgets.QLineEdit(parent=StartScreen)
        self.formLayout.addRow("Sunucu IP:", self.host_edit)
        self.formLayout.addRow("Port:", self.port_edit)
        self.rootLayout.addLayout(self.formLayout)

        self.status_label = QtWidgets.QLabel(parent=StartScreen)
        self.status_label.setText("Sunucuyu başlatıp iki istemci açın.")
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.rootLayout.addWidget(self.status_label)
        self.rootLayout.addStretch()

        self.buttonRow = QtWidgets.QHBoxLayout()
        self.buttonRow.addStretch()
        self.btn_start = QtWidgets.QPushButton(parent=StartScreen)
        self.btn_start.setText("Oyuna Başla")
        self.btn_start.setMinimumSize(130, 36)
        self.buttonRow.addWidget(self.btn_start)
        self.buttonRow.addStretch()
        self.rootLayout.addLayout(self.buttonRow)
