# 如何贡献

感谢你愿意改进 GCC Telegram AI 助手。这份文档说明怎么参与，以及提交时要遵守的约定。

提问或报告问题请开 [Issue](https://github.com/Swiftevo/gcc-telegram-agent/issues)。准备改代码请发 Pull Request。更完整的行为约定见 [行为准则](CODE_OF_CONDUCT.md)。

## 分支约定

| 分支 | 用途 |
|---|---|
| `main` | 生产。已部署的 [@GCCpublicgoods_bot](https://t.me/GCCpublicgoods_bot) 以这条为准 |
| `dev` | 日常集成。功能合并到这里，验证后再进入 `main` |
| `feat/...`、`fix/...` | 功能或修复的短生命周期分支 |

不要直接向 `main` 推送。默认流程：

```text
origin/dev  →  feat/简短说明  →  PR 合入 origin/dev  →  再 PR 合入 origin/main
```

## 开发环境

需要 Python 3.12。

```bash
git clone https://github.com/Swiftevo/gcc-telegram-agent.git
cd gcc-telegram-agent
git checkout dev
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m unittest discover -s tests -v
```

不要把 `.env`、Token、密码或密钥提交到 Git。本地服务只能绑定 `127.0.0.1`，不要把本机端口暴露到公网。

## 提交 Issue

开 Issue 前先搜索是否已有同类讨论。

标题尽量带上类型词，方便自动打标签，例如：

- `新功能：……` 或 `enhancement: …`
- `缺陷：……` 或 `bug: …`
- `文档：……`
- 涉及身份、邮箱验证时加上「身份」或 `access`
- 涉及 GitHub Actions 时加上「工作流」或 `GitHub Actions`

正文请写清：

1. 要解决的问题或目标
2. 复现步骤或期望行为
3. 实际行为（若是缺陷）
4. 环境信息（Python 版本、polling / webhook、是否本地运行）

## 提交代码

1. 从最新 `dev` 拉出功能分支，名称用英文短横线，例如 `feat/grant-status`、`fix/email-otp`。
2. 一次 PR 只做一件事。重构和功能改动分开。
3. 新逻辑放在 `gcc_agent/` 对应模块。根目录的 `db.py`、`models.py`、`core/`、`handlers/` 只是兼容入口，不要在那里加新功能。
4. 行为变化要有测试，放在 `tests/` 下对应目录（`access`、`applications`、`knowledge`、`persistence`、`qa`）。
5. 提交前在本地跑：

   ```bash
   python -m unittest discover -s tests -v
   ```

6. 向 **`dev`** 开 Pull Request，不要直接开向 `main`。

### 提交说明

用简短的祈使句，说明「为什么」而不是罗列改了哪些文件。推荐前缀：

| 前缀 | 用途 |
|---|---|
| `feat:` | 新功能 |
| `fix:` | 缺陷修复 |
| `docs:` | 文档 |
| `test:` | 测试 |
| `refactor:` | 不改变对外行为的结构调整 |
| `chore:` | 构建、依赖、仓库杂项 |

关联 Issue 时在说明里写 `Refs #编号`。该 PR 合入后应关闭 Issue 时写 `Fixes #编号`。

### Pull Request

PR 标题与提交说明同样清晰。正文建议包含：

- **Summary**：改了什么、为什么
- **Test plan**：你怎么验证的（命令、Telegram 操作路径）

GitHub Actions 会按改动路径给 PR 打标签。请确认 CI 通过后再请求审查。

审查通过后由维护者合入 `dev`；发布到生产时再从 `dev` 合入 `main`。

## 代码约定

- 面向用户的文案同时考虑简体中文、繁体中文和英文。
- 外部输入不要拼进 SQL 或 shell；排序字段必须白名单。
- 日志不要打印密码、Token、验证码或邮箱等敏感信息。
- 非公开接口默认拒绝未授权访问；资源访问要做归属校验。
- 不要新增无鉴权的 debug / internal 接口。
- 本地或文档中的监听地址使用 `127.0.0.1`，不要写成 `0.0.0.0`。

不确定是否安全时，按「有风险」处理，并在 PR 里写明。

## 文档

用户能直接感知的变化，请同步 `README.md`。若改了安装、命令或贡献流程，也请更新 `README.zh-TW.md`、`README.en.md` 和本文件。

有疑问可以直接开 Issue，或在 PR 里 @ 维护者。
