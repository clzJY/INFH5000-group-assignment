# 下载清单与 Mac 操作

公开大文件默认在 Mac 下载，暂不启用星流。Mac 中统一暂存于 `~/xingliu-transfer/ucmp-week3/`；文件均面向 Linux x86_64，Mac 只负责获取和转发。

## 下载内容

2026-11-01 已通过官方地址的有界 Range 请求读取到压缩包大小。下表使用十进制 MB、GB，解压后的占用尚未测量。

| 文件 | 压缩大小 | 必要性与来源 |
|---|---:|---|
| 固定版本 MetaUrban 源码 | 201,209,533 B，201.21 MB | 实验室已获取；传输包包含运行所需源码，Mac 不必重复下载。[固定 commit](https://github.com/metadriverse/metaurban/tree/6b8ff9aa48dd27d5c57fa1c712db520732f11fa9) |
| `pretrained_policy_576k.zip` | 655,890 B，0.66 MB | 已包含在上述源码中，并验证 SHA256，无需额外模型下载 |
| Linux CPython 3.11.14 | 47,042,299 B，47.04 MB | 必需；下载脚本锁定官方发布资产与 SHA256。[官方 release](https://github.com/astral-sh/python-build-standalone/releases/tag/20251014) |
| Linux Python wheels | 总量待 Mac 解析依赖后确定 | 必需；包括 CPU PyTorch、SB3、Panda3D、渲染与视频库。直接依赖完整列于 `requirements/runtime-linux-py311.txt`；脚本自动收集传递依赖并生成逐文件 SHA256 receipt |
| 完整静态资产 `assets_full.zip`（上游名 `assets.zip`） | 2,437,771,429 B，2.44 GB | 动态实验必需；[官方静态资产](https://drive.google.com/file/d/17pUIjPZrtac60YVHUL3YHMSaQ6J_Pmgc/view) |
| 行人资产 `assets_pedestrain.zip` | 1,588,857,017 B，1.59 GB | 动态实验和官方 wheelchair 外观必需；保留上游拼写。[官方行人资产](https://drive.google.com/file/d/1XUGfG57Cof43dX2pkMYBhsFVirJ4DQ1o/view) |
| 最小资产 `assets_tiny.zip` | 479,067,250 B，479.07 MB | 可选，只做单独的最小渲染检查；完整路线不需要重复下载。[官方 tiny 资产](https://drive.google.com/file/d/10bAr4-WnMHCSNCuz7qG41MDt_GStxkI9/view) |

两份完整资产合计 **4,026,628,446 B，约 4.03 GB**，不含运行环境。静态资产加密，需要你先完成 [官方注册表单](https://forms.office.com/r/tFBRFk7u4E)，保留返回的解压码；导入脚本通过终端隐藏输入读取，不把解压码写入命令或日志。

为避免重复获取，推荐直接下载完整资产，暂不下载 tiny。`assets_tiny.zip` 和完整包都包含 `assets/`，不要混合覆盖；导入工具拒绝覆盖已有目录或链接。

## 把准备包放到 Mac

在 Mac 终端运行。`lab` 请替换为你已有且已验证主机密钥的实验室 SSH alias；若当前网络不使用这个 alias，使用你现有的 SSH 连接方式。不要沿用历史星流端点。

```bash
mkdir -p "$HOME/xingliu-transfer/ucmp-week3/project"
scp lab:/data/private/user7/projects/storage_management/ucmp_week3_prepare_20261101-155721/releases/ucmp-week3-preparation.tar.gz "$HOME/xingliu-transfer/ucmp-week3/"
tar -xzf "$HOME/xingliu-transfer/ucmp-week3/ucmp-week3-preparation.tar.gz" -C "$HOME/xingliu-transfer/ucmp-week3/project"
```

代码准备包包括核心代码、配置、说明和已获取的上游运行源码／checkpoint；不包括聊天记录、任何旧研究环境或大型场景资产。先核对中央记录中的准备包 SHA256，再解包。

## 获取运行时和完整资产

使用 Mac 的 Python 3.11 或 3.12 启动下载工具。脚本会在暂存区创建独立的 Mac 下载工具 venv；此 venv 不传给 Linux。运行时下载会明确指定 CPython 3.11、Linux x86_64 的 wheel 平台，不下载 CUDA 版 PyTorch。

```bash
python3 "$HOME/xingliu-transfer/ucmp-week3/project/week3_assignment/scripts/download_on_mac.py" --stage runtime
```

完成官方注册后，再执行：

```bash
python3 "$HOME/xingliu-transfer/ucmp-week3/project/week3_assignment/scripts/download_on_mac.py" --stage full --registration-complete
```

每个成功阶段输出 `MAC_DOWNLOAD_STAGE_COMPLETE` 和一份 `receipt_*.json`。网络中断后重跑相同阶段；curl 对支持 Range 的来源保留 `.part`。若 Google Drive 返回 HTML／配额提示，脚本会报错，不能把登录页或错误页当作资产。此时使用官方链接在浏览器完成下载，再将实际文件按清单命名放入 `downloads/`，重跑该阶段生成并核验 receipt。

源码已在准备包中，仅在准备包没有上游源码时才需要 `--stage source`。Python 与源码有预先固定的 SHA256；Google Drive 未提供独立可信 SHA256，receipt 用于后续传输一致性核对。

## 回传实验室

在 Mac 终端运行。不要传 `tools/` 的 Mac 虚拟环境；不使用 `--delete`。

```bash
rsync -av --partial --exclude=project/ --exclude=tools/ --exclude=ucmp-week3-preparation.tar.gz "$HOME/xingliu-transfer/ucmp-week3/" lab:/data/private/user7/projects/Tempfile/UCMP-MB/week3_assignment/cache/mac_artifacts/
```

若没有 rsync，可用现有 SCP 或 tar-over-SSH 传输 `downloads/`、`wheelhouse/` 和所有 `receipt_*.json`，保留目录层级。服务器先验证 receipt，再运行离线安装。当前不需要启动星流完成这些步骤。

## 本次服务器测速结论

用户明确允许来源实测速率超过 1 MB/s 时在服务器下载；该授权覆盖本轮技能中默认的 Mac 获取约定。源码代理两轮约 4.15–4.49 MB/s，源码完整获取约 5.01 MB/s，已保存。Google Drive tiny 直连两次失败，代理两轮约 2.99–3.10 MB/s；这不能外推为 PyPI、Python 发布资产或全部完整包的持续速率，因此本轮不在服务器批量获取它们。

完整样本及获取校验保存在项目外的中央存储记录中。
