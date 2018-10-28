import warnings
import datetime
import time  # for sleep() calls
import pickle
import traceback
import os

# Threading
import threading
from queue import Queue

# Selenium
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait  # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC  # available since 2.26.0
from selenium.common.exceptions import NoSuchElementException

warnings.simplefilter("ignore", DeprecationWarning)

# Globals
BASE_URL = 'https://www.amazon.com'
START_PAGE = 1
THREAD_COUNT = 8  # 16 Core Server
IMAGE_URL = os.path.dirname(os.path.realpath(__file__)) + '/images/'
HIDE_MAGIC = False
VERBOSE_OUTPUT = False

''' Launch Browser '''
# Run headless
options = Options()
options.headless = True
browser = webdriver.Firefox(firefox_options=options)


def amazon_login():
	"""
	Log into Amazon
	"""

	amazon_username = ''
	amazon_password = ''

	browser.get("https://www.amazon.com/gp/sign-in.html")

	element = browser.find_element_by_name("email")
	element.send_keys(amazon_username)

	element = browser.find_element_by_name("password")
	element.send_keys(amazon_password)

	element = browser.find_element_by_id("signInSubmit")
	element.click()

	''' Navigate to "Your Account" page to confirm successful login '''
	browser.get("https://www.amazon.com/gp/css/homepage.html/ref=nav_youraccount_ya")

	if browser.title == 'Your Account':
		pickle.dump(browser.get_cookies(), open("AmazonCookies.pkl", "wb"))

		return True
	else:
		return False


def start_work(item_page_url):
	""""
	Main processing function to iterate through giveaway page urls to build main item listing
	"""

	item_link = None
	item_name = None

	try:
		new_browser = webdriver.Firefox(firefox_options=options)

		new_browser.get(item_page_url)

		# Get all the prize titles
		item_links = new_browser.find_elements_by_class_name('giveAwayItemDetails')

		for item in item_links:

			# When it's an "easy" one (no interaction), save that prize title
			if 'No entry requirement' in item.get_attribute('innerHTML'):
				item_link = item.get_attribute('href')
				span_first = True
				for span in item.find_elements_by_tag_name('span'):
					if span_first:
						if 'a-size-base' in span.get_attribute('class'):
							span_first = False
							item_name = span.text

				# Add item name and link to master dictionary
				item_info_dict = {"name": item_name, "link": item_link}
				item_list.append(item_info_dict)
		
		# Close browser instance
		close_browser(new_browser)
	except BaseException as e:
		with print_lock:
			print("Oops... {}".format(repr(e)))


def enter_giveaway_for_item(item_page_url):
	"""
	Processing function to take a given item url and enter the giveaway
	"""

	try:
		options_item_browser = Options()
		options_item_browser.headless = HIDE_MAGIC
		new_browser = webdriver.Firefox(firefox_options=options_item_browser)

		# Important! For cookies to work, request needs to be on same domain.
		# Navigate to base_url first, then apply cookies to it
		new_browser.get(BASE_URL)
		for cookie in pickle.load(open("AmazonCookies.pkl", "rb")):
			new_browser.add_cookie(cookie)

		# Cookies have been applied now (logged in), so navigate to the item giveaway page
		new_browser.get(item_page_url)

		new_giveaway = None

		try:
			new_giveaway = WebDriverWait(new_browser, 15).until(EC.presence_of_element_located((By.ID,
																								"box_click_target")))
		except Exception:
			# Giveaway already attempted
			pass
			
		''' If it's a new giveaway, continue on; otherwise, jump to next giveaway link '''
		if new_giveaway is not None:

			prize_title = None

			# Get item title
			prize_title_element = new_browser.find_element_by_id('prize-name')
			if prize_title_element is not None:
				prize_title = prize_title_element.get_attribute('text')

			if prize_title is None:
				prize_title = 'Item Name Not Available'

			try:
				box_to_click = new_browser.find_element_by_id('box_click_target')
				box_to_click.click()

				# Give it time to play box opening animation
				time.sleep(10)

				giveaway_result = new_browser.find_elements_by_id('title')
				if giveaway_result:
					for element in giveaway_result:
						if "you didn't win" in element.get_attribute('innerHTML'):
							if VERBOSE_OUTPUT:
								print("¯\\_(ツ)_/¯ ...didn't win the {}".format(prize_title))
							close_browser(new_browser)
						else:
							print("٩(- ̮̮̃-̃)۶ ...possibly WON the {}".format(prize_title))

							# Grab a screenshot of the giveaway item
							new_browser.save_screenshot(IMAGE_URL + '{}_giveaway_{}_result.png'.format(datetime.date.today(), prize_title))
				else:
					if VERBOSE_OUTPUT:
						print("Hmm... didn't seem to retrieve a giveaway result")

					# Grab a screenshot of the giveaway item
					new_browser.save_screenshot(IMAGE_URL + '{}_giveaway_{}_result_error.png'.format(datetime.date.today(), prize_title))

					close_browser(new_browser)
			except NoSuchElementException:
				# Fail Gracefully
				if VERBOSE_OUTPUT:
					print("-[Visited previously-entered giveaway for {}]-".format(prize_title))
				close_browser(new_browser)
		else:
			if VERBOSE_OUTPUT:
				print("-[Visited previously-entered giveaway]-")
			close_browser(new_browser)
	except BaseException as e:
		with print_lock:
			print("Oops... {}".format(repr(e)))


def close_browser(browser_to_close=None):
	if browser_to_close is None:
		browser_to_close = browser

	''' Close the browser instance '''
	browser_to_close.close()
	browser_to_close.quit()


print_lock = threading.Lock()

q = Queue()
q_submit = Queue()

item_list = []

url_list = []


def build_url_list(START_PAGE):
	for page_number in range(START_PAGE, 2):
		url_list.append("{}/ga/giveaways?pageId={}".format(BASE_URL, page_number))


def get_items_from_url():
	while True:
		current_url = q.get()
		start_work(current_url)
		q.task_done()


# Create some threads
for i in range(THREAD_COUNT):
	t = threading.Thread(target=get_items_from_url)
	t.daemon = True
	t.start()


def enter_giveaways():
	while True:
		item_url = q_submit.get()
		enter_giveaway_for_item(item_url)
		q_submit.task_done()


# Create some threads
for i in range(THREAD_COUNT):
	t = threading.Thread(target=enter_giveaways)
	t.daemon = True
	t.start()


if __name__ == '__main__':
	# Log in first
	print("Amazon Giveaway Bot")
	print("\nKicking things off...")

	run_start = time.time()

	try:

		# Build list of item page url's
		build_url_list(START_PAGE)

		print("Building list of page urls... [Done]")

		# Put each url in a the Queue for processing
		for current_url in url_list:
			q.put(current_url)
		
		# Start the magic
		q.join()

		print("Building item list... [Done]")

		print("-[{0} items retrieved in {1:.3f} seconds]-".format(str(len(item_list)), time.time() - run_start))

		# If item_list is empty, there's no new giveaways to enter so no point logging in.
		if len(item_list) > 0:
			if amazon_login():
				print("Logging in... [Done]")

				# item_list should contain all items with their name and links
				for item in item_list:
					if 'link' in item:
						# Put each url in a the Queue for processing		
						q_submit.put(item['link'])

				# Should have a full Queue to start processing
				q_submit.join()

				# Done!
				print("Entering giveaways... [Done]")
			else:
				print("Unable to log in... shutting down")
		else:
			print("-[No new giveaways to enter]-")
	except Exception as e:
		print("That didn't work... {}".format(traceback.print_exc()))
		close_browser()

	print("Processing new giveaways... [Done]")

	print("-[{0} giveaways entered in {1:.3f} seconds]-".format(str(len(item_list)), time.time() - run_start))
	
	close_browser()
