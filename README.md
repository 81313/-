# 🟦 1. 基礎設定

```
app = Flask(__name__)
base_url = "https://qry.nfu.edu.tw/"
```
**建立 Flask Web 伺服器**  
**base_url用於補齊原網站上相對路徑的CSS或連結（因為官方網站的 CSS 大多是相對路徑，如果不修正會導致前端顯示錯誤）**

# 🟦 2. get_chrome_options() ─ 設定 Selenium 的 ChromeDriver  
此函式負責建立 Chrome 無頭模式設定。

包含：
* ✔ 無頭模式（不開視窗）
* ✔ 禁用 GPU
* ✔ 禁用 sandbox（常用於 Linux 主機）
* ✔ 禁用圖片載入（加速爬蟲查詢流程）

最重要的是：  
```
prefs = {"profile.managed_default_content_settings.images": 2}  
```
  ➡關閉圖片載入，讓 Selenium 執行更快。  
* **此函式每次建立 driver 前都會被呼叫。**

# 🟦 3. fetch_source_select_options()
用途：前端第一次載入頁面時需要學年選單與教室選單 → 由這個函式向原網站抓取。

流程：
* 🔹Step 1: 用 Selenium 開啟原網站 jclassroom.php
   因為官方網站含大量JS，因此不能單純用requests，必須用Selenium。
* 🔹Step 2: 等待兩個主要元素出現
    `
    學年 #selyr
    教室 #selclssroom
    `
    確保 JS 載入完成。
* 🔹Step 3: 抓下拉選單 HTML
```
year_html = driver.find_element(...).get_attribute("innerHTML")
room_html_raw = driver.find_element(...).get_attribute("innerHTML")
```
###### 取得整份 <option> 的 HTML，而非單純文字內容。

* 🔹 Step 4: 篩選教室選項，只保留 BGA03、BGA04、BGA05
因為這個網站是用來查「綜合工程一館」三樓~五樓的教室，因此在程式指定只留下：
    * BGA03 開頭
    * BGA04 開頭
    * BGA05 開頭  
三層樓的所有教室。

* 🔹 Step 5: 抓 head 裡的 CSS，修正成完整 URL
因為官方網站的CSS是：<link rel="stylesheet" href="css/style.css">，但如果在自己的網站直接引用會無法使用，所以透過程式逐一修改為：
```
https://qry.nfu.edu.tw/css/style.css
```  
使用 urljoin(base_url, href) 自動補完整路徑。

* 🔹 Step 6: 回傳 JSON 給前端模板
包含：
* 1.年度 <option> HTML
* 2.篩選後的教室 <option> HTML
* 3.修正後的 <head> CSS 內容

# 🟦 4. fetch_table_html(year, room)
用途：接受使用者選擇的學年/教室，向原網站查詢該教室的課表

流程：
* 🔹 1. 開啟原網站
```
driver.get("https://qry.nfu.edu.tw/jclassroom.php")
```
* 🔹 2. 等待兩個 select 元素載入
```
#selyr
#selclssroom
```
* 🔹 3. 用 JavaScript 直接設定選單值（避免觸發多餘事件）
重要設定：
```
driver.execute_script("document.getElementById('selyr').value='...';")
driver.execute_script("document.getElementById('selclssroom').value='...';")
```
直接指定值比simulate click可靠得多。
* 🔹 4. 點擊查詢按鈕
```
driver.find_element(By.ID, "bt_qry").click()
```
* 🔹 5. 等待結果表格出現
透過複合 CSS 選擇器定位：
```
table.tbcls[style*='width:1000px'][style*='margin-bottom:30px']
```
***原網站的課表表格格式就是這樣。***

* 🔹 6. 抓 head（CSS）與 table HTML
```
head_html = driver.execute_script("return document.head.innerHTML;")
table_html = table_element.get_attribute("outerHTML")
```
* 🔹 7. 修正 head 的 CSS 連結成絕對路徑
同上處理流程。
* 🔹 8. 修正表格內所有 <a href=""> 的連結
    例如：href="teacher.php?id=123"
    會變成：https://qry.nfu.edu.tw/teacher.php?id=123

* 🔹 9. 回傳資料給前端
包含 head 與 table 兩部分。

# 🟦 5. Flask 路由 /（首頁）
用途：載入頁面時自動取得來源網站的下拉選單及 CSS，並渲染前端頁面 layout.html
```
source = fetch_source_select_options()
return render_template("layout.html", ...)
```
前端頁面不直接向來源網站存取任何東西，都由後端處理。
# 🟦 6. Flask 路由 /fetch（查詢 API）
前端按下「查詢」按鈕後會用 AJAX 呼叫這個 API。
流程：
* 1.接收 year 與 room
* 2.限制 room → 避免被亂傳資料
```
if not (room.startswith("BGA03") or ...):
    return jsonify({"error": "教室代碼必須以 BGA03、BGA04 或 BGA05 開頭"})
```
* 3.呼叫 fetch_table_html()
* 4.回傳 JSON 給前端
* 🟦 7. 最後的執行條件
```
if __name__ == "__main__":
    app.run(debug=True)
``` 
