# -*- coding:utf-8 -*-
# coding: utf-8

import os
import time
from time import sleep
import random

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common import NoSuchElementException, ElementClickInterceptedException, TimeoutException
from selenium.webdriver.remote.webelement import WebElement

from captcha_util import CaptchaUtils
from logger import Logger

log = Logger()

class DriverUtils:

    def __init__(self, driver):
        self.driver = driver
        self.captcha_util = CaptchaUtils(driver)
        self.shot_count = 0
        self.find_element_count = 0

    def open_url(self, url):
        try:
            log.logger.info(f'打开:{url}')
            self.driver.get(url)
            log.logger.info(f'打开成功:{url},{self.driver.title}')
            time.sleep(1)
            return True
        except Exception as e:
            log.logger.error(f'打开失败:{url} reason is {e}')
            self.driver.execute_script('window.stop()')
            return False

    def random_sleep(self):
        # sleep(0.1)
        sleep(1 + random.randint(0, 1) + round(random.random(), 2))

    def random_quick_sleep(self):
        sleep(1 + round(random.random(), 2))

    def is_element_exist(self, path) -> bool:
        try:
            self.driver.find_element(By.XPATH, path)
        except NoSuchElementException:
            return False
        return True

    def is_element_exist_by_class(self, class_name) -> bool:
        try:
            elements = self.driver.find_elements(By.CLASS_NAME, class_name)
        except Exception:
            return False
        return len(elements) > 0

    def is_element_exist_by_css(self, css) -> bool:
        try:
            self.driver.find_element(By.CSS_SELECTOR, css)
        except NoSuchElementException:
            return False
        return True

    def find_css_element(self, css) -> WebElement:
        if not self.is_element_exist_by_css(css):
            raise TimeoutException
        return self.driver.find_element(By.CSS_SELECTOR, css)

    def find_css_elements(self, css) -> list[WebElement]:
        if not self.is_element_exist_by_css(css):
            raise TimeoutException
        return self.driver.find_elements(By.CSS_SELECTOR, css)

    def find_element_ext(self, path) -> WebElement:
        check_count = 0
        element = None
        while not self.is_element_exist(path):
            self.captcha_util.check_captcha()
            self.accept_cookies()
            if check_count > 15:
                log.logger.error(f'获取元素失败:{path}')
                raise TimeoutException
            if check_count == 5:
                log.logger.info(f'获取元素有点慢:{path}')
            check_count = check_count + 1
            sleep(1)
        return self.driver.find_element(By.XPATH, path)

    def find_elements_ext(self, path) -> list[WebElement]:
        check_count = 0
        while not self.is_element_exist(path):
            # self.captcha_util.check_captcha()
            # self.accept_cookies()
            if check_count > 15:
                log.logger.error(f'获取元素失败:{path}')
                raise TimeoutException
            if check_count == 5:
                log.logger.error(f'获取元素有点慢:{path}')
            check_count = check_count + 1
            sleep(0.5)
        return self.driver.find_elements(By.XPATH, path)
    
    def click(self, path):
        # self.captcha_util.check_captcha()
        # self.accept_cookies()
        element = self.find_element_ext(path)
        if element:
            self.real_click(element, path)
            self.random_sleep()
            # self.captcha_util.check_captcha()
        # else:
        #     self.driver.quit()

    def real_click(self, element, path):
        try:
            element.click()
        except ElementClickInterceptedException:
            log.logger.error(f'元素点击不了:{path}')
            # self.driver.quit()

    def click_by_element(self, element):
        if element:
            # element.click()
            print("ready to click the sendButton 1")
            actions = ActionChains(self.driver)
            print("ready to click the sendButton 2")
            actions.move_to_element(element).click().perform()
            print("ready to click the sendButton 3")
            # self.random_sleep()

    def click_by_css(self, css):
        # self.captcha_util.check_captcha()
        # self.accept_cookies()
        element = self.find_css_element(css)
        if element:
            self.real_click(element, css)
            self.random_sleep()        

    def input_value(self, path, value, is_clear=False, is_direct=False):
        # self.captcha_util.check_captcha()
        # self.accept_cookies()
        element = self.find_element_ext(path)
        if is_clear:
            element.clear()
        if is_direct:
            element.send_keys(value)
        else:
            actions = ActionChains(self.driver)
            actions.move_to_element(element).click()
            actions.send_keys(value)
            actions.perform()
        self.random_sleep()
        self.captcha_util.check_captcha()

    def input_value_by_css(self, path, value, is_clear=False, is_direct=False):
        element = self.find_css_element(path)
        if is_clear:
            element.clear()
        if is_direct:
            element.send_keys(value)
        else:
            actions = ActionChains(self.driver)
            actions.move_to_element(element).click()
            actions.send_keys(value)
            actions.perform()
        # self.random_sleep()
        # self.captcha_util.check_captcha()

    def select_tiktok_birthday(self, index, random_start, random_end):
        actions = ActionChains(self.driver)
        item = self.driver.find_elements(By.XPATH, '(//*[@data-e2e="select-container"])')[index]
        actions.move_to_element(item)
        actions.click()
        actions.perform()
        self.random_sleep()
        item = self.driver.find_elements(By.XPATH, '(//*[@data-e2e="select-list"])')[index].find_elements(By.TAG_NAME, 'div')[
                random.randint(random_start, random_end)]
        actions = ActionChains(self.driver)
        actions.move_to_element(item)
        actions.click()
        actions.perform()
        self.random_sleep()

    def accept_cookies(self):
        print('accept_cookies')
        # try:
        #     shadow_host_path = '//*[@user-config-ele-id="tiktok-cookie-banner-config"]'
        #     if self.is_element_exist(shadow_host_path):
        #         shadow_host = self.find_element_ext(shadow_host_path)
        #         shadow_root = shadow_host.shadow_root
        #         shadow_root.find_elements(By.CSS_SELECTOR, 'button[type="button"]')[1].click()
        # except Exception as e:
        #     log.logger.info('点击接受cookies失败')
        #     log.logger.exception(e)
