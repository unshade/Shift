import sys
from appium import webdriver
from appium.options.common.base import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

server_ip = "http://immich.bekh.site"
server_username = "admin@admin.com"
server_password = "admin"

app_path = sys.argv[1] if len(sys.argv) > 0 else "appium/immich.apk"
options = AppiumOptions()
options.load_capabilities({
    "platformName": "Android",
    "appium:options": {
        "automationName": "UiAutomator2",
        "platformVersion": "14.0",
        "app": app_path,
        "deviceName": "Android Emulator",
        "noReset": False,
        "autoGrantPermissions": True
    },
    "appium:ensureWebviewsHavePages": True,
    "appium:nativeWebScreenshot": True,
    "appium:newCommandTimeout": 3600,
    "appium:connectHardwareKeyboard": True
})

driver = webdriver.Remote("http://127.0.0.1:4723", options=options)
wait = WebDriverWait(driver, 200)  # 200 seconds timeout

try:
    # Initial server setup
    server_button = wait.until(EC.presence_of_element_located(
        (AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().className(\"android.widget.ImageView\").instance(1)")
    ))
    server_button.click()

    # Server URL input
    server_url = wait.until(EC.presence_of_element_located(
        (AppiumBy.CLASS_NAME, "android.widget.EditText")
    ))
    server_url.click()
    server_url.send_keys(server_ip)

    # Next button
    next_button = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Next")
    ))
    next_button.click()

    # Login credentials
    email_field = wait.until(EC.presence_of_element_located(
        (AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().className(\"android.widget.EditText\").instance(0)")
    ))
    email_field.click()
    email_field.send_keys(server_username)

    password_field = wait.until(EC.presence_of_element_located(
        (AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().className(\"android.widget.EditText\").instance(1)")
    ))
    password_field.click()
    password_field.send_keys(server_password)

    # Login
    login_button = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Login")
    ))
    login_button.click()

    # Navigate to settings
    profile_button = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "A")
    ))
    profile_button.click()

    settings_button = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Settings")
    ))
    settings_button.click()

    # Backup settings
    backup_button = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Backup")
    ))
    backup_button.click()

    # Enable backup services
    foreground_backup = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Turn on foreground backup")
    ))
    foreground_backup.click()

    background_service = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Turn on background service")
    ))
    background_service.click()

    ok_button = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "OK")
    ))
    ok_button.click()

    # Navigate back
    for _ in range(2):
        back_button = wait.until(EC.element_to_be_clickable(
            (AppiumBy.ACCESSIBILITY_ID, "Back")
        ))
        back_button.click()

    # Additional backup operations
    view_element = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().className(\"android.view.View\").instance(8)")
    ))
    view_element.click()

    backup_button = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Backup")
    ))
    backup_button.click()

    # Button operations
    for _ in range(3):
        button = wait.until(EC.element_to_be_clickable(
            (AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().className(\"android.widget.Button\").instance(" + 
            ("1" if _ == 0 else "0") + ")")
        ))
        button.click()

    # Image view and additional buttons
    image_view = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().className(\"android.widget.ImageView\").instance(1)")
    ))
    image_view.click()

    button1 = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().className(\"android.widget.Button\").instance(1)")
    ))
    button1.click()

    button0 = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().className(\"android.widget.Button\").instance(0)")
    ))
    button0.click()

    # Sign out process
    profile_button = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "A")
    ))
    profile_button.click()

    sign_out_button = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Sign Out")
    ))
    sign_out_button.click()

    confirm_button = wait.until(EC.element_to_be_clickable(
        (AppiumBy.ACCESSIBILITY_ID, "Yes")
    ))
    confirm_button.click()

except TimeoutException as e:
    print(f"Timed out waiting for element: {e}")
finally:
    driver.quit()