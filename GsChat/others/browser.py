import copy
from typing import Optional, Literal, Tuple

from gsuid_core.logger import logger
from .build import OTHER
from ..utils import BaseBrowser


@OTHER.register_module()
class Browser:
    def __init__(self, config=None):
        self.config = copy.deepcopy(config)
        self.base_browser = BaseBrowser()

    async def screenshot(self,
                         url: str,
                         *,
                         elements=None,
                         timeout: Optional[float] = 100000,
                         wait_until: Literal[
                             "domcontentloaded", "load", "networkidle", "load", "commit"] = "networkidle",
                         viewport_size: Tuple[int, int] = (1920, 1080),
                         full_page=True,
                         **kwargs):
        url = url.strip()
        if not url.startswith(('https://', 'http://')):
            url = f'https://{url}'
        viewport_size = {'width': viewport_size[0], 'height': viewport_size[1]}
        browser = await self.base_browser.get_browser()
        page = await browser.new_page(
            viewport=viewport_size,
            **kwargs)
        try:
            await page.goto(url, wait_until=wait_until, timeout=timeout)
            assert page
            if not elements:
                return await page.screenshot(timeout=timeout, full_page=full_page)

            clip = None
            for e in elements:
                card = await page.wait_for_selector(e, timeout=timeout, state='visible')
                assert card
                clip = await card.bounding_box()
            return await page.screenshot(clip=clip, timeout=timeout, full_page=full_page, path='test.png')
        except Exception as e:
            logger.error(f'screenshot fail: {str(e)}')
        finally:
            if page:
                await page.close()
