import json

from ImageGen import ImageGenAsync

from gsuid_core.bot import Bot
from gsuid_core.data_store import get_res_path
from gsuid_core.logger import logger
from .base import BaseImage
from .build import IMAGE


@IMAGE.register_module()
class BingImg(BaseImage):
    def __init__(self, config=None):
        super(BingImg, self).__init__(config)

    async def _search(self, keywords, bot: Bot):
        U = self._get_random_key()

        await bot.send(f"请稍等，我正在为您创作: [{keywords}]")
        try:
            async with ImageGenAsync(U, True) as image_generator:
                images = await image_generator.get_images(keywords)
                for url in images:
                    self.send_urls.append(url)
        except Exception as e:
            logger.info(f'{type(e)}: 图片发送失败: {e}')
            if "block" in str(e):
                await bot.send('对不起，该内容不适合展示，已经被风控，换个词试试吧。')

    def init_data(self):
        self.res_path = get_res_path('GsChat')
        cookie_path = self.res_path / 'bing_cookies'
        cookie_path.mkdir(parents=True, exist_ok=True)
        cookies_files: list = [
            file
            for file in cookie_path.rglob("*.json")
            if file.stem.startswith("cookie")
        ]

        try:
            cookies = [
                json.load(open(file, "r", encoding="utf-8")) for file in cookies_files
            ]
            self.Us = []
            for cookie in cookies:
                for item in cookie:
                    if item.get("name") == "_U":
                        self.Us.append(item.get("value"))
                        break

            logger.info(f"bing_cookies读取, 初始化成功, 共{len(self.Us)}个_U")
        except Exception as e:
            logger.info(f"读取bing cookies失败 error信息: {str(e)}")
