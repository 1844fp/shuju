# v0.5.2 OCR与部署预检

知识上传支持PNG/JPEG、扫描PDF及指定页同页混排，OCR使用Windows本地能力。保留原有文档来源定位。部署预检入口为 `python infrastructure/deployment_preflight.py`。

冻结验收共164次业务测试执行，163通过、1项环境跳过。18页前端构建通过，实际Windows OCR和隔离HTTP上传通过。Docker验收延后。
