from flask import Flask, request, abort, jsonify # type: ignore
import serial
import subprocess
import os
import psutil
import time
import threading
import hmac
import hashlib
import asyncio
import time
import sys
import pywhatkit as kt # type: ignore
from flask_cors import CORS # type: ignore

TempHum = 0
timer_task = None
app = Flask(__name__)
mutePressed = False
volumePreMute = 50
isLoopOn = False
API_KEY = os.environ.get("MACRO_API_KEY", "")
HMAC_SECRET = os.environ.get("MACRO_HMAC_SECRET", "")
REPLAY_WINDOW_SEC = 60                                       
SEEN_NONCES = set()

CORS(app, supports_credentials=True, resources={r"/*": {
    "origins": "*",
    "allow_headers": ["Content-Type", "X-API-Key", "X-Timestamp", "X-Nonce", "X-Signature"],
    "methods": ["POST", "OPTIONS"]
}}) 

script_name = os.path.splitext(os.path.basename(__file__))[0]

sys.stdout = open(f"{script_name}.log", "a")
sys.stderr = open(f"{script_name}.err", "a")

def caesar_decrypt(ciphertext, shift):
    decrypted = ''
    for char in ciphertext:
        if char.isalpha():
            start = ord('A') if char.isupper() else ord('a')
            decrypted_char = chr((ord(char) - start - shift) % 26 + start)
            decrypted += decrypted_char
        else:
            decrypted += char
    return decrypted


def start_event_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def shut_Down_Timer():
    handle_command("MUTE")
    for i in range(4):
        handle_command("buttonFourDoubleClick")
        handle_command("buttonFiveSingleClick")
        
    handle_command("buttonFourLongPress")

async def run_timer(seconds):
    print("handling")
    try:
        await asyncio.sleep(seconds)
        await shut_Down_Timer()
    except asyncio.CancelledError:
        print("Timer was cancelled before completion.")

def start_timer(seconds):
    global timer_task
    if timer_task and not timer_task.done():
        print("Timer already running, cancelling old one.")
        timer_task.cancel()
    timer_task = asyncio.run_coroutine_threadsafe(run_timer(seconds), loop)

def cancel_timer():
    global timer_task
    if timer_task and not timer_task.done():
        print("Timer cancel requested.")
        timer_task.cancel()
    else:
        print("No active timer to cancel.")

loop = asyncio.new_event_loop()
threading.Thread(target=start_event_loop, args=(loop,), daemon=True).start()

def open_black_tab():
    url = "file:///Users/aditya/IoT/black.html"

    script = f'''
    tell application "Safari"
        activate
        tell window 1
            set newTab to make new tab at end of tabs with properties {{URL:"{url}"}}
            set current tab to newTab
        end tell
    end tell
    '''
    subprocess.run(["osascript", "-e", script])

def handleTimer(duration):
    try:
        if duration == "CancelTimer":
            cancel_timer()
        elif duration == "30MinTimer":
            (start_timer(30 * 60))
        else:
            (start_timer(60 * 60))
    except Exception as e:
        print(str(e))
        return False
    else:
        return True
        
def isnumeric(s, check):
    try:
        int(s) 
        if(check == 1):
            run_applescript('set volume output volume (' + str(s * 2) + ')')
        return True
    except ValueError:
        return False

def ytopen(query: str):
    handle_command("buttonFourDoubleClick")
    kt.playonyt(query)
    time.sleep(3)
    handle_command("buttonSixSingleClick")


def run_applescript(script):
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print("AppleScript error:", e.stderr)
        return ""

def isSafariOpen():
    for process in psutil.process_iter(attrs=["name"]):
        if process.info["name"] == "Safari":
            return True
    return False

def isYtOpen():
    script = '''
    tell application "Safari"
        repeat with w in windows
            repeat with t in tabs of w
                if (URL of t) contains "youtube.com" then return "true"
            end repeat
        end repeat
        return "false"
    end tell
    '''
    return run_applescript(script) == "true"

try:
    ser = serial.Serial("/dev/cu.usbserial-0001", 115200, timeout=0.1)
    ser.flush()
    print("Serial connected.")
except Exception as e:
    print("Serial port error:", e)
    exit()

def mute():
    global volumePreMute
    global mutePressed

    volumePreMute = run_applescript('output volume of (get volume settings)')
    mutePressed = True
    print(mutePressed)
    run_applescript('set volume output volume 0')

def handle_command(command):
    print(f"Executing: {command}")

    global isLoopOn
    global mutePressed
    global volumePreMute

    if command == "UP":
        run_applescript('set volume output volume ((output volume of (get volume settings)) + 2)')
    
    elif command == "DOWN":
        run_applescript('set volume output volume ((output volume of (get volume settings)) - 2)')

    elif command == "MUTE":
        if(mutePressed == False):
            mute()
        elif(mutePressed == True):
            if(int(run_applescript('output volume of (get volume settings)')) > 0):
                mutePressed = True
                mute()
            else:
                run_applescript('set volume output volume ' + str(volumePreMute))
                mutePressed = False

    elif command is int:
        run_applescript('set volume output volume (' + str(command) + ')')
    
    elif command == "buttonOneSingleClick":
        if isSafariOpen():
            if isYtOpen():
                script = '''osascript <<'EOF'
                tell application "Safari"
                    set foundTab to false
                    repeat with w in windows
                        repeat with t in tabs of w
                            if (URL of t) contains "youtube.com" then
                                tell t to do JavaScript "if (document.querySelector(\\"button[aria-label='Previous video']\\")) { document.querySelector(\\"button[aria-label='Previous video']\\").click(); } else { window.history.back(); }"
                                set foundTab to true
                                exit repeat
                            end if
                        end repeat
                        if foundTab then exit repeat
                    end repeat
                end tell
                EOF
                '''
                subprocess.run(script, shell=True)

                time.sleep(3)
                
                if(isLoopOn):
                    script = '''
                    tell application "Safari"
                        repeat with w in windows
                            repeat with t in tabs of w
                                if (URL of t) contains "youtube.com" then
                                    do JavaScript "document.querySelector('video').loop = !document.querySelector('video').loop;" in t
                                    exit repeat
                                end if
                            end repeat
                        end repeat
                    end tell
                    '''
                    run_applescript(script)
            else:
                os.system("open -a Safari 'https://www.youtube.com'")
        else:
            os.system("open -a Safari 'https://www.youtube.com'")

    elif command == "buttonOneDoubleClick" or command == "buttonOneLongPress":
        if isSafariOpen():
            if isYtOpen():
                os.system("open -a Safari ")
            else:
                subprocess.run(['osascript', '-e', 'tell application "Safari" to activate'])
                time.sleep(3)
                script   = '''
                tell application "Safari"   
                    set windowList to every window
                    repeat with aWindow in windowList
                        set tabList to every tab of aWindow
                        repeat with aTab in tabList
                            if (URL of aTab contains "youtube.com") then
                                set current tab of aWindow to aTab
                                set index of aWindow to 1
                                return
                            end if
                        end repeat
                    end repeat
                end tell
                '''

                subprocess.run(script, shell=True)
        else:
            os.system("open -a Safari")
    
    elif command == "buttonTwoSingleClick":
        if isSafariOpen():
            if isYtOpen():
                script = '''
                tell application "Safari"
                    repeat with w in windows
                        repeat with t in tabs of w
                            if (URL of t) contains "youtube.com" then
                                do JavaScript "document.querySelector('video').paused ? document.querySelector('video').play() : document.querySelector('video').pause();" in t
                                exit repeat
                            end if
                        end repeat
                    end repeat
                end tell
                '''
                run_applescript(script)
            else:
                os.system("open -a Safari 'https://www.youtube.com'")
        else:
            os.system("open -a steam")
    
    elif command == "buttonTwoDoubleClick" or command == "buttonTwoLongPress":
        if isSafariOpen():
            if isYtOpen():
                script = '''
                tell application "Safari"
                    repeat with w in windows
                        repeat with t in tabs of w
                            if (URL of t) contains "youtube.com" then
                                do JavaScript "document.querySelector('video').loop = !document.querySelector('video').loop;" in t
                                exit repeat
                            end if
                        end repeat
                    end repeat
                end tell
                '''
                run_applescript(script)
                if(isLoopOn):
                    isLoopOn = False
                else:
                    isLoopOn = True
            else:
                os.system("open -a Safari 'https://www.youtube.com'")
        else:
            pass
            #os.system("open -a Safari")
    
    elif command == "buttonThreeSingleClick":
        if isSafariOpen():
            if isYtOpen():
                script = '''
                tell application "Safari"
                    set foundTab to false
                    repeat with w in windows
                        repeat with t in tabs of w
                            if (URL of t) contains "youtube.com" then
                                set foundTab to true
                                tell t to do JavaScript "document.querySelector('.ytp-next-button').click();"
                                exit repeat
                            end if
                        end repeat
                        if foundTab then exit repeat
                    end repeat
                end tell
                '''
                run_applescript(script)

                time.sleep(3)

                if(isLoopOn):
                    script = '''
                    tell application "Safari"
                        repeat with w in windows
                            repeat with t in tabs of w
                                if (URL of t) contains "youtube.com" then
                                    do JavaScript "document.querySelector('video').loop = !document.querySelector('video').loop;" in t
                                    exit repeat
                                end if
                            end repeat
                        end repeat
                    end tell
                    '''
                    run_applescript(script)
            else:
                os.system("open -a Safari 'https://www.youtube.com'")
        else:
            pass
            os.system("open -a Terminal")

    elif command == "buttonFourSingleClick":
        os.system('osascript -e \'tell application "System Events" to keystroke "w" using command down\'')

    elif command == "buttonFourDoubleClick":
        os.system('osascript -e \'tell application "System Events" to keystroke "q" using command down\'')

    elif command == "buttonFourLongPress":
        os.system('osascript -e \'tell application "System Events" to quit every application\'')
        os.system('osascript -e \'tell application "System Events" to shut down\'')

    elif command == "buttonFiveSingleClick":
        running_apps_raw = os.popen("""
        osascript -e '
        tell application "System Events"
            set appList to name of (every application process whose background only is false)
        end tell
        return appList
        '
        """).read()

        apps = [app.strip() for app in running_apps_raw.strip().split(",")]
        apps = [app for app in apps if app not in ["Electron", "loginwindow", "Finder"]]
        print(apps)

        active_app = os.popen("""
        osascript -e '
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
        end tell
        return frontApp
        '
        """).read().strip()

        if active_app in apps:
            next_app = apps[(apps.index(active_app) + 1) % len(apps)]
        else:
            next_app = apps[0]

        os.system(f"osascript -e 'tell application \"{next_app}\" to activate'")


    elif command == "buttonFiveDoubleClick" or command == "buttonFiveLongPress":
        pass

    elif command == "buttonSixSingleClick":
        os.system('osascript -e \'tell application "System Events" to key code 3 using {control down, command down}\'')
    
    elif command == "buttonSixDoubleClick" or command == "buttonSixLongPress":
        os.system("pmset sleepnow")
    
    else:
        print("Unknown command:", command)

def verify_auth(req):
    if caesar_decrypt(req.headers.get("X-API-Key"),0) != API_KEY:
        abort(401, "Invalid API key")

    ts = req.headers.get("X-Timestamp")
    nonce = req.headers.get("X-Nonce")
    sig = req.headers.get("X-Signature")

    if not (ts and nonce and sig):
        abort(401, "Missing HMAC headers")

    try:
        ts = int(ts)
    except ValueError:
        abort(401, "Bad timestamp")

    now = int(time.time())
    if abs(now - ts) > REPLAY_WINDOW_SEC:
        abort(401, "Stale request")

    key = f"{ts}:{nonce}"
    if key in SEEN_NONCES:
        abort(401, "Replay detected")
    SEEN_NONCES.add(key)

    for k in list(SEEN_NONCES):
        kts = int(k.split(":")[0])
        if now - kts > REPLAY_WINDOW_SEC:
            SEEN_NONCES.discard(k)

    body = req.get_data(as_text=True) or ""
    signed = f"{ts}.{nonce}.{body}".encode()
    expected = hmac.new(HMAC_SECRET.encode(), signed, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, sig):
        abort(401, "Bad signature")

@app.post("/action")
def action():
    global TempHum 
    verify_auth(request)

    data = request.get_json(silent=True) or {}
    cmd = data.get("cmd")
    if not cmd:
        return jsonify(error="Missing cmd"), 400

    if isnumeric(cmd, 1):
        return jsonify(status="ok"), 200
    
    if(cmd[:4] == "Play"):
        if(cmd[5:] == "Black"):
            open_black_tab()
            return jsonify(status="ok"), 200    
        ytopen(cmd[3:])
        return jsonify(status="ok"), 200

    allowed = {"UP", "DOWN", "MUTE", "Weather", "30MinTimer", "1HrTimer", "CancelTimer", "buttonOneSingleClick", "buttonTwoSingleClick", "buttonThreeSingleClick", "buttonFourSingleClick", "buttonFiveSingleClick", "buttonSixSingleClick", "buttonOneDoubleClick", "buttonTwoDoubleClick", "buttonThreeDoubleClick", "buttonFourDoubleClick", "buttonFiveDoubleClick", "buttonSixDoubleClick", "buttonOneLongPress", "buttonTwoLongPress", "buttonThreeLongPress", "buttonFourLongPress", "buttonFiveLongPress", "buttonSixLongPress" }
    if cmd not in allowed:
        return jsonify(error="Unknown cmd"), 400
    
    if cmd == "Weather":
       return str(TempHum)
    
    if cmd == "30MinTimer" or cmd == "1HrTimer" or cmd == "CancelTimer":
        if handleTimer(cmd):
            return jsonify(status="ok"), 200
        return jsonify(status="error", error=str("Handle timer returned false")), 500

    try:
        handle_command(cmd)
    except Exception as e:
        return jsonify(status="error", error=str(e)), 500

    return jsonify(status="ok"), 200

def serial_loop():
    global TempHum
    while True:
        try:
            command = ser.readline().decode().strip()
            if command:
                if isnumeric(command, 0):
                    TempHum = command
                else:
                    handle_command(command)
        except Exception as e:
            print("Serial read error:", e)

if __name__ == "__main__":
    try:
        ser = serial.Serial("/dev/cu.usbserial-0001", 115200, timeout=0.1)
        ser.flush()
        print("Serial connected.")
    except Exception as e:
        print("Serial port error:", e)
        exit()

    threading.Thread(target=serial_loop, daemon=True).start()

    app.run(host="'ipaddress", port=5050, ssl_context=("cert.pem", "key.pem"), debug=True, use_reloader=False)

# nano /Users/aditya/Library/LaunchAgents/macroKeyboard.plist
