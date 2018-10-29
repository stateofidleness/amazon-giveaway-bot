# amazon-giveaway-bot
Amazon Giveaway Bot for automated giveaway entry.

My first project in Python.

To use:
1. pip install via requirements.txt
2. Download the geckodriver.exe file from the Selenium website: https://github.com/mozilla/geckodriver/releases
3. Place the downloaded geckodriver.exe file in the root of the project folder (same level as app.py)
4. Update app.py with your Amazon login details
5. Run and enjoy!

Disclaimer:

There's some issues to work out with better exception-handling of the Selenium calls, and adding support for the giveaways that require watching a short video. Currently, this only enters those that require only clicking the animated box for entry.

Tip: You can mess with the value in build_url_list to increase speed and limit the the number of pages to iterate through.

This project is intended for educational purposes only.

Good luck with your giveaways!
