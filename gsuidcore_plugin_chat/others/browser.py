import copy
from .build import OTHER
from contextlib import asynccontextmanager
from contextlib import suppress
from typing import Optional, Literal, Tuple, AsyncGenerator, AsyncIterator

from playwright.async_api import Page, Browser, Playwright, async_playwright, Error

from gsuid_core.logger import logger

@OTHER.register_module()
class Browser:
  def __init__(self, config=None):
    self.config = copy.deepcopy(config)
    self._playwright: Optional[Playwright] = None
    self._browser: Optional[Browser] = None 

  async def init_browser(self, **kwargs) -> Browser:
      try:
          self._playwright = await async_playwright().start()
          self._browser = await self.launch_browser(**kwargs)
      except NotImplementedError:
          logger.warning('Playwright', '初始化失败，请关闭FASTAPI_RELOAD')
      except Error:
          await install_browser()
          self._browser = await self.launch_browser(**kwargs)
      return self._browser


  async def launch_browser(self, **kwargs) -> Browser:
      assert self._playwright is not None, "Playwright is not initialized"
      return await self._playwright.chromium.launch(**kwargs)


  async def get_browser(self, **kwargs) -> Browser:
      return self._browser or await self.init_browser(**kwargs)


  async def install_browser(self):
      import os
      import sys

      from playwright.__main__ import main

      logger.info('Playwright', '正在安装 chromium')
      sys.argv = ["", "install", "chromium"]
      with suppress(SystemExit):
          logger.info('Playwright', '正在安装依赖')
          os.system("playwright install-deps")
          main()


  @asynccontextmanager
  async def get_new_page(self, **kwargs) -> AsyncGenerator[Page, None]:
      assert self._browser, "playwright尚未初始化"
      page = await self._browser.new_page(**kwargs)
      try:
          yield page
      finally:
          await page.close()


  async def screenshot(self,
                      url: str,
                      *,
                      elements = None,
                      timeout: Optional[float] = 100000,
                      wait_until: Literal["domcontentloaded", "load", "networkidle", "load", "commit"] = "networkidle",
                      viewport_size: Tuple[int, int] = (1920, 1080),
                      full_page=True,
                      **kwargs):
      if not url.startswith(('https://', 'http://')):
          url = f'https://{url}'
      viewport_size = {'width': viewport_size[0], 'height': viewport_size[1]}
      brower = await self.get_browser()
      page = await brower.new_page(
          viewport=viewport_size,
          **kwargs)
      try:
          await page.goto(url, wait_until=wait_until, timeout=timeout)
          assert page
          if not elements:
              return await page.screenshot(timeout=timeout, full_page=full_page)
          for e in elements:
              card = await page.wait_for_selector(e, timeout=timeout, state='visible')
              assert card
              clip = await card.bounding_box()
          return await page.screenshot(clip=clip, timeout=timeout, full_page=full_page, path='test.png')

      except Exception as e:
          raise e
      finally:
          if page:
              await page.close()


  @asynccontextmanager
  async def get_new_page(self,**kwargs) -> AsyncIterator[Page]:
      browser = await self.get_browser()
      page = await browser.new_page(**kwargs)
      try:
          yield page
      finally:
          await page.close()
          