# trading.py
class TradingLogic:
    def __init__(self, ocx, log_fn, get_account_fn):
        self.ocx = ocx
        self.log = log_fn
        self.get_account = get_account_fn
        self.watch_targets = set()
        self.watch_list = {}  # {code: {'price': price, 'volume': volume, 'amount': amount}}
        self.daily_high = {}  # {code: high_price}
        self.order_conditions = {}  # {code: {'high_price': price, 'sell_wall': amount, 'buy_volume': volume}}

    def set_common_input(self):
        account = self.get_account()
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "계좌번호", account)
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "비밀번호", "")
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "조회구분", "1")
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "거래소구분", "KRX")

    def request_deposit(self):
        self.set_common_input()
        self.ocx.dynamicCall("CommRqData(QString, QString, int, QString)",
                             "예수금조회", "opw00001", 0, "1000")

    def request_balance(self):
        self.set_common_input()
        self.ocx.dynamicCall("CommRqData(QString, QString, int, QString)",
                             "계좌평가잔고내역", "opw00018", 0, "2000")

    def request_stock_info(self, code):
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.ocx.dynamicCall("CommRqData(QString, QString, int, QString)",
                             "주식기본정보조회", "opt10001", 0, "3000")
        # 당일 고가 조회
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "기준일자", "20240319")  # 당일
        self.ocx.dynamicCall("CommRqData(QString, QString, int, QString)",
                             "일별주가요청", "opt10081", 0, "3001")

    def start_auto_trade(self):
        self.set_common_input()
        self.ocx.dynamicCall("CommRqData(QString, QString, int, QString)",
                             "자동매매시작확인", "opw00001", 0, "9000")
        self.log("🚀 자동매매 시작됨!")
        for code in self.watch_targets:
            self.ocx.dynamicCall("SetRealReg(QString, QString, QString, QString)",
                                 "5000", code, "41;61;10", "1")
            self.log(f"👀 감시 등록: {code}")

    def on_receive_tr_data(self, rqname, trcode):
        if rqname == "예수금조회":
            deposit = self.ocx.dynamicCall(
                "GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "예수금").strip()
            self.log(f"✅ 예수금: {deposit} 원")
        elif rqname == "계좌평가잔고내역":
            asset = self.ocx.dynamicCall(
                "GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "추정예탁자산").strip()
            profit = self.ocx.dynamicCall(
                "GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "총평가손익금액").strip()
            self.log(f"✅ 추정자산: {asset} 원, 평가손익: {profit} 원")
        elif rqname == "주식기본정보조회":
            name = self.ocx.dynamicCall(
                "GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "종목명").strip()
            price = self.ocx.dynamicCall(
                "GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "현재가").strip()
            self.log(f"✅ {name} 현재가: {price} 원")
        elif rqname == "거래대금상위요청":
            for i in range(50):  # Top 50 stocks
                code = self.ocx.dynamicCall(
                    "GetCommData(QString, QString, int, QString)", trcode, rqname, i, "종목코드").strip()
                name = self.ocx.dynamicCall(
                    "GetCommData(QString, QString, int, QString)", trcode, rqname, i, "종목명").strip()
                amount = self.ocx.dynamicCall(
                    "GetCommData(QString, QString, int, QString)", trcode, rqname, i, "거래대금").strip()
                current_price = self.ocx.dynamicCall(
                    "GetCommData(QString, QString, int, QString)", trcode, rqname, i, "현재가").strip()
                price_change = self.ocx.dynamicCall(
                    "GetCommData(QString, QString, int, QString)", trcode, rqname, i, "등락률").strip()
                
                # 거래대금을 억 단위로 변환
                amount_bil = float(amount) / 100000000 if amount else 0
                price_change_float = float(price_change) if price_change else 0

                # 등락률이 10% 이상인 종목만 추가
                if price_change_float >= 10.0:
                    self.add_watch_code(code)
                    self.log(f"✅ {name} ({code}) - 현재가: {current_price}원, 거래대금: {amount_bil:.2f}억, 등락률: {price_change_float:.2f}%")
        elif rqname == "일별주가요청":
            code = self.ocx.dynamicCall(
                "GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "종목코드").strip()
            high_price = self.ocx.dynamicCall(
                "GetCommData(QString, QString, int, QString)", trcode, rqname, 0, "고가").strip()
            self.daily_high[code] = float(high_price)
            self.log(f"📊 {code} 당일 고가: {high_price}원")
        else:
            # Existing logic
            super().on_receive_tr_data(rqname, trcode)

    def on_receive_real_data(self, code, real_type):
        if real_type == "주식호가잔량":
            for i in range(10):
                price = abs(int(self.ocx.dynamicCall("GetCommRealData(QString, int)", code, 41 + i).strip()))
                volume = int(self.ocx.dynamicCall("GetCommRealData(QString, int)", code, 61 + i).strip())
                amount = price * volume
                
                # 매도호가에 2억원 이상의 물량이 있고, 해당 가격이 당일 고가인 경우
                if amount >= 200000000 and price == self.daily_high.get(code, 0):
                    self.log(f"📌 {code} 매도호가 {i+1}단계: {price}원, 물량 {volume}주 → {amount:,}원 (당일고가)")
                    self.watch_list[code] = {'price': price, 'volume': volume, 'amount': amount}
                    break

        elif real_type == "주식체결":
            if code in self.watch_list:
                current_price = abs(int(self.ocx.dynamicCall("GetCommRealData(QString, int)", code, 10).strip()))
                volume = int(self.ocx.dynamicCall("GetCommRealData(QString, int)", code, 15).strip())
                amount = current_price * volume
                
                # 매수체결이 3천만원 이상인 경우
                if amount >= 30000000:
                    self.log(f"💰 {code} 매수체결 발생: {current_price}원, {volume}주 → {amount:,}원")
                    self.order_conditions[code] = {
                        'high_price': self.watch_list[code]['price'],
                        'sell_wall': self.watch_list[code]['amount'],
                        'buy_volume': volume
                    }
                
                # 매도호가 돌파 확인
                if current_price > self.watch_list[code]['price']:
                    self.log(f"🚨 돌파 감지! {code} 현재가 {current_price}원이 감시가격 {self.watch_list[code]['price']}원을 초과")
                    self.send_order(code, 1)
                    del self.watch_list[code]
                    if code in self.order_conditions:
                        del self.order_conditions[code]

    def send_order(self, code, qty):
        account = self.get_account()
        self.log(f"📤 매수주문: {code} - {qty}주 (시장가)")
        self.ocx.dynamicCall(
            "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
            "자동매수", "6000", account, 1, code, qty, 0, "03", "")  # 03: 시장가

    def add_watch_code(self, code):
        self.watch_targets.add(code)
        self.log(f"✅ 감시 종목 추가됨: {code}")

    def remove_watch_code(self, code):
        if code in self.watch_targets:
            self.watch_targets.remove(code)
            self.log(f"❎ 감시 종목 제외됨: {code}")
        else:
            self.log(f"⚠️ 감시 목록에 없는 종목입니다: {code}")

    def show_watch_codes(self):
        if self.watch_targets:
            self.log("📋 현재 감시 중인 종목:")
            for code in self.watch_targets:
                self.log(f" - {code}")
        else:
            self.log("📭 감시 목록이 비어 있습니다.")

    def fetch_top_trading_stocks(self):
        # Request top trading amount stocks
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "시장구분", "000")  # 전체
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "기간", "1")  # 당일
        self.ocx.dynamicCall("CommRqData(QString, QString, int, QString)",
                             "거래대금상위요청", "OPT10032", 0, "4000")
