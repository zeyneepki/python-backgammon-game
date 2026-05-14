from PyQt6 import QtCore, QtWidgets


class Ui_EndScreen(object):
    def setupUi(self, EndScreen):
        EndScreen.setObjectName("EndScreen")
        EndScreen.setWindowTitle("Oyun Bitti")
        EndScreen.setFixedSize(520, 240)
        self.rootLayout = QtWidgets.QVBoxLayout(EndScreen)
        self.rootLayout.setContentsMargins(24, 24, 24, 24)
        self.rootLayout.setSpacing(18)

        self.lbl_winner = QtWidgets.QLabel(parent=EndScreen)
        self.lbl_winner.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_winner.setStyleSheet("font-size: 22px; font-weight: bold;")
        self.rootLayout.addWidget(self.lbl_winner, 1)

        self.btn_replay = QtWidgets.QPushButton(parent=EndScreen)
        self.btn_replay.setText("Tekrar Oyna")
        self.btn_replay.setMinimumHeight(36)
        self.rootLayout.addWidget(self.btn_replay, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
