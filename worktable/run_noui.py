import os
import sys
# 1 添加项目路径到sys，作为根目录运行
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(ROOT_PATH)
# 2 兼容多账号，当前文件夹创建 .vntrader
if not os.path.exists(".vntrader"):
    os.mkdir(".vntrader")

import multiprocessing
from time import sleep
from datetime import datetime, time
from logging import INFO, DEBUG
from vnpy.trader.utility import load_json

from vnpy.event import EventEngine
from vnpy.trader.setting import SETTINGS
from vnpy.trader.engine import MainEngine

from vnpy.gateway.ctp import CtpGateway
from vnpy.app.cta_strategy import CtaStrategyApp
from vnpy.app.cta_strategy.base import EVENT_CTA_LOG

from vnpy_pro.app.cta_strategy import CtaStrategyAppPro
from vnpy_pro.tools.widget import get_logger

SETTINGS["log.active"] = True
SETTINGS["log.level"] = INFO
SETTINGS["log.console"] = True

default_logger = get_logger(
    level=SETTINGS["log.level"],
    is_console=SETTINGS["log.console"]
)
ctp_setting = load_json("connect_ctp.json")


def run_child():
    SETTINGS["log.file"] = True

    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(CtpGateway)
    cta_engine = main_engine.add_app(CtaStrategyAppPro)
    main_engine.write_log("主引擎创建成功")

    log_engine = main_engine.get_engine("log")
    event_engine.register(EVENT_CTA_LOG, log_engine.process_log_event)
    main_engine.write_log("注册日志事件监听")

    main_engine.connect(ctp_setting, "CTP")
    main_engine.write_log("连接CTP接口")

    # sleep(10)
    sleep(5)

    cta_engine.init_engine()
    main_engine.write_log("CTA策略初始化完成")

    cta_engine.init_all_strategies()
    sleep(5)
    # sleep(60)   # Leave enough time to complete strategy initialization
    main_engine.write_log("CTA策略全部初始化")

    cta_engine.start_all_strategies()
    main_engine.write_log("CTA策略全部启动")

    # cta_engine.send_report_email("账号1初始化早报")

    # cta_engine.save_all_trade_data()
    # main_engine.write_log("CTA策略实例交易数据保存成功")
    # cta_engine.update_all_daily_results()
    # main_engine.write_log("CTA策略实例资金曲线绘制成功")

    while True:
        sleep(1)


def run_parent():
    default_logger.info("[主进程]启动CTA策略守护父进程")

    DAY_START = time(8, 45)
    DAY_END = time(15, 30)

    NIGHT_START = time(20, 45)
    NIGHT_END = time(2, 45)

    child_process = None

    while True:
        current_time = datetime.now().time()
        trading = False

        if (
            (DAY_START <= current_time <= DAY_END)
            or (current_time >= NIGHT_START)
            or (current_time <= NIGHT_END)
        ):
            trading = True
        trading = True

        if trading and child_process is None:
            default_logger.info("[主进程]启动子进程")
            child_process = multiprocessing.Process(target=run_child)
            child_process.start()
            default_logger.info("[主进程]子进程启动成功")

        # 非记录时间则退出子进程
        if not trading and child_process is not None:
            default_logger.info("[主进程]关闭子进程")
            child_process.terminate()
            child_process.join()
            child_process = None
            default_logger.info("[主进程]子进程关闭成功")

        sleep(5)


if __name__ == "__main__":
    run_parent()
