# 微信语音提醒 · UIA 版（WeChatUIAAlert）

微信来消息时，用你选的提示音提醒、把「谁说了什么」念出来，`Ctrl+Alt+Q` 随时打断。

和普通的通知工具不同，它**不截图、不做 OCR**——直接读微信自己的 UI Automation 控件树，
所以微信**最小化、收进托盘、被别的窗口挡住、甚至挪到屏幕外**都照样工作。

---

## 和上一个项目的关系

| | [wechat-voice-alert](https://github.com/lonelypiggy060525/wechat-voice-alert)（上一个） | 本项目 |
| --- | --- | --- |
| 数据来源 | `PrintWindow` 截图 + RapidOCR 识别 | 微信 UI Automation 控件树 |
| 微信窗口 | 必须可见、不能最小化 | **最小化 / 托盘 / 屏幕外都行** |
| 识别错误 | 名字、数字可能认错（emoji 完全读不出） | 微信直接给文字，没有识别错误 |
| 长消息 | 预览约 14 字，要模拟点击读气泡 | 预览约 60 字，读气泡也是读控件 |
| 开销 | 常驻约 1% CPU、150 MB | 轮询控件树，几乎不占 CPU，24 MB |
| 对微信进程 | 完全不碰 | **改 1 个字节**（见「风险」） |

上一个项目是因为当时确认「微信 4.x 的 UIA 树是空的」才被迫读屏的。后来发现那棵树不是不存在，
而是被 Qt 的「无障碍 gate」关着——把那个字节打开，控件树就完整了。

## 原理

微信 4.x 用 Qt 自绘，默认不向 UI Automation 公开控件，外部只能看到一个空壳窗口：

```
Qt51514QWindowIcon          <- gate=0：3 个空节点
mmui::MainWindow            <- gate=1：完整控件树
  └ mmui::ChatSessionList
      └ mmui::XTableView
          └ mmui::ChatSessionCell   Name = "那只猪猪\n[1条]\n我去下午去洗\n18:59\n"
```

程序把 `Weixin.dll` 里那个「有没有辅助功能客户端」的标志字节写成 1（只改运行中进程的 1 个字节，
不注入代码、不挂 DLL、不改文件），微信当场开始返回完整控件树。

定位这个字节的方法（特征码扫描、按 DLL 版本缓存 RVA、写完校验控件树是否真的物化）来自
[wechatauto-replica](https://github.com/fanyuantaier/wechatauto-replica) 的 `tools/wake_uia.py`
（Apache-2.0），本仓库的 `wake_uia.py` 就是它，未作修改。

## 功能

- **提示音**：6 个内置音效，也可以选自己的音频（wav/mp3/wma 直接播，m4a/aac 等自动转 mp3 缓存）
- **语音播报**：微软在线神经语音（晓晓/云希/云扬…）+ 离线 SAPI 兜底，语速、音量独立可调
- **完整消息**：预览被截断时点开会话读气泡文本，拿到的是完整内容（含换行和 emoji）
- **提醒范围**：每个联系人/群一个持久开关，名单外按默认处理
- **只提醒别人发的**：未读数增加才算新消息，自己发的（含手机同步）不会念
- **多消息排队**：念完一条再念下一条，不会互相打断
- **打断**：`Ctrl+Alt+Q`（可改）
- **常驻托盘**：关窗口不退出；开机自启一个勾

## 运行

下载 [Releases](../../releases) 里的 `WeChatUIAAlert.exe`，双击即可（免 Python）。
未签名，Windows 可能提示「已保护你的电脑」→ 更多信息 → 仍要运行。

从源码跑：

```bat
uv venv --python 3.11 .venv
uv pip install --python .venv/Scripts/python.exe uiautomation comtypes pywin32 edge-tts pillow pyinstaller
.venv\Scripts\pythonw.exe app.py
```

首次启动会扫一遍 `Weixin.dll`（约 200 MB，实测 8 秒）找到那个字节，之后记在
`%USERPROFILE%\.wechatauto\gate_cache.json`，再启动是毫秒级。微信重启后字节会归零，
程序每 30 秒检查一次并自动重新置 1。

配置在 `%APPDATA%\WeChatUIAAlert\`。

## 风险（重要，请先读完）

1. **会修改微信进程的内存**。只改 1 个字节、不注入代码、不挂 DLL，但这仍然不是微信支持的行为。
   腾讯理论上可以把它判定为异常行为并采取措施（包括限制账号）——风险由使用者自己承担。
2. **依赖具体版本的二进制布局**。字节位置按 `Weixin.dll` 的特征码扫描，微信大版本更新后可能失效；
   那时程序会显示「微信控件树未打开」，需要等上游更新特征，或者手工指定 `--rva`。
3. **退出后字节保持为 1**（控件树继续公开）。要关掉可以运行
   `.venv\Scripts\python.exe wake_uia.py --off`，或者重启微信。
4. **读全文会把会话标为已读**，并让该会话排到列表最前面——这是微信自己的行为，绕不过去。
   不想要可以在「语音播报」页关掉「朗读完整内容」。
5. **只能读会话列表和当前打开会话的气泡**，没有历史消息、不能搜索，也不碰微信的数据库。
6. **语音合成会联网**（微软 Edge 神经语音）。断网时自动退回本地 SAPI，不发声失败。
7. 本程序不做任何上传；聊天内容只在本机内存和 `%APPDATA%\WeChatUIAAlert\last_messages.log` 里。
   日志里会有消息内容，介意的话可以删掉这个文件或关掉日志。

## 已知限制

- 只轮询会话列表里**可见**的会话；列表滚动到屏外的会话看不到未读
- 判定只看「未读数增加」——所以你在某个会话里连续聊天（未读数一直是 0）时，对方的新消息也算 0→0，不会播报；这类情况微信自己就会把消息标成已读，界面上能看到
- 微信被**关到托盘**（点 × 或最小化到托盘）也没关系：程序检测到窗口被隐藏，会把它重新打开**在屏幕外**（你屏幕上什么都看不到），重新打开控件树后继续读；普通最小化本来就一直能读
- 关到托盘后，程序重新打开的那个窗口会在任务栏留一个微信按钮（屏幕上看不到）；想彻底退出微信，请右键托盘图标 →「退出」，不要点 ×
- 图片/表情/语音没有文字，只能念成「发来一条消息」
- 群聊的发送人取自微信列表里的「某某: 」前缀，微信不给前缀时（比如连续消息合并）会退化成群名
- 微信更新后如果控件类名变了（`mmui::` 系列），需要改 `uia_list.py` 里的选择器

## 致谢

- [wechatauto-replica](https://github.com/fanyuantaier/wechatauto-replica)（Apache-2.0）：
  `wake_uia.py` 的 gate 定位与校验逻辑
- [uv](https://github.com/astral-sh/uv)、[uiautomation](https://github.com/yinkaisheng/Python-UIAutomation-for-Windows)、
  [RapidOCR](https://github.com/RapidAI/RapidOCR)（上一个项目用的）、[edge-tts](https://github.com/rany2/edge-tts)

## License

MIT。`wake_uia.py` 来自 Apache-2.0 项目，见文件头注释。
