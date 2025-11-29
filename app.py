# app.py
import os
from flask import Flask, request, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = Flask(__name__)
base_url = "https://qry.nfu.edu.tw/"

def get_chrome_options():
    """設定 ChromeDriver 選項，包含無頭模式與禁用圖片加速載入"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    # 禁用圖片載入加速
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    return options

def fetch_source_select_options():
    """
    從來源網站動態抓取學年與教室下拉選單的 HTML 內容。
    只保留教室中以 BGA03、BGA04、BGA05 開頭的選項。
    """
    options = get_chrome_options()
    driver = webdriver.Chrome(options=options)
    try:
        driver.get("https://qry.nfu.edu.tw/jclassroom.php")
        # 等待學年與教室下拉選單元素出現
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "selyr")))
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "selclssroom")))
        # 取得 select 元素的 innerHTML（包含所有 option）
        year_html = driver.find_element(By.ID, "selyr").get_attribute("innerHTML")
        room_html_raw = driver.find_element(By.ID, "selclssroom").get_attribute("innerHTML")
        # 篩選教室選項，只保留 BGA03、BGA04、BGA05 開頭的
        soup = BeautifulSoup(room_html_raw, "html.parser")
        filtered_options = []
        for option in soup.find_all("option"):
            val = option.get("value", "")
            if val.startswith("BGA03") or val.startswith("BGA04") or val.startswith("BGA05"):
                filtered_options.append(str(option))
        room_html = "\n".join(filtered_options)
        # 取得頁面 head 內容，方便載入來源網站 CSS
        head_html = driver.execute_script("return document.head.innerHTML;")
        # 修正 head 中所有 CSS 連結，強制改為來源網站完整路徑
        soup_head = BeautifulSoup(head_html, "html.parser")
        for link in soup_head.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if not href.startswith('http'):
                link['href'] = urljoin(base_url, href)
            else:
                link['href'] = urljoin(base_url, os.path.basename(href))
        fixed_head_html = str(soup_head)
        return {"year_html": year_html, "room_html": room_html, "head": fixed_head_html}
    finally:
        try:
            driver.quit()
        except:
            pass

def fetch_table_html(year, room):
    """
    根據使用者選擇的學年與教室，使用 Selenium 查詢課表並回傳結果。
    同時修正 CSS 與連結路徑。
    """
    options = get_chrome_options()
    driver = webdriver.Chrome(options=options)
    try:
        driver.get("https://qry.nfu.edu.tw/jclassroom.php")
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "selyr")))
        wait.until(EC.presence_of_element_located((By.ID, "selclssroom")))
        # 直接用 JS 設定下拉選單值，避免觸發多餘事件
        driver.execute_script(f"document.getElementById('selyr').value='{year}';")
        driver.execute_script(f"document.getElementById('selclssroom').value='{room}';")
        # 點擊查詢按鈕
        driver.find_element(By.ID, "bt_qry").click()
        # 等待結果表格出現
        wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR, "table.tbcls[style*='width:1000px'][style*='margin-bottom:30px']"
        )))
        # 取得 head 與表格 HTML
        head_html = driver.execute_script("return document.head.innerHTML;")
        table_element = driver.find_element(By.CSS_SELECTOR, "table.tbcls[style*='width:1000px'][style*='margin-bottom:30px']")
        table_html = table_element.get_attribute("outerHTML")
        # 修正 head 中 CSS 連結
        soup = BeautifulSoup(head_html, "html.parser")
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if not href.startswith('http'):
                link['href'] = urljoin(base_url, href)
            else:
                link['href'] = urljoin(base_url, os.path.basename(href))
        fixed_head_html = str(soup)
        # 修正表格中所有連結 href
        soup_table = BeautifulSoup(table_html, "html.parser")
        for a in soup_table.find_all("a", href=True):
            a['href'] = urljoin(base_url, a['href'])
        fixed_table_html = str(soup_table)
        return {"head": fixed_head_html, "table": fixed_table_html}
    except Exception as e:
        return {"error": str(e)}
    finally:
        try:
            driver.quit()
        except:
            pass

@app.route("/")
def index():
    """
    首頁路由，動態取得來源網站的學年與教室選項及 head CSS，
    並渲染模板。
    """
    source = fetch_source_select_options()
    year_html = source["year_html"]
    room_html = source["room_html"]
    source_head = source["head"]
    return render_template("layout.html", year_html=year_html, room_html=room_html, source_head=source_head)

@app.route("/fetch")
def fetch():
    """
    接收前端查詢請求，取得學年與教室參數，
    回傳查詢結果 JSON。
    """
    year = request.args.get("year", "")
    room = request.args.get("room", "")
    # 限制教室選項：只接受 BGA03、BGA04、BGA05 開頭的教室
    if not (room.startswith("BGA03") or room.startswith("BGA04") or room.startswith("BGA05")):
        return jsonify({"error": "教室代碼必須以 BGA03、BGA04 或 BGA05 開頭"})
    result = fetch_table_html(year, room)
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)