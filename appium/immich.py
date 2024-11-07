from appium import webdriver
from appium.options.common.base import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy

# For W3C actions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

options = AppiumOptions()
options.load_capabilities({
	"platformName": "Android",
	"appium:options": {
        "automationName": "UiAutomator2", 
        "platformVersion": "15.0", 
        "app": "/Users/maxence/Downloads/immich.apk", 
        "deviceName": "Android Emulator", 
        "noReset": True
    },
	"appium:ensureWebviewsHavePages": True,
	"appium:nativeWebScreenshot": True,
	"appium:newCommandTimeout": 3600,
	"appium:connectHardwareKeyboard": True
})

driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

# Click on the "Next" button using content-desc
next_button = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Next")
next_button.click()
print("Clicked on the 'Next' button.")

driver.quit()
