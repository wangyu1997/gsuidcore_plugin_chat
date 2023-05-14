<p align="center">
  <a href="https://github.com/KimigaiiWuyi/GenshinUID/"><img src="https://s2.loli.net/2023/03/25/bareSdYcsmRPOyZ.png" width="256" height="256" alt="GenshinUID"></a>
</p>
<h1 align = "center">GenshinUID Core Chat 2.0</h1>
<h4 align = "center">✨支持OneBot(QQ)、QQ频道、微信、开黑啦、Telegram的全功能原神Bot插件✨</h4>

<div>
  <img src="https://i.328888.xyz/2023/03/30/iCsDVw.md.png" width="24%" height="auto">
  <img src="https://i.328888.xyz/2023/03/30/iCsy3q.md.png" width="24%" height="auto">
  <img src="https://i.328888.xyz/2023/03/30/iCsUba.md.png" width="24%" height="auto">
  <img src="https://i.328888.xyz/2023/03/30/iCsn6x.md.jpeg" width="24%" height="auto">
</div>


# 基于gsuid_core的智能聊天插件(理论兼容多个平台)

    使用前请务必看完readme, 这是一个融合了openai, newbing, 词库的智能回复插件



# 安装

* 手动安装
  ```
    cd gsuid_core/gsuid_core/plugins
    git clone https://github.com/wangyu1997/gsuidcore_plugin_chat.git
    cd gsuidcore_plugin_chat
    poetry run pip install -r requirements.txt
  ```


# 配置文件

配置文件位于gscore根目录的`data`文件夹下的config.yaml (初次运行后会自动创建)：

配置说明如下：

```
chat: #聊天模块
  Bing: 
    cd_time: 120 # bing重置的CD, 下同
    proxy: '' # bing的代理,国内部署需配置, 下同
    style: creative # bing的风格 支持 [creative/balanced/precise]
    show_create: true # 是否跳过创建新回话的提示 下同
  Normal:
    api_keys: # 普通聊天的key, 可以从leyoyu.cn获取
    - xxxxx
    nickname: Paimon # 机器人昵称
    person: miao # 默认加载人格，可在data/personality中替换文件
    proxy: http://xxx # 国内代理，国外访问不了
    show_create: false
  Openai:
    api_keys: # api key 可以配置多条
    - xxxx
    max_tokens: 1000 # 最发返回token数量
    show_create: true
  default: chat # 默认聊天引擎 [chat/bing/openai]
genshin:
  material:
    push_time: '4:10' # 材料推送时间
    skip_three: false # 是否跳过三星武器
image:
  FilckrImg:
    api_keys: # filckr api 
    - xxxx
    cnt: 5 # 默认返回的图片最大数量 下同
  WebSearchImg:
    api_keys: # websearch api 
    - xxx
  align_prompt: 帮我生成一个适配<QUERY>的英文搜索文本，直接返回文本，不需要额外的文字： # 用chatgpt转译查询prompt
  default: filckr # 默认插图引擎 [filckr/websearch]
other:
  setereo:
    data: default.data # 用户自定义发病语录
  song:
    api: https://netease-cloud-music-api-git-master-wangyu1997.vercel.app
  todo:
    push_time: 30 # 开始推送的最小时间（默认30分钟，如有任务在30分钟内ddl，则触发提醒）

```

# 使用方法


- [bing|openai|chat xxx]  (使用bing/openai/国内chatgpt的聊天服务)
- [@bot xxx]或私聊xxx (调用当前默认引擎回复)
- [切换引擎bing|openai|chat] (切换默认聊天(群聊或私聊)引擎)
- [切换模式|cm] (切换群内聊天模式,群聊模式可以所有群员共享一个session)
- [查看引擎|ce] (查看当前的聊天模式)
- [重置对话|reset]  (重置当前的聊天模式)

- [搜图 xxx]  (调用搜图引擎进行关键词搜索图片)
- [转搜图 xxx]  (搜图之前调用chatgpt进行query对齐)
- [切换搜图 filckr|websearch]  (切换搜图引擎)
- [查看搜图]  (查看当前的搜图引擎)

- [截图|网页截图 url]  (获取url截图)
- [发病 xxx]  (返回发病语录)

- [材料 [周一|今天|空]]  (获取材料)
- [周本 [周一|今天|空]]  (获取周本)
- [计算 艾尔海森 80-90 0-9 9 10 ]  (获取升级所需资源)
- [推送材料提醒]  (手动推送材料提醒到私聊或者群聊 需要超管)
- [（删除）订阅材料]  (订阅或关闭私聊或者群聊的材料提醒 需要超管)

- [提醒xxxx]  (增加提醒 如 提醒我明天上午九点吃饭)
- [删除提醒xxx]  (删除提醒 如 删除提醒吃饭)

- [点歌 xxx]  (从网易云获取第一首可以下载的歌曲)
- [画图 xxx]  (调用BingAI的ImageCreator模块创作4张图片 本质是Dell-E)


- [@xxx (设置)昵称 xxx]  (账单模块 为某个人设置一个昵称)
- [创建账单|重置账单]  (账单模块 在群聊中清空账单)
- [@xx@xx@xx 账单 烧烤 200]  (账单模块 在群聊中创建新的项目并将@的所有人添加为平摊者)
- [撤销账单]  (账单模块 撤销本人支出的上一笔账单)
- [我的账单]  (账单模块 查看我的支出项目)
- [清算]  (账单模块 通过创建的账单开始结算每个人应该给其他人转账多少)
- [今日账单]  (账单模块 查看今日账单)





# 注意事项

## 关于获取网页截图:

    如果playwright出现报错的话，请自行升级内核或者更换playwright版本


## 关于聊天:

    1. 国内聊天
    
        基于公共api获取回复，如果不配置openai和bing，不影响本功能使用。
        简单对话自动调用默认配置回复（下同）。

        注意：如果服务器在国外，并且使用了pandapy的服务，需要自己搭建国内http代理，并且配置chat_proxy


    2. bing

        0. 也许需要科学上网, 代理配置详细请看下文
        1. 使用功能必须配置cookie, 否则无法使用, 这个cookie内容过多不适合在.env, 所以这个cookie将会与json文件的形式进行配置
        2. 首先你需要一个通过申请的账号, 使用edge浏览器安装"editthiscookie"浏览器插件, 或者使用相关的其他插件获取cookie. 进入"bing.com/chat"登录通过的账号
        3. 右键界面选择"editthiscookie", 找到一个看上去像出门的样子的图标"导出cookie", cookie一般就能在你的剪贴板, 注意了, cookie导出来是一个list, 大概长这样[{},{},{}]
        4. 新建cookiexxx.json文件(xxx为任意合法字符), 把你剪贴板的cookie的字符串粘贴进去, 再次强调json大概长[{},{},{}]这样
        5. 打开你bot项目文件夹, 依次进入data/cookies, 没有就新建, 把json文件丢进去, 有几个账号可以放几个, 要求cookie开头, .json结尾, 载入插件时初始化会全部读取, 创建会话的时候会通过random来选择一个账号的cookie
        6. 注意观察加载插件的时候, log会提示你加载了几个cookie
        7. 尽量保证EdgeGPT模块是最新(pip install EdgeGPT --upgrade)

        使用了与Bing通讯的接口 [EdgeGPT](https://github.com/acheong08/EdgeGPT)  

    3. openai
        1. openai_api_key请注册openai后在 https://beta.openai.com/account/api-keys 自己获取
        2. openai_max_tokens貌似是ai返回的文本最大多少(根据我自己用的经验)
        3. openai_api_key必须配置, openai_max_tokens随意, 有默认值(1000)
        4. 需要配置代理, 否则无法使用, 代理配置详细请看下文
        5. 这个模块貌似不是免费的, 注册的账号只有$18.00的免费额度(现在缩成了5刀??), 请注意使用
        6. openai_api_key要求你填的是list, 创建会话的时候会随机从list选一个, 你可以填多个, 注意观察加载插件的时候, log会提示你加载了几个apikey
        7. 尽量保证revChatGPT模块是最新(pip install revChatGPT --upgrade)

        使用了与openai通讯的接口 [ChatGPT](https://github.com/acheong08/ChatGPT)  
    
    4. bing和openai的proxy配置
        1. 你需要使用v2ray或者clash等代理工具开启本地监听端口
        2. 根据http和socks5的不同, 配置不同, 
        3. 以v2rayN举例, 本地监听端口1080, 你应该配置成"socks5://127.0.0.1:1080"或者"http://127.0.0.1:1081"




## 关于图片搜索:

    1.基于Flickr的关键词搜索，默认搜索500张并随机发送三张。

    api key的获取方式: https://www.flickr.com/services/apps/create/noncommercial/

    
    2.基于Web Image Search的关键词搜索，每天固定100次免费搜索。

    注意，Web Image Search对英文query支持好，为了更好的搜索，首先使用chatgpt默认的国内对齐英文实体，再进行查询。如果要使用本功能，请先配置chat功能。
    
    api key的获取方式: https://rapidapi.com/contextualwebsearch/api/web-search

    3. align_prompt可以自己修改prompt, 用<QUERY>占位即可

## 关于提醒:

    1.提醒时间和事件基于chatgpt解析，请先配置好国内的chatgpt方可使用

    2.名字相同的提醒事项只能添加一次，会根据添加提醒的群组或私聊，推送到对应的地方

    3. 默认十分钟检查并推送一次

## 关于点歌:

    1. 推荐使用自己的Vercel部署网易云api 参考: https://github.com/Binaryify/NeteaseCloudMusicApi

    2. 默认下载列表可以获取mp3的第一首歌曲，并发送歌曲信息和文件（由于wechat限制，没法发送语音）



## 关于画图:

    1. 使用的BingAI的ImageCreator创作图片，只需要使用`画图 你的描述`即可


## 关于账单:

    1. 该模块是本人在旅行途中方便大家AA临时写的模块，使用过程中可能会有bug，但是只要添加项目成功，金额不会算错，还存在BUG，尚未修复

    2. 因为GsCore无法获取wechat好友的nickname，为了方便起见，先使用`昵称`指令，该命令会在群聊账单中为at的好友创建一个wxid->nickname的映射，方便清算和转账

    3. 常用的功能主要是`账单`和`清算`，设置好昵称之后，每天结算的时候只需要`创建账单`，然后每个人依次使用`账单指令`,根据本人当日支出的款项并at需要平摊的好友即可创建成功。

    4. `查看账单`确定当前账单无误之后，使用`清算`命令即可对每个人自动计算应该给哪些人转账多少钱（没有做复杂的转账数量最小化）


## 感谢两位佬的源码参考:

> - [nonebot_plugin_smart_reply](https://github.com/Special-Week/nonebot_plugin_smart_reply)
> - [nonebot_plugin_gsmaterial](https://github.com/monsterxcn/nonebot-plugin-gsmaterial)