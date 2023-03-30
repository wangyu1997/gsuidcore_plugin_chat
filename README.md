
> 本插件fork自[nonebot_plugin_smart_reply](https://github.com/Special-Week/nonebot_plugin_smart_reply)。


# 基于gsuid_core的智能(障)回复插件(理论兼容多个平台)

    问问提前请务必看完readme, 这是一个融合了openai, newbing, 词库的智障回复插件


## 功能

    普通对话调用简易版chatgpt
    接入了new bing的接口, 详情见下文
    接入了openai的接口, 详情见下文


### 安装方式:

    cd gsuid_core/gsuid_core/plugins
    git clone https://github.com/wangyu1997/gsuidcore_plugin_chat.git
    cd gsuidcore_plugin_chat.git
    poetry run pip install -r requirements.txt

修改`gsuidcore_plugin_chat/data/`下的`config.json`和`cookies`文件夹


### config配置项:

|config          |type            |default    |example                                  |usage                                   |
|----------------|----------------|-----------|-----------------------------------------|----------------------------------------|
| bot_nickname   | string         |我     |Bot_NICKNAME = "Hinata"                  |      你Bot的称呼                         |
| ai_reply_private  | boolean |false     |ai_reply_private = true          |    私聊时是否启用AI聊天            |
| openai_api_key    | list  |寄        |openai_api_key = ["aabb114514"]    |    openai的api_key, 详细请看下文         |
| openai_max_tokens | int     |1000      |openai_max_tokens = 1500         |    openai的max_tokens, 详细请看下文     |
| openai_cd_time    | int     |600        |openai_cd_time = 114             |    openai创建会话的cd                       |
| newbing_cd_time    | int     |600        |newbing_cd_time = 114             |    newbing创建会话的cd                       |
|bing_or_openai_proxy|str       |""         |bing_or_openai_proxy = "http://127.0.0.1:1081" |    openai或者newbing的代理, 配置详细请看下文|        
|newbing_style    |str             |creative   |newbing_style = "creative"             |newbing的风格, "creative", "balanced", "precise", 三选一, 乱填报错我不管|

config.json完全不配置不影响插件运行, 但是部分功能会无法使用(openai, newbing)


​       
## 关于openai:

    1. openai_api_key请注册openai后在 https://beta.openai.com/account/api-keys 自己获取
    2. openai_max_tokens貌似是ai返回的文本最大多少(根据我自己用的经验)
    3. openai_api_key必须配置, openai_max_tokens随意, 有默认值(1000)
    4. 需要配置代理, 否则无法使用, 代理配置详细请看下文
    5. 这个模块貌似不是免费的, 注册的账号只有$18.00的免费额度(现在缩成了5刀??), 请注意使用
    6. openai_api_key要求你填的是list, 创建会话的时候会随机从list选一个, 你可以填多个, 注意观察加载插件的时候, log会提示你加载了几个apikey
    7. 尽量保证revChatGPT模块是最新(pip install revChatGPT --upgrade)


    用法:
        1. openai + 内容, 和openai发起会话, 如果没有会新建会话
        2. 重置openai, 重置openai的会话
    
    使用了与openai通讯的接口 [ChatGPT](https://github.com/acheong08/ChatGPT)        




## 关于new bing的配置:

    0. 也许需要科学上网, 代理配置详细请看下文
    1. 使用功能必须配置cookie, 否则无法使用, 这个cookie内容过多不适合在.env, 所以这个cookie将会与json文件的形式进行配置
    2. 首先你需要一个通过申请的账号, 使用edge浏览器安装"editthiscookie"浏览器插件, 或者使用相关的其他插件获取cookie. 进入"bing.com/chat"登录通过的账号
    3. 右键界面选择"editthiscookie", 找到一个看上去像出门的样子的图标"导出cookie", cookie一般就能在你的剪贴板, 注意了, cookie导出来是一个list, 大概长这样[{},{},{}]
    4. 新建cookiexxx.json文件(xxx为任意合法字符), 把你剪贴板的cookie的字符串粘贴进去, 再次强调json大概长[{},{},{}]这样
    5. 打开你bot项目文件夹, 依次进入data/cookies, 没有就新建, 把json文件丢进去, 有几个账号可以放几个, 要求cookie开头, .json结尾, 载入插件时初始化会全部读取, 创建会话的时候会通过random来选择一个账号的cookie
    6. 注意观察加载插件的时候, log会提示你加载了几个cookie
    7. 尽量保证EdgeGPT模块是最新(pip install EdgeGPT --upgrade)


    用法:
        1. bing + 内容, 和bing发起会话, 如果没有会新建会话.
        2. 重置bing, 重置bing的会话

    使用了与Bing通讯的接口 [EdgeGPT](https://github.com/acheong08/EdgeGPT)        




## bing_or_openai_proxy的配置:

    1. 你需要使用v2ray或者clash等代理工具开启本地监听端口
    2. 根据http和socks5的不同, 配置不同, 
    3. 以v2rayN举例, 本地监听端口1080, 你应该配置成"socks5://127.0.0.1:1080"或者"http://127.0.0.1:1081"





响应器:
```python
# 使用普通chat的响应器
regular_sv = SV(
    '普通聊天',
    pm=3,  
    priority=17,
    enabled=True,
    black_list=[],
    area='ALL'
)
@regular_sv.on_fullmatch('重置chat', block=True,)
@regular_sv.on_prefix(('chat'), block=True,)
# 使用bing的响应器
bing = SV(
    'NEWBING',
    pm=3, 
    priority=14,
    enabled=True,
    black_list=[],
    area='ALL'
)
@bing.on_fullmatch('重置bing', block=True,)
@bing.on_prefix('bing', block=True,)  
# 使用openai的响应器
openai = SV(
    'OPENAI',
    pm=3, 
    priority=13,
    enabled=True,
    black_list=[],
    area='ALL'
)
@openai.on_fullmatch('重置openai', block=True,)
@openai.on_prefix('openai', block=True,)