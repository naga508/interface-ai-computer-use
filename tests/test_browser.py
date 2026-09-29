from playwright.sync_api import sync_playwright


def test_member_lookup():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("http://127.0.0.1:5000")

        page.get_by_label("Member ID").fill("12345")
        page.get_by_role("button", name="Search").click()

        page.get_by_text("Savings Balance").wait_for()

        savings_text = page.locator("body").inner_text()

        print(savings_text)

        browser.close()