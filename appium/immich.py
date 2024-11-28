import sys

from appium import webdriver
from appium.options.common.base import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy

# For W3C actions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

app_path = sys.argv[1] if len(sys.argv) > 0 else "appium/immich.apk"
options = AppiumOptions()
options.load_capabilities({
	"platformName": "Android",
	"appium:options": {
        "automationName": "UiAutomator2", 
        "platformVersion": "13.0",
        "app": app_path, 
        "deviceName": "Android Emulator", 
        "noReset": False
    },
	"appium:ensureWebviewsHavePages": True,
	"appium:nativeWebScreenshot": True,
	"appium:newCommandTimeout": 3600,
	"appium:connectHardwareKeyboard": True
})

driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

server_button = driver.find_element(by=AppiumBy.ANDROID_UIAUTOMATOR, value="new UiSelector().className(\"android.widget.ImageView\").instance(1)")
server_button.click()
server_url = driver.find_element(by=AppiumBy.CLASS_NAME, value="android.widget.EditText")
server_url.click()
server_url.send_keys("http://10.0.2.2:2283")
server_next = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Next")
server_next.click()
server_email_text = driver.find_element(by=AppiumBy.ANDROID_UIAUTOMATOR, value="new UiSelector().className(\"android.widget.EditText\").instance(0)")
server_email_text.click()
server_email_text.send_keys("maxencebek1@gmail.com")
server_password_text = driver.find_element(by=AppiumBy.ANDROID_UIAUTOMATOR, value="new UiSelector().className(\"android.widget.EditText\").instance(1)")
server_password_text.click()
server_password_text.send_keys("admin")
server_login = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Login")
server_login.click()

immich_backup_button = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Backup")
immich_backup_button.click()
# Wait for the ui to load
sleep(1)
immich_select = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Select")
immich_select.click()

recent_folder = driver.find_element(by=AppiumBy.ANDROID_UIAUTOMATOR, value="new UiSelector().description(\"Recent\n1\")")
recent_folder.click()
immich_auto_backup_switch = driver.find_element(by=AppiumBy.CLASS_NAME, value="android.widget.Switch")
immich_auto_backup_switch.click()
immich_return = driver.find_element(by=AppiumBy.ANDROID_UIAUTOMATOR, value="new UiSelector().className(\"android.widget.Button\").instance(0)")
immich_return.click()
immich_start_backup_button = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Start Backup")
immich_start_backup_button.click()
immich_return.click()
immich_backup_button.click()

el11 = driver.find_element(by=AppiumBy.ANDROID_UIAUTOMATOR, value="new UiSelector().className(\"android.widget.Button\").instance(1)")
el11.click()

immich_sync_button = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Sync")
immich_sync_button.click()
immich_return.click()
immich_return.click()

driver.quit()
