# 本次实际验证

制作环境：Linux，Python 3.12；2026-10-22 Europe/London。

- `python -m unittest test_core.py test_config.py`：11 项测试通过。覆盖允许范围、跨账户拒绝、精确地址、缺失/空配置、相似域名拒绝、正文截断、日期/分页、附件临时路径/大小及未读状态。
- 隔离 venv 按 `requirements.txt` 安装：成功，MCP 1.30.0；pywin32 按平台标记跳过。
- `python test_protocol.py`：通过真实 stdio MCP 初始化、五工具发现、只读注解及错误传播检查；Linux 本机读信返回预期 Windows 要求错误。
- Python 全文件语法编译：通过。
- 公开内容检查：未包含原用户邮箱、密钥、原隧道ID、私有任务记录或邮件；配置示例为空，测试邮件均为合成数据。

本次未在 Windows 运行 COM、DPAPI 或自动启动；未在朋友电脑安装，也未验证朋友的 OpenAI Tunnel/ChatGPT 读信。协议测试不证明端到端成功。
