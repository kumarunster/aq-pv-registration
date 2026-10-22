# Amelanq Netz-Anmeldung — Live-Test /installer/login

import asyncio
from playwright.async_api import async_playwright

BASE = "http://localhost:8092"

async def try_login(email, password, page_url, label):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(page_url, wait_until="networkidle")
        # E-Mail + Passwort setzen
        inputs = await page.query_selector_all("input")
        assert len(inputs) >= 2, f"{label}: nicht genug Inputs gefunden ({len(inputs)})"
        await inputs[0].fill(email)
        await inputs[1].fill(password)
        btn = await page.query_selector("button[type='submit']")
        assert btn, f"{label}: Submit-Button nicht gefunden"
        await btn.click()
        # Warten: entweder Fehlermeldung erscheint, oder Redirect
        try:
            await page.wait_for_url(f"{BASE}/installer", timeout=8000)
            status = "OK_REDIRECT"
        except Exception:
            err = await page.query_selector(".text-red-400")
            if err:
                status = "Fehler: " + (await err.inner_text()).strip()
            else:
                status = f"Unklar, aktuelle URL: {page.url}"
        await browser.close()
        return status

if __name__ == "__main__":
    res = asyncio.run(try_login(
        "installer@amelanq.com",
        "Installer1234!",
        BASE + "/installer/login",
        "Installer"
    ))
    print("Installer-Login:", res)
