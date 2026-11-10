#!python3

import sys
import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import *
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from datetime import date
import mailbox
from email.header import decode_header
import email

import datetime
import getpass
import imaplib

import tempfile
import shutil

interesting_senders = [
    '楽天特典付きキャンペーンニュース <incentive@emagazine.rakuten.co.jp>',
    'ポイントインセンティブニュース <point-g@emagazine.rakuten.co.jp>',
    '楽天カレンダーお得なニュース <calendar-info@emagazine.rakuten.co.jp>',
    'ポイントお得情報ニュース <pointo10henbai@emagazine.rakuten.co.jp>',
    'メールdeポイント <info@pointmail.rakuten.co.jp>',
    '楽天ダイヤモンド・プラチナ優待ニュース <platinum-news@emagazine.rakuten.co.jp>',
    '楽天カードショッピングニュース <shopping@mail.rakuten-card.co.jp>',
    '<info@rcp.rakuten.co.jp>',
    '<gnavi-member@gnavi.co.jp>'
]
#not interesting:
#Infoseek メールdeポイント事務局 <info@pointmail.rakuten.co.jp>

# dont include http or https as both will be checked
banner_urls = [
    "://point-g.rakuten.co.jp/mailmag/common/pg_click_banner_btn.png",
    "://point-g.rakuten.co.jp/mailmag/common/pg_click_banner_btn_2.png",
    "://point-g.rakuten.co.jp/mailmag/common/pg_click_banner_btn_3.png",
    "://image.infoseek.rakuten.co.jp/content/tmail/htmlmail/maildepoint_btn2.gif",
    "://image.pointmall.rakuten.co.jp/public/special/pointmail/2023/dreamkuji_mail/btn.png",
    "://image.pointmall.rakuten.co.jp/public/special/pointmail/programmatic/mv_300_red.png",
    "://image.pointmall.rakuten.co.jp/public/special/pointmail/programmatic/mv_300_green.png",
    "://image.pointmall.rakuten.co.jp/pointmail/tmail/htmlmail/point1.gif",
    "://event.rakuten.co.jp/incentive/ichiba/mailmag/common/clickbanner.png"
]

class MyEmail:
    def __init__(self, msgstr):
        self.body = None

        #print(msgstr)
        self.msg = email.message_from_string(msgstr)

        # extract subject and from
        self.subject, charset = email.header.decode_header(self.msg['Subject'])[0]
        if type(self.subject) != str:
            charset = 'utf-8' if not charset else charset
            self.subject = self.subject.decode(charset)

        #print(self.msg['From'])
        header_from = email.header.decode_header(self.msg['From'])

        # set FROM from header
        self.fr, charset = header_from[0]
        if type(self.fr) != str:
            charset = 'utf-8' if not charset else charset
            self.fr = self.fr.decode(charset)

        # set SENDER from header
        if len(header_from) > 1:
            sender, charset = header_from[1]
            charset = 'utf-8' if not charset else charset
            sender = sender.decode(charset)
            self.sender = sender
        else:
            self.sender = "<{}>".format(self.msg['Sender'])

        #print('Raw Date:', msg['Date'])
        # convert to local date-time
        date_tuple = email.utils.parsedate_tz(self.msg['Date'])
        if date_tuple:
            self.local_date = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
            #print("Local Date:", local_date.strftime("%a, %d %b %Y %H:%M:%S"))
        # ['Date', 'Received', 'Content-Type', 'From', 'To', 'Subject', 'Message-ID', 'Sender']
    
    def checkSenderSubject(self):
        senderchk = False
        subjectchk = False

        # check sender
        fullsender = "{} {}".format(self.fr, self.sender)
        senderchk = fullsender in interesting_senders
        #print("{}".format(fullsender))

        subjectchk = (
            ("【クリック" in self.subject and "ポイント" in self.subject)
            or ("メールdeポイント" in self.subject and self.subject.count("ポイント") >= 2)
            or "【1ポイントゲット！】" in self.subject
            or "クリックして1ポイント" in self.subject
            or "クリックで1ポイント" in self.subject
            )
        
        return senderchk, subjectchk

    def tryAnyShop(self):
        if not "text/html" in self.msg['Content-Type']:
            return None
        self.retrieveBody()
        if not ("期間中に掲載商品のいずれかをクリックしていただいた方" in self.body or "掲載店舗の商品いずれかをクリックしていただいた方" in self.body):
            print(f"not shop mail")
            return None

        for line in self.body.splitlines():
            print(line)
            if '<tr><td><img' in line and 'href' in line:
                for u in line.split('"'):
                    if "http" in u and not (".png" in u or ".gif" in u or ".jpg" in u):
                        print(f"URL detected: {u}") 
                        return u
                break
        print(f"no shop")
        return None

    def tryTextualURL(self):
        # text/html can contain this as well!!!
        #if not "text/plain" in self.msg['Content-Type']:
        #    return None
        self.retrieveBody()
        nexturl = False
        for line in self.body.splitlines():
            #print(nexturl)
            #print(line)
            #下の文字列が見つかってから最初のHTTP かつ src ではない
            if ('↓ クリックでもれなく1ポイントGet!! ↓' in line 
                or '▼楽天ポイント獲得はこちら▼' in line
                or '】ドリームくじ（' in line
                or 'ここより下↓に本文コンテンツを入れる' in line
                or 'コンテンツエリア' in line
                or 'クリックポイントここからスタート' in line
                or 'クリックで1ポイント' in line
                or 'ゲームで遊んで楽しく買って楽天ポイントGET！' in line
               ):
                nexturl = True
            elif nexturl and "http" in line: # and (not "img src" in line)の条件削除
                print(line)
                for u in line.split('"'):
                    if "http" in u and not (".png" in u or ".gif" in u or ".jpg" in u):
                        print(f"URL txt detected: {u}") 
                        return u
               #break
               # if 'href="' in line:  # text/htmlの場合 #アドレスの誤検出をしたので、httpを抽出する方法に変更
               #     test = line.split('"') #herfが見つかったので”で区切って確認
               #     print (test)
               #     line = line.split('"')[1] 
               #     print(f"URL txt detected: {line}")  # URL検出メッセージを出力
            #else:
                #nexturl = False
        print(f"no txt")
        return None

    def tryBannerURL(self):
        if not "text/html" in self.msg['Content-Type']:
            return None
        self.retrieveBody()
        banner_url = None
        for banner_url in banner_urls:
            if banner_url in self.body:
                break
        if not banner_url:
            return None
        lines = self.body.splitlines() #いったんLinesに格納
        for index, line in enumerate(lines): #enumerateでインデックス取得
            if banner_url in line:
                #print(lines[index-1])
                #print(lines[index])
                line2 = lines[index-1] + lines[index]+ lines[index+1] #urlの前後1行を追加してURL検索
                print(line2)
                for u in line2.split('"'):
                    if "http" in u and not (".png" in u or ".gif" in u or ".jpg" in u):
                        self.detected_message = u  # 検出されたメッセージを保持
                        print(f"URL banner detected: {u}")  # URL検出メッセージを出力
                        return u
                break
        print(f"no banner")
        return None
    
    def retrieveBody(self):
        if self.body:
            return
        charset = "utf-8"
        # Content-Type: text/plain; charset="utf-8"
        for pref in self.msg['Content-Type'].split():
            if "charset=" in pref:
                charset = pref.split('=')[1]
                break
        self.body = self.bodyFromMsg(self.msg).decode(charset)
        #print(self.body)  # メールの本文を出力

    def bodyFromMsg(self, b):
        body = ""
        if b.is_multipart():
            for part in b.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get('Content-Disposition'))
                # skip any text/plain (txt) attachments
                if ctype == 'text/plain' and 'attachment' not in cdispo:
                    body = part.get_payload(decode=True)  # decode
                    break
        # not multipart - i.e. plain text, no attachments, keeping fingers crossed
        else:
            body = b.get_payload(decode=True)
        return body

    def __repr__(self):
        r = ''
        if '様' in self.subject:
            r += 'Subject: {}\n'.format('<hidden for privacy>')
        else:
            r += 'Subject: {}\n'.format(self.subject)
        r += '   From: {} {}\n'.format(self.fr, self.sender)
        r += '   Date: {}'.format(self.local_date.strftime("%Y-%m-%d %H:%M"))
        return r

class MyMailbox:
    def __init__(self, server):
        self.conn = imaplib.IMAP4_SSL(server)
    def connect(self, us, pw, folder):
        self.conn.login(us, pw)
        #l = self.conn.list()
        #print(l)
        readonly = False
        ret = self.conn.select(folder, readonly)
    def close(self):
        self.conn.close()
        self.conn.logout()

    def filter(self):
        #date = (datetime.date.today() - datetime.timedelta(2)).strftime("%d-%b-%Y")
        #(res, data) = conn.search(None, ('UNSEEN'), '(SENTSINCE {0})'.format(date), '(FROM {0})'.format("calendar-info@emagazine.rakuten.co.jp".strip()))
        #(res, data) = conn.search(None, ('UNSEEN'), '(SENTSINCE {0})'.format(date))
        res, data = self.conn.search(None, ('UNSEEN'))
        if res != 'OK':
            print(res, data)
            return None
        ids = data[0].split()
        return ids

    def parseMails(self, ids, markS=False):
        interesting_count, sender_count, subject_count  = (0, 0, 0)
        fids = []
        urls = []
        for id in ids:
            rv, data = self.conn.fetch(id, '(RFC822)')
            if rv != 'OK':
                print("ERROR getting message", id)
                return -1
            # fetch seems to add \Seen flag. Undo.
            self.markUnseen(id)

            msgstr = data[0][1].decode('utf-8')
            memail = MyEmail(msgstr)

            print()
            print(memail)
            senderchk, subjectchk = memail.checkSenderSubject()
            if not senderchk and not subjectchk:
                print("  Uninteresting. SKIP.")
                continue

            interesting_count += 1
            if subjectchk:
                subject_count += 1
            if senderchk:
                sender_count += 1

            url = memail.tryBannerURL()
            if not url:
                url = memail.tryTextualURL()
                if not url:
                    url = memail.tryAnyShop()
                    if not url:
                        print(memail.body)
                        print("  no idea. check by yourself!")
                        if markS:
                            print("  Mark email as read.")
                            self.markSeen(id)
                        continue

            print("  FOUND URL.")
            urls.append(url)
            fids.append(id)

        return fids, urls, interesting_count, sender_count, subject_count

    def markUnseen(self, id):
        self.conn.store(id,'-FLAGS','\Seen')
    def markSeen(self, id):
        self.conn.store(id,'+FLAGS','\Seen')

    def markAllUnseen(self):
        """
        Mark all messages that are currently SEEN -> remove \Seen flag.
        This searches for 'SEEN' messages in the selected mailbox and
        issues a single STORE to remove the \Seen flag for the sequence set.
        """
        try:
            res, data = self.conn.search(None, 'SEEN')
            if res != 'OK':
                print("markAllUnseen: search failed:", res, data)
                return False
            if not data or not data[0]:
                print("markAllUnseen: no messages with SEEN flag found")
                return True
            ids = data[0].split()
            # build a comma-separated sequence set: "1,2,3"
            idlist = ",".join([id.decode() for id in ids])
            rv, rdata = self.conn.store(idlist, '-FLAGS', '\\Seen')
            if rv != 'OK':
                print("markAllUnseen: store failed:", rv, rdata)
                return False
            print(f"markAllUnseen: marked {len(ids)} messages as unseen")
            return True
        except Exception as e:
            print("markAllUnseen: exception:", e)
            return False

class MyChrome:
    def __init__(self):
        pass
    def prepare(self, profilepath="./chrome-profile", headless=False):
        # Chrome立ち上げ
        options = Options()
        if headless:
            options.add_argument('--headless=new')
            #options.add_argument("--no-sandbox")
            #options.add_argument('--lang=en_US')
            #options.add_argument('--window-size=1920x1080');
        options.add_argument('--user-data-dir={}'.format(profilepath))
        if os.name == "posix":
            self.chrome = webdriver.Chrome(executable_path="/usr/bin/chromedriver", options=options)
            #self.chrome = webdriver.Chrome(executable_path="./chromedriver", options=options)
        else:
            self.chrome = webdriver.Chrome(executable_path="./chromedriver.exe", options=options)

    def get(self, url):
        self.chrome.get(url)

    def shutdown(self):
        try:
            self.chrome.quit()
        except:
            pass

def click_when_uncovered(driver, locator, timeout=10):
    wait = WebDriverWait(driver, timeout)

    try:
        # ボタンが表示され、操作可能になるまで待つ
        element = wait.until(EC.element_to_be_clickable(locator))
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
            element,
        )

        # ボタンの中央を別の要素が覆っていない状態になるまで待つ
        def is_uncovered(d):
            try:
                target = d.find_element(*locator)
                if not target.is_displayed() or not target.is_enabled():
                    return False

                return d.execute_script("""
                    const el = arguments[0];
                    const rect = el.getBoundingClientRect();
                    const x = rect.left + rect.width / 2;
                    const y = rect.top + rect.height / 2;
                    const topElement = document.elementFromPoint(x, y);
                    return topElement === el || el.contains(topElement);
                """, target)
            except StaleElementReferenceException:
                return False

        wait.until(is_uncovered)
        wait.until(EC.element_to_be_clickable(locator)).click()

    except TimeoutException:
        try:
            driver.save_screenshot("login-click-intercepted.png")
            print("Timeout screenshot saved. Current URL:", driver.current_url)
        except Exception as screenshot_error:
            print("Could not save timeout screenshot:", screenshot_error)
        raise

    except ElementClickInterceptedException:
        driver.save_screenshot("login-click-intercepted.png")
        raise

def run(server, user, pw, folder, profile, rakutenPw, markS, rakutenUser):
    mail = MyMailbox(server)
    mail.connect(user, pw, folder)

    # --- ここで一旦すべての既読フラグを外して未読に戻す ---
    # 必要に応じてこの呼び出しをコメントアウト／条件付きにしてください
    #mail.markAllUnseen()
    # -----------------------------------------------------

    ids = mail.filter()
    if len(ids) > 0:
        print("Checking {} unseen emails...".format(len(ids)))
        fids, urls, interesting, sender, subject = mail.parseMails(ids, markS)

        #headless = True if len(fids) == interesting and len(fids) == sender and len(fids) == subject else False
        #headless = True if len(fids) == interesting else False
        headless = True

        print()
        print("Stats:")
        print("Total unseen emails: {}".format(len(ids)))
        print("Interesting: {} (sender: {}, subject: {})".format(interesting, sender, subject))
        print("# URLs: {}".format(len(urls)))

        if len(fids) > 0:
            if headless:
                print()
                print("RUN IN HEADLESS MODE.")
                #headless = False
            print()
            chrome = MyChrome()
            chrome.prepare(profile, headless)
            for fid, url in zip(fids, urls):
                print("Opening url...")
                print(url)
                chrome.get(url)
                # check if there is a password input field
                pwsite = chrome.chrome.find_elements_by_xpath("//input[@type=\"password\"]")
                if len(pwsite) > 0:
                    print("password field FOUND. try logging in...")
                    try:
                        uname = chrome.chrome.find_element_by_id("loginInner_u")
                        upass = chrome.chrome.find_element_by_id ("loginInner_p")
                    except NoSuchElementException:
                        try:
                            uname = chrome.chrome.find_element_by_id("u")
                            upass = chrome.chrome.find_element_by_id ("p")
                        except NoSuchElementException:
                            print('could not find element ids!')
                            return 1
                        
                    ulogin = chrome.chrome.find_element_by_class_name("loginButton")
                    if uname and upass and ulogin:
                        uname.send_keys(rakutenUser)
                        upass.send_keys(rakutenPw)
                        ulogin.click()
                    else:
                        print("LOGIN FAILED. quit.")
                        return 2

                # 新しいログイン画面の場合だけ実行
                if chrome.chrome.find_elements(By.ID, "user_id"):
                    try:
                        uname = WebDriverWait(chrome.chrome, 10).until(
                            EC.visibility_of_element_located((By.ID, "user_id"))
                        )
                    except TimeoutException:
                        print("could not find visible user_id field")
                        return 1

                    print("INPUT field FOUND. try logging in...")
                    uname.send_keys(rakutenUser)

                    def save_language_timeout_screenshot(driver, reason):
                        screenshot_path = "language-popup-not-found.png"
                        try:
                            saved = driver.save_screenshot(screenshot_path)
                            print(
                                f"Timeout screenshot saved: {screenshot_path} "
                                f"(success={saved}, reason={reason})"
                            )
                            print("Current URL:", driver.current_url)
                        except Exception as screenshot_error:
                            print("Could not save timeout screenshot:", screenshot_error)
                            
                    def save_language_screenshot(driver, reason):
                        # リトライごとに別ファイルにし、前の画像を上書きしない
                        screenshot_path = (
                            f"language-popup-{reason}-{int(time.time() * 1000)}.png"
                        )
                        try:
                            saved = driver.save_screenshot(screenshot_path)
                            print(
                                f"Screenshot saved: {screenshot_path} "
                                f"(success={saved})"
                            )
                        except Exception as screenshot_error:
                            print("Could not save screenshot:", screenshot_error)

                    # 通常DOMとShadow DOMの両方から、表示中の
                    # 「Select language」要素を探す
                    find_language_button = """
                        const normalize = value =>
                            (value || '').replace(/\\s+/g, ' ').trim().toLowerCase();

                        const roots = [document];

                        while (roots.length) {
                            const root = roots.pop();

                            for (const el of root.querySelectorAll('*')) {
                                if (el.shadowRoot) {
                                    roots.push(el.shadowRoot);
                                }

                                const label = normalize(
                                    el.innerText ||
                                    el.textContent ||
                                    el.getAttribute('aria-label')
                                );

                                if (label !== 'select language') {
                                    continue;
                                }

                                const target =
                                    el.closest(
                                        'button, [role="button"], ' +
                                        'input[type="button"], input[type="submit"]'
                                    ) || el;

                                const rect = target.getBoundingClientRect();
                                const style = window.getComputedStyle(target);

                                if (
                                    rect.width > 0 &&
                                    rect.height > 0 &&
                                    style.display !== 'none' &&
                                    style.visibility !== 'hidden' &&
                                    target.disabled !== true
                                ) {
                                    return target;
                                }
                            }
                        }

                        return null;
                    """

                    try:
                        lang_btn = WebDriverWait(chrome.chrome, 15).until(
                            lambda driver: driver.execute_script(
                                find_language_button
                            )
                        )
                        print("Language selector button detected.")
                        lang_btn.click()

                        # 言語選択後に表示されるポップアップの状態を記録する。
                        # この段階では×をクリックせず、iframeの有無を確認する。
                        time.sleep(1)

                        driver = chrome.chrome
                        screenshot_path = (
                            f"language-popup-frame-check-{int(time.time() * 1000)}.png"
                        )

                        try:
                            saved = driver.save_screenshot(screenshot_path)
                            print(
                                f"Language popup screenshot saved: "
                                f"{screenshot_path} (success={saved})"
                            )
                        except Exception as screenshot_error:
                            print(
                                "Could not save language popup screenshot:",
                                screenshot_error
                            )

                        frames = driver.find_elements(By.TAG_NAME, "iframe")
                        print(f"Language popup check: {len(frames)} iframe(s) found.")

                        for index, frame in enumerate(frames):
                            try:
                                rect = driver.execute_script(
                                    """
                                    const r = arguments[0].getBoundingClientRect();
                                    return {
                                        x: Math.round(r.x),
                                        y: Math.round(r.y),
                                        width: Math.round(r.width),
                                        height: Math.round(r.height)
                                    };
                                    """,
                                    frame
                                )

                                print(
                                    "iframe[{}]: id={!r}, name={!r}, title={!r}, "
                                    "src={!r}, displayed={}, rect={}".format(
                                        index,
                                        frame.get_attribute("id"),
                                        frame.get_attribute("name"),
                                        frame.get_attribute("title"),
                                        frame.get_attribute("src"),
                                        frame.is_displayed(),
                                        rect
                                    )
                                )
                            except Exception as frame_error:
                                print(
                                    f"Could not inspect iframe[{index}]:",
                                    frame_error
                                )
                                
                        # 「Enjoy our service in English」の文言は使わず、
                        # ポップアップ右上の小さなボタンを位置から探して閉じる。
                        close_popup_script = """
                            const visible = el => {
                                const r = el.getBoundingClientRect();
                                const s = getComputedStyle(el);
                                return r.width > 0 && r.height > 0 &&
                                       s.display !== 'none' &&
                                       s.visibility !== 'hidden' &&
                                       Number(s.opacity) > 0;
                            };

                            // 言語選択ボタンと同様に、Shadow DOM も検索する。
                            const roots = [document];
                            while (roots.length) {
                                const root = roots.pop();

                                for (const host of root.querySelectorAll('*')) {
                                    if (host.shadowRoot) {
                                        roots.push(host.shadowRoot);
                                    }
                                }

                                // ポップアップらしい領域を探す。
                                const panels = [
                                    ...root.querySelectorAll(
                                        '[role="dialog"], [aria-modal="true"]'
                                    )
                                ];

                                for (const el of root.querySelectorAll('div, section')) {
                                    if (panels.includes(el) || !visible(el)) continue;

                                    const r = el.getBoundingClientRect();
                                    const s = getComputedStyle(el);
                                    const hasPanelStyle =
                                        s.position === 'fixed' ||
                                        s.position === 'absolute' ||
                                        s.boxShadow !== 'none';

                                    if (
                                        hasPanelStyle &&
                                        r.width >= 200 &&
                                        r.height >= 100 &&
                                        r.width < window.innerWidth * 0.95 &&
                                        r.height < window.innerHeight * 0.95
                                    ) {
                                        panels.push(el);
                                    }
                                }

                                for (const panel of panels) {
                                    if (!visible(panel)) continue;

                                    const p = panel.getBoundingClientRect();
                                    const controls = [
                                        ...panel.querySelectorAll(
                                            'button, [role="button"], [tabindex], [onclick]'
                                        )
                                    ].filter(visible);

                                    // ×に相当する、ポップアップ右上の小さな操作要素を選ぶ。
                                    const candidates = controls
                                        .map(el => {
                                            const r = el.getBoundingClientRect();
                                            const nearTopRight =
                                                r.left >= p.right - 72 &&
                                                r.top <= p.top + 72;

                                            return {
                                                el,
                                                distance:
                                                    Math.abs(p.right - r.right) +
                                                    Math.abs(r.top - p.top),
                                                matches:
                                                    nearTopRight &&
                                                    r.width <= 48 &&
                                                    r.height <= 48
                                            };
                                        })
                                        .filter(item => item.matches)
                                        .sort((a, b) => a.distance - b.distance);

                                    if (candidates.length) {
                                        candidates[0].el.click();
                                        return true;
                                    }
                                }
                            }

                            return false;
                        """

                        # ポップアップの×候補を調査する。
                        # この診断ではクリックしない。
                        inspect_popup_controls = """
                            const visible = el => {
                                const r = el.getBoundingClientRect();
                                const s = getComputedStyle(el);
                                return r.width > 0 && r.height > 0 &&
                                       s.display !== 'none' &&
                                       s.visibility !== 'hidden' &&
                                       Number(s.opacity) > 0;
                            };

                            const panels = [
                                ...document.querySelectorAll(
                                    '[role="dialog"], [aria-modal="true"]'
                                )
                            ];

                            for (const el of document.querySelectorAll('div, section')) {
                                if (!visible(el)) continue;

                                const r = el.getBoundingClientRect();
                                const s = getComputedStyle(el);
                                const panelStyle =
                                    s.position === 'fixed' ||
                                    s.position === 'absolute' ||
                                    s.boxShadow !== 'none';

                                if (
                                    panelStyle &&
                                    r.width >= 200 &&
                                    r.height >= 100 &&
                                    r.width < window.innerWidth * 0.95 &&
                                    r.height < window.innerHeight * 0.95
                                ) {
                                    panels.push(el);
                                }
                            }

                            const results = [];

                            for (const panel of panels) {
                                if (!visible(panel)) continue;

                                const p = panel.getBoundingClientRect();
                                const controls = [
                                    ...panel.querySelectorAll(
                                        'button, [role="button"], [tabindex], [onclick]'
                                    )
                                ].filter(visible);

                                for (const el of controls) {
                                    const r = el.getBoundingClientRect();
                                    const nearTopRight =
                                        r.left >= p.right - 72 &&
                                        r.top <= p.top + 72;

                                    if (
                                        nearTopRight &&
                                        r.width <= 48 &&
                                        r.height <= 48
                                    ) {
                                        results.push({
                                            tag: el.tagName,
                                            text: (el.innerText || el.textContent || '')
                                                .trim()
                                                .slice(0, 100),
                                            ariaLabel: el.getAttribute('aria-label'),
                                            title: el.getAttribute('title'),
                                            className: el.getAttribute('class'),
                                            outerHTML: el.outerHTML.slice(0, 500),
                                            rect: {
                                                x: Math.round(r.x),
                                                y: Math.round(r.y),
                                                width: Math.round(r.width),
                                                height: Math.round(r.height)
                                            },
                                            panelRect: {
                                                x: Math.round(p.x),
                                                y: Math.round(p.y),
                                                width: Math.round(p.width),
                                                height: Math.round(p.height)
                                            }
                                        });
                                    }
                                }
                            }

                            return results;
                        """

                        popup_controls = chrome.chrome.execute_script(
                            inspect_popup_controls
                        )
                        print(
                            "Popup top-right control candidates:",
                            popup_controls
                        )

                        diagnostic_path = (
                            f"language-popup-controls-{int(time.time() * 1000)}.png"
                        )
                        saved = chrome.chrome.save_screenshot(diagnostic_path)
                        print(
                            f"Popup control diagnostic screenshot saved: "
                            f"{diagnostic_path} (success={saved})"
                        )

                        popup_closed = False
                        print(
                            "Diagnostic only: popup was not clicked. "
                            "Inspect the candidate list and screenshot."
                        )

                    except Exception:
                        # 検索失敗・クリック失敗のどちらでも画像を保存してから再送出
                        save_language_screenshot(
                            chrome.chrome,
                            "selector-error"
                        )
                        print("Language selector detection/click failed.")
                        raise

                    # 2) その後にNextを押す
                    click_when_uncovered(chrome.chrome, (By.ID, "cta001"))

                    # 3) Nextの後に言語ポップアップが出る場合も対応
                    try:
                        lang_btn = WebDriverWait(chrome.chrome, 15).until(
                            lambda d: next(
                                (
                                    el for el in d.find_elements(*language_button)
                                    if el.is_displayed() and el.is_enabled()
                                ),
                                None
                            )
                        )
                        print("Language popup appeared after Next. Selecting language.")
                        lang_btn.click()
                        WebDriverWait(chrome.chrome, 10).until(
                            EC.invisibility_of_element_located(language_button)
                        )
                    except TimeoutException:
                        print("No language popup after Next.")

                    # 4) パスワード入力欄を待って入力
                    upass = WebDriverWait(chrome.chrome, 15).until(
                        EC.visibility_of_element_located((By.ID, "password_current"))
                    )
                    upass.send_keys(rakutenPw)
                    click_when_uncovered(chrome.chrome, (By.ID, "cta011"))
                    
                    

#                # new site:
#                pwsite = chrome.chrome.find_elements_by_xpath("//input[@id=\"user_id\"]")
#                if len(pwsite) > 0:
#                    print("INPUT field FOUND. try logging in...")
#                    time.sleep(2)
#                    try:
#                        uname = chrome.chrome.find_element_by_id("user_id")
#                        unext = chrome.chrome.find_element_by_id("cta001")
#                    except NoSuchElementException:
#                        print('could not find element user_id or cta')
#                        return 1
#                    uname.send_keys(rakutenUser)
#                    unext.click()
#                    time.sleep(2)
#                    try:
#                        upass = chrome.chrome.find_element_by_id("password_current")
#                        ulogin = chrome.chrome.find_element_by_id("cta011")
#                        #ulogin = chrome.chrome.find_elements_by_xpath("//div[@id=\"cta\"]")[1]
#                    except NoSuchElementException:
#                        print('could not find element rakutenUser or cta2')
#                        return 1
#                    upass.send_keys(rakutenPw)
#                    ulogin.click()
#                    time.sleep(2)

                print("Mark email as read...")
                mail.markSeen(fid)
                # wait for opening web pages to complete loading
                #webdriver.support.ui.WebDriverWait(self.chrome, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
            chrome.shutdown()
            print("DONE.")
    else:
        print("No unseen mails.")

    mail.close()
    return 0

def main(args):
    # Chrome用の一時ディレクトリ作成（毎回ユニーク）
    profile = tempfile.mkdtemp(prefix='chrome-profile-')
    # ...（元の処理）...

    #profile = './chrome-profile'
    server = "imap.gmx.net"
    folder = "INBOX"
    user = "email@gmail.com"
    pw = "password"
    markS = False

    if len(args) >= 6:
        #profile = args[1]
        server = args[2]
        folder = args[3]
        user = args[4]
        pw = args[5]
        rakutenPw = args[6]
    if len(args) >= 8:
        markS = args[7] == "true" or args[7] == "True"
        rakutenUser = args[8]

    # print("{} on {}".format(user, server))
    #return run(server, user, pw, folder, profile, rakutenPw, markS, rakutenUser)
    try:
        return run(server, user, pw, folder, profile, rakutenPw, markS, rakutenUser)
    finally:
        # 終了後に一時ディレクトリを削除
        shutil.rmtree(profile, ignore_errors=True)
        
if __name__ == "__main__":
    sys.exit(main(sys.argv))
