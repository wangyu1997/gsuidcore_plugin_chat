import copy
import json
import os
import time
from pathlib import Path

import httpx

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from .base import BaseChat
from .build import CHAT
from ..utils import download_file


@CHAT.register_module()
class NormalChat(BaseChat):
    def __init__(self, config=None):
        super(NormalChat, self).__init__(config)
        self.prompt = []
        self.api_url = self.config.api_url
        self.keys = self.config.api_keys
        self.model = self.config.model
        self.proxy = self.config.proxy
        self.token_length = self.config.token_length
        self.nickname = self.config.nickname
        self.download_url = self.config.data_url
        self.person_path: Path = self.res_path / 'personalities'
        self.person_path.mkdir(parents=True, exist_ok=True)
        self.person_file: Path = self.person_path / f'{self.config.person}.json'

        self.headers = {
            'Content-Type': "application/json",
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
        }

    async def _create(self, user_id):
        current_time = int(time.time())
        self.chat_dict[user_id] = {
            "session": [],
            "last_time": current_time,
            "sessions_number": 0,
            "isRunning": False,
            'person': True
        }

    async def _ask(self, user_id, bot: Bot, event: Event):
        msg = event.text.strip()

        session = self.chat_dict[user_id]['session']
        try:
            load_person = self.chat_dict[user_id]['person']
            result = await self.normal_chat(msg, session, load_person)
            self.chat_dict[user_id]["sessions_number"] += 1
            if result is None:
                data = f"抱歉，{self.nickname}暂时不知道怎么回答你呢, 试试使用openai或者bing吧~"
                await self.create(user_id, bot, event)
            else:
                self.chat_dict[user_id]['session'].append((msg, result))
                data = result
            self.chat_dict[user_id]["isRunning"] = False
            return data

        except Exception as e:
            await bot.send(f"{type(e)}: NormalChat请求失败 {str(e)}")
            self.chat_dict[user_id]["isRunning"] = False
            return None

    async def init_data(self):
        if not os.path.exists(self.person_file):
            logger.warning(f'NormalChat 人设文件[{self.person_file.name}]不存在，已切换到默认配置')
            self.person_file: Path = self.person_path / f'{self.config.default}.json'

        if not os.path.exists(self.person_file):
            logger.info(f'NormalChat 正在下载人设文件...')
            await download_file(self.person_file, self.download_url)

        if os.path.exists(self.person_file) and str(self.person_file).endswith('.json'):
            logger.info(f'NormalChat 尝试加载人格文件: {self.person_file}')
            try:
                per_data = json.loads(
                    open(self.person_file, 'r', encoding='utf-8').read()
                )
                self.prompt.append(
                    {
                        'role': 'system',
                        'content': f'{per_data["system_prompt"].replace("_bot_name_", self.nickname)}',
                    }
                )
                for item in per_data['personality']:
                    self.prompt.append(
                        {
                            'role': 'user',
                            'content': f'{item["user"].replace("_bot_name_", self.nickname)}',
                        }
                    )
                    self.prompt.append(
                        {
                            'role': 'assistant',
                            'content': f'{item["ai"].replace("_bot_name_", self.nickname)}',
                        }
                    )
            except Exception as e:
                logger.info(f'{type(e)}: 加载人格失败 {str(e)}')

    async def normal_chat(self, msg, session=None, load_person=True):
        if not session:
            session = []

        prompt = []

        if load_person:
            prompt = copy.deepcopy(self.prompt)

        for human, ai in session:
            prompt.append({'role': 'user', 'content': human})
            prompt.append({'role': 'assistant', 'content': ai})

        prompt.append({'role': 'user', 'content': msg})

        data = {
            "messages": prompt,
            "tokensLength": self.token_length,
            "model": self.model,
        }

        proxies = {}
        if self.proxy:
            proxies = {'all://': self.proxy}

        key = self._get_random_key()
        url = self.api_url.replace('<KEY>', key)

        async with httpx.AsyncClient(
            verify=False, timeout=None, proxies=proxies
        ) as client:
            res = await client.post(url, json=data, headers=self.headers)
            res = res.json()
            message = res["choices"][0]["text"].strip()

            # 去除"nickname："
            message = message.strip()
            message = message.lstrip(f"{self.nickname}：").lstrip(f"{self.nickname}:")
            return message

    async def switch_style(self, user_id, style, bot, event):
        """
        开关人格
        :param style:
        :param user_id:
        :return:
        """
        if user_id not in self.chat_dict:
            res = await self.create(user_id, bot, event)
            if res:
                if self.config.show_create:
                    await bot.send(f'{self.config.name} 对话已创建')
            else:
                return
        self.chat_dict[user_id]['person'] = style
        self.chat_dict[user_id]['session'] = []
