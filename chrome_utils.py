import time
import und as uc
import bit_api
import driver_utils
from logger import Logger

log = Logger()


def get_driver(browserId):
    try:
        res = bit_api.openBrowser(browserId)
        driverPath = res['data']['driver']
        debuggerAddress = res['data']['http']
    except:
        log.logger.error('打开浏览器窗口失败')
        return None, None
    log.logger.info(driverPath)
    log.logger.info(debuggerAddress)

    debug_port = debuggerAddress.split(':')[-1]
    driver = get_driver_internal(int(debug_port))
    return driver, browserId

def get_driver_internal(port):
    try:
        print(port)
        driver = uc.Chrome(port=port,driver_executable_path='chrome_driver/chromedriver')
        driver.set_page_load_timeout(90)
        return driver
    except Exception as e:
        log.logger.error('启动webdriver失败，重试')
        log.logger.exception(e)
        time.sleep(1)
    return None



if __name__ == "__main__":
    driver,_ = get_driver('f190f0eaf9bc4265bfbfa60da3deed47')
    if driver:
        du = driver_utils.DriverUtils(driver)
        du.open_url('https://www.yalala.com/')
        print(driver.title)

