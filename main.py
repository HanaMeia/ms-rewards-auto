import asyncio
import json
import os.path
from datetime import datetime

from loguru import logger
from playwright.async_api import async_playwright
import random

curent_path = os.path.dirname(os.path.abspath(__file__))

HOME_URL = 'https://rewards.bing.com/'


async def check_login(page):
    buttons_selector = ['#acceptButton','#iShowSkip','#iNext','#iLooksGood','.ext-primary.ext-button']
    for selector in buttons_selector:
        try:
            await page.wait_for_selector(selector, timeout=1000)
            await page.click(selector)
        except:
            continue
    try:
        await page.wait_for_selector('html[data-role-name="RewardsPortal"]', timeout=5000)
        return True
    except:
        return False


async def do_login(page, account,retry=0):
    await page.context.clear_cookies()
    await page.goto('https://rewards.bing.com/signin')

    email = account['email']
    await page.fill('#i0116', email)
    await page.click('#idSIButton9')

    await page.wait_for_selector('#i0118', timeout=2000)
    await page.fill('#i0118', account['password'])
    await page.click('#idSIButton9')

    is_logged_in = await check_login(page)

    if not is_logged_in:
        if retry < 3:
            logger.info(f"{email} Login failed, retrying... current retry: {retry + 1}")
            await do_login(page, account, retry + 1)
        else:
            logger.error(f"{email} Login failed, exceeded maximum retry")
            raise Exception(f"{email} Login failed, exceeded maximum retry")

async def get_last_page(page):
    await asyncio.sleep(2)
    pages = page.context.pages
    return pages[-1]


async def do_daily_set(page, account_email, dashboard_data):
    logger.info(f"{account_email} is processing daily set")

    current_time = datetime.now().strftime('%m/%d/%Y')
    daily_set_promotions = dashboard_data['dailySetPromotions'][current_time]
    uncompleted = [x for x in daily_set_promotions if not x['complete'] and x['pointProgressMax'] > 0]

    if not uncompleted:
        logger.info(f"{account_email} daily set is already completed")
        return

    await solve_activity(page, account_email, uncompleted)
    logger.info(f"{account_email} daily set is completed")
    await go_home(page)


async def solve_activity(page, account_email, uncompleted,punch_card=False):
    for activity in uncompleted:
        if activity['promotionType'] == 'urlreward':
            if 'q=' not in activity['destinationUrl']:
                logger.info(f"{account_email} {activity['name']} is not supported will be skipped")
                continue

            offer_id = activity['offerId']
            selector = f'[data-bi-id^="{offer_id}"]'

            if punch_card:
                selector = f'a[href*="{offer_id}"]'
            else:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                except:
                    name = activity['name']
                    selector = f'[data-bi-id^="{name}"]'

            await page.click(selector)

            activity_page = await get_last_page(page)
            await asyncio.sleep(2)

            await activity_page.close()
        else:
            # todo other case
            pass


async def do_more_promotions(page, account_email, dashboard_data):
    logger.info(f"{account_email} is processing more promotions")

    more_promotions = dashboard_data['morePromotions']

    if dashboard_data['promotionalItem']:
        more_promotions.append(dashboard_data['promotionalItem'])

    uncompleted = [x for x in more_promotions if
                   not x['complete'] and x['pointProgressMax'] > 0 and x['exclusiveLockedFeatureStatus'] != 'locked']

    if not uncompleted:
        logger.info(f"{account_email} more promotions are already completed")
        return

    await solve_activity(page, account_email, uncompleted)


async def main() -> None:
    with open(f'{curent_path}/data/accounts.json', 'r') as f:
        accounts = json.loads(f.read())

    for account in accounts:
        logger.info(f"{account['email']} is processing")
        await process_account(account)


async def do_punch_cards(contex, account_email, dashboard_data):
    logger.info(f"{account_email} is processing punch cards")
    pure_cards = dashboard_data['punchCards']

    uncompleted = [x for x in pure_cards if x['parentPromotion'] and not x['parentPromotion'] ['complete']]

    if not uncompleted:
        logger.info(f"{account_email} punch cards are already completed")
        return

    for card in uncompleted:
        page = await contex.new_page()
        await page.goto(card['parentPromotion']['destinationUrl'])

        child_uncompleted = [x for x in card['childPromotions'] if not x['complete']]

        await solve_activity(page, account_email, child_uncompleted, punch_card=True)


async def do_search(page, account_email, dashboard_data):
    logger.info(f"{account_email} is processing search")

    search_counter = dashboard_data['userStatus']['counters']
    generic_data = search_counter['pcSearch'][0]
    missing_point = generic_data['pointProgressMax'] - generic_data['pointProgress']

    if missing_point <= 0:
        logger.info(f"{account_email} search is already completed")
        return

    logger.info(f"{account_email} search is not completed missing point {missing_point} , starting search...")

    with open('keywords.txt', 'r') as f:
        keywords = f.read().split('\n')
    random.shuffle(keywords)

    for i in range(10):
        await page.goto('https://www.bing.com/')
        await asyncio.sleep(2)
        try:
            await page.wait_for_selector('#sb_form_q', timeout=1000)
            cookie_banner = await page.query_selector('#bnp_btn_accept')
            if cookie_banner:
                await cookie_banner.click()
        except:
            pass

        await page.fill('#sb_form_q', keywords[i])
        await page.press('#sb_form_q', 'Enter')
        await asyncio.sleep(5)

    logger.info(f"{account_email} search is completed")


async def process_account(account):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(locale='en-US')
        page = await context.new_page()

        account_email = account['email']
        cookie_path = f'{curent_path}/data/{account_email}-cookies.json'
        if os.path.exists(cookie_path):
            logger.info(f'{account_email} cookies found, loading...')
            with open(cookie_path, 'r') as f:
                cookies = json.loads(f.read())
                await context.add_cookies(cookies)

        await page.goto('https://rewards.bing.com/signin')

        is_logged_in = await check_login(page)

        if not is_logged_in:
            logger.info(f'{account_email} is not logged in, logging in...')
            await do_login(page, account)
        else:
            logger.info(f'{account_email} is already logged in.')

        await save_cookies(context, cookie_path)

        await go_home(page)

        await asyncio.sleep(2)

        dashboard_data = await get_dashboard_data(page)

        await do_daily_set(page, account_email, dashboard_data)

        await do_more_promotions(page, account_email, dashboard_data)

        await do_punch_cards(context, account_email, dashboard_data)

        await do_search(page, account_email, dashboard_data)

        await browser.close()


async def save_cookies(context, cookie_path):
    cookies = await context.cookies()
    with open(cookie_path, 'w') as f:
        f.write(json.dumps(cookies, indent=2))


async def get_dashboard_data(page):
    script_content = await page.evaluate('''() => {
                const scripts = Array.from(document.querySelectorAll('script'));
                const targetScript = scripts.find(script => script.innerText.includes('var dashboard'));
                return targetScript ? targetScript.innerText : null;
            }''')
    dashboard_data = await page.evaluate('''(scriptContent) => {
                const regex = /var dashboard = (\{.*?\});/s;
                const match = regex.exec(scriptContent);
                if (match && match[1]) {
                    return JSON.parse(match[1]);
                }
                return null;
            }''', script_content)
    return dashboard_data


async def go_home(page):
    await page.goto(HOME_URL)


asyncio.run(main())
