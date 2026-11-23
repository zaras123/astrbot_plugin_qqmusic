# 更新日志

这里只记录 AstrBot 分支的版本；Karin 与 Yunzai 的历史不计入。
## v2.1.25

详情卡恢复本地曲库来源标识。

- multi / nebula 主题的点歌详情卡按 `local` / `channelKind` 显示「本地曲库（原文件）」，不再误显示为「QQ 音乐（你的账号）」。
- 本地详情卡保留来源、版本与音质信息；三端数据与模板同步。
## v2.1.24

修复文件发送开关无效与官方 FLAC 校验失败。

- aiocqhttp 文件优先走 `upload_group_file` / `upload_private_file`，不再依赖会被 NapCat/Lagrange 静默吞掉的 File 消息段；`uploadFile` 开关真正生效。
- QQ 官方/公众号等被动回复平台：语音与文件都发送；文件优先原始无损文件，官方接口拒绝大 FLAC 时自动降级压缩 MP3。
- 识别 ID3v2 标签后的 `fLaC`，语音统一转 128K MP3，避免把 FLAC 交给语音组件触发 `invalid sync code`。
- 下载校验 `Content-Length`；`ffprobe` 验证失败时按音质逐档回退（320 / m4a / 128），仍失败才提示，不再发送坏音频。
- Yunzai/Karin 同步质量回退逻辑；三端版本统一到 2.1.24。
## v2.1.23

审核合规修复与 Yunzai 锅巴侧栏修复。

- AstrBot：按上架审核要求删除 `render.py` 的 `logging` 回退，仅保留 `from astrbot.api import logger`；新增发行测试禁止内置 `logging`。
- Yunzai：修复锅巴侧栏「QQ音乐管理」未出现的问题——改为给真实 DI `systemService` 追加菜单、路由 path 去掉 `/guoba` 前缀、iframe 相对资源改用 HttpOnly Cookie 鉴权。
- 三端版本统一到 2.1.23；AstrBot 26 项测试与 ZIP 冒烟、Yunzai 锅巴控制台测试、Karin `npm test` 均通过。
## v2.1.22

三端内容与版本同步。

- WebUI 的 `localStorage` 回退同步到 Yunzai/Karin，三端 `app.js` 现在内容一致（bridge 仍按框架区分）。
- AstrBot 发行包字体子集与 16 MiB 审核修正纳入本版本：ZIP 13,384,526 字节（12.76 MiB）。
- 版本统一到 2.1.22；AstrBot 26 项测试、发行 ZIP 冒烟、Yunzai WebUI/多适配器测试、Karin `npm test` 均通过。
## v2.1.21

修复 AstrBot/icqq 群列表读取，并对三端统一 WebUI 再做一次一致性回归。

**修复**

- 适配 icqq `get_group_list()` 返回 `{群号: Group}` 以及对象行：本地曲库页现在能显示 icqq 群，不再永远落到“手动填写群号”。
- 群列表解析同时兼容 `{data/groups/list: [...]}` 包装、对象属性缺省与成员数字段异常。

**校验**

- AstrBot 26 项单元测试通过（新增 API 设置保存、icqq 群对象解析用例）。
- Yunzai WebUI/多适配器/票务/统计/勋章/语音等脚本全部通过；Karin `npm test` 通过。
- WebUI 静态文件与 Yunzai/Karin 逐字节一致（仅 AstrBot 的 bridge 与 sandbox localStorage 回退不同）。
- 发行包字体精简为 GB2312 + Big5 常用字子集（约 9988 字），ZIP 从 21.4MB 降到 12.8MB，满足插件市场 16 MiB 限制；Yunzai/Karin 保持完整 GBK 字体。
- 发行 ZIP 110 项，真实框架加载、帮助分发与热重载通过。

## v2.1.20

与 Yunzai / Karin 版本对齐到 2.1.20，完成统一 WebUI 与卡片主题的收尾。

**本地曲库 WebUI**

- 「本地曲库点歌」页与 Yunzai / Karin 使用同一套 HTML/CSS/JS、同一套 logo 与主题，AstrBot 只保留原生 bridge 接入。
- 右上角「插件设置」只配置 API 地址与 Token；未配置 Token 时搜索与发送返回 `TOKEN_REQUIRED`，不会请求 API 本地曲库。
- 群列表按当前在线适配器分组（`适配器|账号|群号`），没有群列表接口的适配器提供手动群号入口。
- 修复插件视图 iframe 处于 sandbox、无法访问 `localStorage` 时页面初始化中断；主题与任务记忆改为内存回退。

**卡片主题**

- 补齐 `poster` / `ticket` / `medal` / `listening` / `platform` / `platforms` / `guide` 模板与 `shared/ticket` 片段；list、lyric、poster、detail、hot、help、status、settings、comment 全部走同一套 Chromium 主题。
- 渲染参数与 Yunzai 一致：同宽视口、3x DPR、超过像素预算降 2x、`.page/.card` 元素截图、不透明导出。
- 缺少 Playwright / Chromium 时仍回退 Pillow，不影响出图。

**修复**

- 歌词卡片改为 snake_case 传参，修复 `#qqm歌词` 报 `build_lyric_card_data() unexpected keyword`。
- 恢复 OneBot 文件发送失败后的 `upload_group_file` / `upload_private_file` 降级。
- 打包脚本补入 `views/library`（bridge / settings / logo）与 `resources/`，市场 ZIP 不再缺资源。
- README 安装目录名、插件标识与数据目录统一为 `astrbot_plugin_qqmusic_ref`。

**验证**

- 24 项单元测试通过；发行 ZIP 真实框架冒烟：SDK 4.29.4 加载、帮助分发、热重载通过，38 个 handler。

## v2.1.19

统一 WebUI 与插件标识修正。

**本地曲库 WebUI**

- 页面与 Yunzai / Karin 完全一致：同一套 `views/library`（HTML/CSS/JS）、同一套 logo 与主题，AstrBot 只保留原生 bridge 接入。
- 顶部「插件设置」进入统一设置页，只配置 API 地址与 Token；未配置 Token 时搜索与发送返回 `TOKEN_REQUIRED`，不会请求 API。
- 群列表按当前在线适配器分组，显示为 `适配器|账号|群号`，无群列表接口的适配器给出明确提示。
- 发送任务在后台执行，逐群回显成功/失败；浏览器只提交曲库 ID 与群号，带签名的音频地址由服务端重新获取。

**修复**

- 修正插件标识与数据目录：`PLUGIN_NAME` 与 `StarTools.get_data_dir()` 统一为 `astrbot_plugin_qqmusic_ref`，避免与运行时插件目录不一致导致页面路由失效、配置落在错误目录。
- `metadata.yaml` 名称、仓库地址与平台列表与 `_ref` 插件保持一致，版本更新为 v2.1.19。
- 补齐 `poster` / `ticket` / `medal` / `listening` / `platform` / `guide` 主题模板与 `shared/ticket` 片段，歌词海报等卡片也走同一套 HTML 主题，不再回退 Pillow。
- 修复 AstrBot 插件视图 iframe 处于 sandbox、无法访问 `localStorage` 时页面初始化报错（改为内存回退，主题与任务记忆在会话内仍可用）。

## v2.1.18

首个 AstrBot 版本，沿用迁移基线版本号。

**本地曲库 WebUI**

- 新增「本地曲库点歌」视图：搜索 API 本地曲库、批量勾选歌曲、按适配器切换群列表、发送到群，并查看每个群的结果。
- 三平台统一管理页：Yunzai / AstrBot / Karin 共用同一套 HTML、CSS 和主逻辑，AstrBot 通过原生 WebUI bridge 接入，仅保留框架差异。
- 统一「API 设置」页，只配置 API 地址和 Token；未配置 Token 时搜索/发送在服务端返回 `TOKEN_REQUIRED`，不会请求 API 本地曲库。
- 群目标支持 `适配器|账号|群号`；只展示当前在线且有群列表的适配器，没有群列表接口的适配器会明确提示。
- 页面只提交曲库 ID 和群号，带 token 的音频地址由服务端按 ID 重新获取，不回传浏览器；发送任务在后台执行。

**播放与卡片**

- 支持多音源点歌、歌词、MV、分享解析、演出票务、订阅、定时点歌、点歌统计、勋章查询和账号操作。
- 卡片复用 Yunzai/Karin 的 HTML 主题（classic / apple / nebula / multi，含深色与时段底色），默认用 Chromium 渲染；缺少 Playwright/浏览器时自动回退 Pillow，不需要 Node.js。
- 发行包内置 `views/library`、`resources/vendor`、CJK 字体和图标，离线环境也能渲染同一套卡片。
- 普通登录只发送 QQ 码；微信和 App 登录指令使用 QQ 音乐 App 扫码通道。

**平台与投递**

- 采用 AstrBot 原生 Python 插件接口，按在线平台枚举群聊，并按适配器能力投递语音、视频和文件；不支持时降级。
- 适配器投递、曲库发送任务、后台重载和发行 ZIP 加载均做了本地冒烟测试；真实账号扫码与跨平台实发仍需按目标平台逐一验收。

**迁移范围**

- QQ 群「一起听」、平台时长上报未迁移。
- 损坏曲库音频可尝试回退官方同曲，不会自动覆盖原文件。
- 更新日志可在 AstrBot 插件管理查看，管理员也可用 `#qqm更新日志` 查看当前安装版本。
- 迁移差异详见 [README](README.md#迁移差异)。

