import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import sys

# 动态获取 msedgedriver 的路径
if getattr(sys, 'frozen', False):
    # EXE 打包运行时，__file__ 不可用
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))


# 全局变量
driverfile_path = os.path.join(base_path, "msedgedriver.exe")
username = ''
password = ''
log_text = None
stop_event = threading.Event()


# GUI - 登录界面
def get_login_info():
    def submit():
        global username, password
        username = entry_username.get()
        password = entry_password.get()
        if not username or not password:
            messagebox.showwarning("输入错误", "学号和密码不能为空！")
            return
        root.destroy()
        threading.Thread(target=main).start()

    root = tk.Tk()
    root.title("登录信息")

    tk.Label(root, text="学号：").grid(row=0, column=0, padx=10, pady=10)
    entry_username = tk.Entry(root)
    entry_username.grid(row=0, column=1, padx=10, pady=10)

    tk.Label(root, text="密码：").grid(row=1, column=0, padx=10, pady=10)
    entry_password = tk.Entry(root, show="*")
    entry_password.grid(row=1, column=1, padx=10, pady=10)

    tk.Button(root, text="确定", command=submit).grid(row=2, column=0, columnspan=2, pady=10)
    root.mainloop()


# GUI - 监控界面
def create_monitor_gui():
    def stop_program():
        stop_event.set()
        root.destroy()

    global log_text
    root = tk.Tk()
    root.title("运行状态监控")

    log_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=20)
    log_text.grid(row=0, column=0, padx=10, pady=10)

    tk.Button(root, text="退出程序", command=stop_program).grid(row=1, column=0, pady=10)
    root.mainloop()


# 日志输出
def log_message(message):
    if log_text:
        log_text.insert(tk.END, message + "\n")
        log_text.see(tk.END)

# 刷新页面
def info_refresh(driver, time_interval):
    driver.refresh()
    time.sleep(time_interval)

# 检查是否在允许的预约时间内
def is_within_allowed_time(area_name):
    from datetime import datetime
    current_time = datetime.now().time()
    start_time = datetime.strptime("08:30", "%H:%M").time()
    end_time = datetime.strptime("22:30", "%H:%M").time()

    if area_name in ["二层南", "二层北"]:
        return True
    return start_time <= current_time <= end_time

# 登录
def login(driver):
    driver.get('https://zjuam.zju.edu.cn/cas/login?service=https%3A%2F%2Fbooking.lib.zju.edu.cn%2Fapi%2Fcas%2Fcas')
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'username')))
    driver.find_element(By.ID, 'username').send_keys(username)
    driver.find_element(By.ID, 'password').send_keys(password)
    driver.find_element(By.ID, 'dl').click()
    log_message("登录成功！")
    time.sleep(6)

# 预约座位的函数
def reserve_seat(driver):
    try:
        X_path = '//*[@id="SeatScreening"]/div[5]/div/div/div[2]/button'
        reserve_button = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, X_path)))
        reserve_button.click()

        X_path = '//*[@id="SeatScreening"]/div[5]/div/div/div/div[1]/div[2]/div[1]/div[1]/div[2]'
        reserve_button = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, X_path)))
        reserve_button.click()

        X_path = '//*[@id="SeatScreening"]/div[5]/div/div/div/div[1]/div[2]/div[3]/div[1]'
        reserve_button = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, X_path)))
        reserve_button.click()

        try:
            X_path = '//*[@id="SeatScreening"]/div[5]/div/div/div/div[2]/button[2]'
            reserve_button = driver.find_element(By.XPATH, X_path)
            reserve_button.click()
        except Exception :
            log_message("当前状态无法预约")
            return False

        X_path = '//*[@id="SeatScreening"]/div[5]/div/div/div/div[3]/div/div/div/div[1]/div'
        confirm_button = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, X_path)))


        if confirm_button.text == '预约成功':
            return True
        else:
            return False
    except Exception as e:
        log_message(f"预约座位时发生错误: {e}")
        return False

# 监控
def monitor_area(driver):
    seat_areas = ["二层南", "二层北", "三层东", "三层南", "三层北", "四层东", "四层南", "四层西", "四层北", "五层东"]
    flag=0
    no_seats = [False] * 10
    while flag==0:
        try:
            for i in range(10):
                area_name=seat_areas[i]
                if not is_within_allowed_time(area_name):
                    log_message(f"{area_name} 当前不在允许的预约时间，跳过...")
                    continue

                area_xpath = f"//*[@id='SeatScreening']/div[3]/div[2]/div/div/div[3]/div[1]/div[2]/div[{i + 1}]/div/div[2]/div[1]/div[2]/span[2]/b"
                try:
                    area_div = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, area_xpath)))
                    remaining_seats = int(area_div.text)
                    log_message(f"{seat_areas[i]} 剩余座位：{remaining_seats}")

                    if remaining_seats > 0:
                        if i != 0:
                            reserve_button_xpath = f'//*[@id="SeatScreening"]/div[3]/div[2]/div/div/div[3]/div[1]/div[2]/div[{i + 1}]/div/div[2]/div[3]/button'
                            reserve_button = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, reserve_button_xpath)))
                            reserve_button.click()

                        if reserve_seat(driver):
                            log_message(f"{area_name} 预约成功，停止监控。")
                            return  # 成功预约，停止监控
                        else:
                            print(f"{area_name} 预约失败，继续监控。")
                            driver.back()
                            info_refresh(driver, 0.8)
                            no_seats[i] = True  # 标记当前区域没有座位
                    else:
                        log_message(f"{area_name} 没有空余座位，继续监控...")
                        no_seats[i] = True  # 标记当前区域没有座位
                except Exception as e:
                    log_message(f"监控区域 {area_name} 时发生错误: {e}")
                    info_refresh(driver,1)

            # 当所有区域都没有座位时，刷新页面
            if no_seats[0] and no_seats[1]:
                log_message("所有区域都没有座位，刷新页面...")
                info_refresh(driver, 0.8)  # 统一刷新页面
                no_seats = [False] * len(no_seats)  # 重置所有区域的座位状态，继续检查
        except Exception as e:
            log_message(f"监控过程中出现错误: {e}")


# 主运行逻辑
def main():

    threading.Thread(target=create_monitor_gui, daemon=True).start()
    try:
        service = Service(driverfile_path)
        options = Options()
        driver = webdriver.Edge(service=service, options=options)

        log_message("开始登录...")
        login(driver)

        log_message("开始监控座位...")
        driver.find_element(By.XPATH, '//*[@id="app"]/div/div/div/div[2]/div/div/div[2]/div/div[1]/div/div[1]').click()
        time.sleep(2)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "SeatScreening")))
        monitor_area(driver)
    except Exception as e:
        log_message(f"运行时发生错误: {e}")
    finally:
        driver.quit()
        log_message("程序已退出。")


# 启动程序
if __name__ == "__main__":
    get_login_info()
