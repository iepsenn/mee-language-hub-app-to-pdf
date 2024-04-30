import os
import subprocess
from time import sleep
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)


class Extractor():
    url = 'https://mee.macmillaneducation.com/'

    def __init__(self):
        load_dotenv()
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f"--force-device-scale-factor=2.0")
        chrome_options.add_argument("force-device-scale-factor=0.75")
        chrome_options.add_argument("high-dpi-support=0.75")
        self.driver = webdriver.Chrome(options=chrome_options)

    def _save_screenshot(self, driver: webdriver.Chrome, path: str = '/tmp/screenshot.png', filter: dict = {'by': By.TAG_NAME, 'value': 'body'}):
        # Ref: https://stackoverflow.com/a/52572919/
        original_size = driver.get_window_size()
        required_width = driver.execute_script('return document.body.parentNode.scrollWidth')
        required_height = driver.execute_script('return document.body.parentNode.scrollHeight')
        driver.set_window_size(required_width, required_height)
        # driver.save_screenshot(path)  # has scrollbar
        driver.find_element(**filter).screenshot(path)  # avoids scrollbar
        driver.set_window_size(original_size['width'], original_size['height'])

    def _find_element_by_xpath(self, driver: webdriver.Chrome, xpath: str):
        return driver.find_element(By.XPATH, xpath)

    def _find_element_by_id(self, driver: webdriver.Chrome, id: str):
        return driver.find_element(By.ID, id)

    def _extract_data_from_pages(self, driver: webdriver.Chrome, start_page: int, end_page: int = -1, folder: str = 'book'):
        page_number = self._find_element_by_id(driver, 'inputIdGoto')
        goto_page_button = self._find_element_by_xpath(driver, '//*[@id="gotoSubmit"]')

        page_number.clear()
        page_number.send_keys(start_page)

        # goto_page_button.click()
        driver.execute_script("arguments[0].click();", goto_page_button)

        if end_page == -1:
            total_number_of_pages_xpath = '//*[@id="ModalHeaderZoom"]/div[2]/app-goto-page/div/form/div[1]/label'
            end_page = self._find_element_by_xpath(driver, total_number_of_pages_xpath).text.split(' ')[-1]

        current_page_number_xpath = '//*[@id="inputIdGoto"]'
        current_page_number = self._find_element_by_xpath(driver, current_page_number_xpath).get_attribute('value')

        while int(current_page_number.split('-')[-1]) <= int(end_page):
            logging.info(f'Exporting data from page {current_page_number}')
            self._save_screenshot(
                driver=driver, 
                path=f'{folder}/page_{current_page_number}.png', 
                filter={'by': By.ID, 'value': 'viewer'}
            )

            sleep(3)
            if int(current_page_number.split('-')[-1]) == end_page:
                logging.info(f'Page {current_page_number} was the final page')
                break

            logging.info('=> going to next page')
            self._find_element_by_xpath(driver, '//*[@id="Next Button"]/span').click()
            current_page_number = self._find_element_by_xpath(driver, current_page_number_xpath).get_attribute('value')

            sleep(2)

    def _transform_images_into_pdf(self, folder: str = 'book'):
        # process all images into a pdf
        subprocess.run(f'img2pdf {folder}/*png -o livro.pdf',
                       shell=True, executable="/bin/bash")
        # remove temp folder
        subprocess.run('rm -rf book', shell=True, executable="/bin/bash")

    def run(self, start_page: int = 1, end_page: int = 178):
        logging.info('starting extraction...')

        logging.info('selecting macmillaneducationeverywhere login page')
        self.driver.get(self.url)

        logging.info("accepting cookies")
        xpath = '/html/body/dialog/div/div/div[2]/button'
        self._find_element_by_xpath(self.driver, xpath).click()
        sleep(3)

        logging.info('going to login page')
        xpath = '//*[@id="Primary2"]'
        self._find_element_by_xpath(self.driver, xpath).click()
        sleep(3)

        logging.info('filling login form and entering the app')
        username = os.environ.get('USERNAME')
        password = os.environ.get('PASSWORD')

        login_user = self._find_element_by_id(self.driver, "username")
        login_password = self._find_element_by_id(self.driver, "password")
        login_button = self._find_element_by_xpath(self.driver, '//*[@id="main-content"]/div/form/p/button')

        login_user.send_keys(username)
        login_password.send_keys(password)
        login_button.click()

        sleep(5)

        logging.info('confirming the dialog')
        xpath = '//*[@id="Yes"]'
        try:
            self._find_element_by_xpath(self.driver, xpath).click()
        except Exception:
            logging.error('error to accept dialog')

        logging.info('skip´ping onboarding modal')
        xpath = '//*[@id="skip-onboarding-modal"]'
        try:
            self._find_element_by_xpath(self.driver, xpath).click()
        except Exception:
            logging.error('error to skip onboarding')

        sleep(3)

        logging.info('selecting the book')
        xpath = '//*[@id="aob4k6ajijrd5yk8nd2u"]'
        self._find_element_by_xpath(self.driver, xpath).click()

        sleep(3)

        logging.info('opening app in the web')
        xpath = '//*[@id="MACXPD-n3t8sdfm40yd9"]'
        self._find_element_by_xpath(self.driver, xpath).click()

        sleep(3)

        logging.info('defining a better resolution to save images')
        dx, dy = self.driver.execute_script("var w=window; return [w.outerWidth - w.innerWidth, w.outerHeight - w.innerHeight];")
        self.driver.set_window_size(3840 + dx, 2160 + dy)
        
        logging.info('creating temp folder to save images')
        os.makedirs('book', exist_ok=True)

        # import pdb; pdb.set_trace()
        logging.info('>>>>> starting <<<<<')
        self._extract_data_from_pages(self.driver, start_page, end_page)

        # self._transform_images_into_pdf()

        self.driver.quit()


if __name__ == '__main__':
    extractor = Extractor()
    extractor.run()
