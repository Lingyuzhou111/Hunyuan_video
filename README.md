## Hunyuan_video

Hunyuan_video 是一款适用于 chatgpt-on-wechat 的视频生成插件，基于SiliconFlow平台的混元视频生成功能，支持通过文本描述生成视频。

官方混元视频体验地址: https://cloud.siliconflow.cn/playground/text-to-video

该插件使用起来非常简单，只需按以下步骤操作即可。

### 一. 获取API密钥
1. 注册并登录 Silicon Flow 平台，如果你还没有注册过请从这个地址注册https://cloud.siliconflow.cn/i/IvfkhvET

2. 在个人设置中获取 API Key，复制备用

### 二. 安装插件和配置config文件
1. 在微信机器人聊天窗口输入命令：

   #installp https://github.com/Lingyuzhou111/Hunyuan_video.git

2. 配置 config.json 文件，需要设置以下参数：
   - api_key: Silicon Flow的API密钥
   - translate_api_url: 翻译服务API地址
   - translate_api_key: 翻译服务API密钥
   - translate_model: 使用的翻译模型

3. 重启 chatgpt-on-wechat 项目

4. 在微信机器人聊天窗口输入 #scanp 命令扫描新插件

5. 输入 #help Hunyuan_video 查看帮助信息，确认插件安装成功

### 三. 使用说明
1. 基本使用方法：
   - 发送"混元视频 [视频描述]"即可开始生成视频
   - 支持中文描述，插件会自动将其翻译为英文

2. 视频描述建议：
   - 尽可能详细描述想要的场景和画面
   - 可以指定拍摄角度（如俯拍、仰拍、侧拍等）
   - 可以描述镜头运动（如推近、推远等）

3. 视频生成说明：
   - 视频生成需要一定时间，请耐心等待
   - 生成完成后会自动返回视频链接
   - 支持异步任务处理，可以同时提交多个生成请求

### 四. 常见问题
1. 如果生成失败，请检查：
   - API Key 是否正确配置
   - 网络连接是否正常
   - 描述文本是否清晰明确

2. 翻译问题：
   - 如果发现翻译不准确，可以直接使用英文描述
   - 专业术语会自动进行优化翻译

3. 如遇到其他问题，请在 GitHub 仓库提交 Issue

### 五. 版本信息
- 版本：1.0
- 作者：Lingyuzhou
- 最后更新：2024-12-07
- 如在使用时遇到问题请联系插件作者
- Github个人主页https://github.com/Lingyuzhou111

### 六. 特别说明
1. 本插件基于 Silicon Flow API 开发，API收费标准以官方说明为准（目前是0.7元/次），需要确保你的账户有足够的调用额度

2. 建议在生成视频时：
   - 使用清晰、具体的描述
   - 避免违规内容
   - 注意API使用配额

3. 后续更新计划：
   - 支持更多视频参数配置
   - 添加更多自定义选项
