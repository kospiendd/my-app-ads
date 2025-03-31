# ui.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTextEdit,
    QLabel, QLineEdit, QHBoxLayout
)
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop
from trading import TradingLogic

class KiwoomApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("키움증권 종합 조회")
        self.setGeometry(300, 300, 600, 700)

        layout = QVBoxLayout()

        self.login_button = QPushButton("로그인")
        self.login_button.clicked.connect(self.login)
        layout.addWidget(self.login_button)

        self.deposit_button = QPushButton("예수금 조회")
        self.deposit_button.clicked.connect(self.request_deposit)
        layout.addWidget(self.deposit_button)

        self.balance_button = QPushButton("계좌 평가잔고 조회")
        self.balance_button.clicked.connect(self.request_balance)
        layout.addWidget(self.balance_button)

        self.stock_code_input = QLineEdit()
        self.stock_code_input.setPlaceholderText("종목코드 입력 (예: 005930)")
        layout.addWidget(self.stock_code_input)

        code_button_layout = QHBoxLayout()
        self.add_code_button = QPushButton("종목 추가")
        self.add_code_button.clicked.connect(self.add_watch_code)
        code_button_layout.addWidget(self.add_code_button)

        self.remove_code_button = QPushButton("종목 제외")
        self.remove_code_button.clicked.connect(self.remove_watch_code)
        code_button_layout.addWidget(self.remove_code_button)

        self.show_codes_button = QPushButton("감시 종목 보기")
        self.show_codes_button.clicked.connect(self.show_watch_codes)
        code_button_layout.addWidget(self.show_codes_button)

        layout.addLayout(code_button_layout)

        self.stock_info_button = QPushButton("종목 현재가 조회")
        self.stock_info_button.clicked.connect(self.request_stock_info)
        layout.addWidget(self.stock_info_button)

        self.auto_trade_button = QPushButton("자동매매 시작")
        self.auto_trade_button.clicked.connect(self.start_auto_trade)
        layout.addWidget(self.auto_trade_button)

        self.top_stocks_button = QPushButton("거래대금 상위 종목 감시")
        self.top_stocks_button.clicked.connect(self.fetch_top_trading_stocks)
        layout.addWidget(self.top_stocks_button)

        self.result_label = QLabel("결과: -")
        layout.addWidget(self.result_label)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        self.setLayout(layout)

        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.ocx.OnEventConnect.connect(self.on_event_connect)
        self.ocx.OnReceiveTrData.connect(self.on_receive_tr_data)
        self.ocx.OnReceiveRealData.connect(self.on_receive_real_data)

        self.event_loop = QEventLoop()
        self.account = ""
        self.rqname = ""
        self.logic = TradingLogic(self.ocx, self.log, self.get_account)

    def log(self, message):
        self.log_box.append(message)
        print(message)

    def get_account(self):
        return self.account

    def login(self):
        self.log("✅ 로그인 요청 중...")
        self.ocx.CommConnect()
        self.event_loop.exec_()

    def on_event_connect(self, err_code):
        if err_code == 0:
            self.log("✅ 로그인 성공")
            acc_list = self.ocx.dynamicCall("GetLoginInfo(QString)", ["ACCNO"])
            self.account = acc_list.split(";")[0]
            self.log(f"📡 계좌번호: {self.account}")
        else:
            self.log(f"❌ 로그인 실패 - 코드: {err_code}")
        self.event_loop.quit()

    def request_deposit(self):
        if not self.account:
            self.log("❌ 계좌번호가 없습니다. 먼저 로그인하세요.")
            return
        self.logic.request_deposit()

    def request_balance(self):
        if not self.account:
            self.log("❌ 계좌번호가 없습니다. 먼저 로그인하세요.")
            return
        self.logic.request_balance()

    def request_stock_info(self):
        code = self.stock_code_input.text().strip()
        if not code:
            self.log("❌ 종목 코드를 입력하세요.")
            return
        self.logic.request_stock_info(code)

    def start_auto_trade(self):
        if not self.account:
            self.log("❌ 로그인 후 자동매매 시작이 가능합니다.")
            return
        self.logic.start_auto_trade()

    def on_receive_tr_data(self, screen_no, rqname, trcode, recordname, prev_next, data_len, err_code, msg1, msg2):
        self.logic.on_receive_tr_data(rqname, trcode)

    def on_receive_real_data(self, code, real_type, real_data):
        self.logic.on_receive_real_data(code, real_type)

    def add_watch_code(self):
        code = self.stock_code_input.text().strip()
        if code:
            self.logic.add_watch_code(code)

    def remove_watch_code(self):
        code = self.stock_code_input.text().strip()
        if code:
            self.logic.remove_watch_code(code)

    def show_watch_codes(self):
        self.logic.show_watch_codes()

    def fetch_top_trading_stocks(self):
        if not self.account:
            self.log("❌ 로그인 후에 가능합니다.")
            return
        self.logic.fetch_top_trading_stocks()
        self.show_watch_codes()  # Display the currently monitored stocks
