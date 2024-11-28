import sys

from appium import webdriver
from appium.options.common.base import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy

# For W3C actions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

server_ip = "http://127.0.0.1"
server_username = "admin@admin.local"
server_password = "admin"

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
wait = WebDriverWait(driver, 10)  # 10 seconds timeout

try:
    # Use explicit wait for server button
    server_button = wait.until(EC.presence_of_element_located(
        (AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().className(\"android.widget.ImageView\").instance(1)")
    ))
    server_button.click()

    # Use explicit wait for server URL input
    server_url = wait.until(EC.presence_of_element_located(
        (AppiumBy.CLASS_NAME, "android.widget.EditText")
    ))
    server_url.click()
    server_url.send_keys(server_url)

    # Wait for and click Next button
    server_next = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Next")
    ))
    server_next.click()

    # Wait for and input email
    server_email_text = wait.until(EC.presence_of_element_located(
        (AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().className(\"android.widget.EditText\").instance(0)")
    ))
    server_email_text.click()
    server_email_text.send_keys(server_username)

    # Wait for and input password
    server_password_text = wait.until(EC.presence_of_element_located(
        (AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().className(\"android.widget.EditText\").instance(1)")
    ))
    server_password_text.click()
    server_password_text.send_keys(server_password)

    # Wait for and click Login
    server_login = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Login")
    ))
    server_login.click()

    # Wait for Backup button and click
    immich_backup_button = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Backup")
    ))
    immich_backup_button.click()

    # Wait for Select button and click
    immich_select = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Select")
    ))
    immich_select.click()

    # Wait for Recent folder and click
    recent_folder = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().description(\"Recent\n1\")")
    ))
    recent_folder.click()

    # Wait for Auto Backup switch and click
    immich_auto_backup_switch = wait.until(EC.element_to_be_clickable(
        (AppiumBy.CLASS_NAME, "android.widget.Switch")
    ))
    immich_auto_backup_switch.click()

    # Wait for Return button and click
    immich_return = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().className(\"android.widget.Button\").instance(0)")
    ))
    immich_return.click()

    # Wait for Start Backup button and click
    immich_start_backup_button = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Start Backup")
    ))
    immich_start_backup_button.click()

    # Subsequent actions with explicit waits
    immich_return.click()
    immich_backup_button.click()

    el11 = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().className(\"android.widget.Button\").instance(1)")
    ))
    el11.click()

    immich_sync_button = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Sync")
    ))
    immich_sync_button.click()

    immich_return.click()
    immich_return.click()

except TimeoutException as e:
    print(f"Timed out waiting for element: {e}")
finally:
    driver.quit()