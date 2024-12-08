import re
import requests
import json
import os
import threading
import time
from datetime import datetime, timedelta
import plugins
from plugins import *
from bridge.context import ContextType, Context
from bridge.reply import Reply, ReplyType
from common.log import logger
from channel.wechat.wechat_channel import WechatChannel

@plugins.register(name="Hunyuan_video",
                 desc="混元视频生成插件",
                 version="1.0",
                 author="Lingyuzhou",
                 desire_priority=100)
class HunyuanVideo(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.config_data = None
        self.video_tasks = {}  # 存储未完成的任务
        self.command_prefix = "混元视频"
        if self.load_config():
            logger.info("[HunyuanVideo] 配置加载成功")
        logger.info(f"[{__class__.__name__}] 初始化完成")

    def load_config(self):
        """加载配置文件"""
        if self.config_data:
            return True

        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as file:
                    self.config_data = json.load(file)
                return True
            except Exception as e:
                logger.error(f"[HunyuanVideo] 加载配置文件失败: {e}")
        else:
            logger.error("[HunyuanVideo] 配置文件不存在")
        return False

    def translate_prompt(self, prompt):
        """翻译提示词"""
        try:
            url = self.config_data.get('translate_api_url', '')
            headers = {
                "Authorization": f"Bearer {self.config_data.get('translate_api_key', '')}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.config_data.get('translate_model', 'Qwen/Qwen2.5-7B-Instruct'),
                "messages": [
                    {
                        "role": "system",
                        "content": """你是一个专业的翻译助手。请将用户输入的中文文本翻译成英文，需要注意：
1. 保持原文的意思和风格
2. 确保输出的英文自然流畅
3. 所有中文术语都必须翻译成对应的英文
4. 特别注意摄影和电影术语的专业翻译：
   - "推近" -> "zoom in"
   - "推远" -> "zoom out"
   - "俯拍" -> "high-angle shot"
   - "仰拍" -> "low-angle shot"
   - "侧拍" -> "side shot"
5. 确保没有任何中文字符在输出中"""
                    },
                    {
                        "role": "user",
                        "content": f"请将以下文本翻译成英文：\n{prompt}"
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # 提取翻译结果
            translated = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            if translated:
                # 检查是否还有中文字符
                if re.search(r'[\u4e00-\u9fff]', translated):
                    logger.warning(f"[HunyuanVideo] 翻译结果中仍包含中文字符，尝试重新翻译")
                    # 如果还有中文，尝试简单替换一些常见术语
                    translations = {
                        '推近': 'zoom in',
                        '推远': 'zoom out',
                        '俯拍': 'high-angle shot',
                        '仰拍': 'low-angle shot',
                        '侧拍': 'side shot'
                    }
                    for cn, en in translations.items():
                        translated = translated.replace(cn, en)
                
                logger.info(f"[HunyuanVideo] 翻译后的提示词: {translated}")
                return translated
            return prompt
            
        except Exception as e:
            logger.error(f"[HunyuanVideo] 翻译失败: {e}")
            return prompt

    def on_handle_context(self, e_context: Context):
        """处理收到的消息"""
        if not self.config_data:
            logger.error("[HunyuanVideo] 配置未加载，无法处理请求")
            return

        content = e_context['context'].content
        logger.debug(f"[HunyuanVideo] 收到消息: {content}")

        if not content.startswith(self.command_prefix):
            return

        prompt = content[len(self.command_prefix):].strip()
        if not prompt:
            self._send_text_message(e_context, "请在命令后面输入提示词")
            return

        try:
            # 翻译提示词
            translated_prompt = self.translate_prompt(prompt)
            if not translated_prompt:
                raise Exception("提示词翻译失败")
            logger.info(f"[HunyuanVideo] 翻译后的提示词: {translated_prompt}")
            self._send_text_message(e_context, f"提示词已翻译: {translated_prompt}")

            # 发起视频生成请求
            request_id = self._submit_video_task(translated_prompt)
            if not request_id:
                raise Exception("视频生成请求失败")

            # 获取正确的channel_id和from_user_id
            channel_id = e_context['context'].get('channel_id', 'default')
            is_group = e_context['context'].kwargs.get('isgroup', False)
            
            # 根据是否为群聊选择正确的接收者
            if is_group:
                receiver = e_context['context'].kwargs.get('receiver')  # 群聊ID
                session_id = receiver  # 在群聊中，session_id应该是群ID
            else:
                receiver = e_context['context'].get('session_id')  # 私聊用户ID
                session_id = receiver

            # 发送预计等待时间
            max_retries = 60  # 最多尝试60次，约10分钟
            retry_interval = 10  # 每10秒检查一次
            estimated_time = (max_retries * retry_interval) // 60  # 转换为分钟
            self._send_result_message(channel_id, receiver, session_id,
                f"视频正在生成中，预计还需等待约 {estimated_time} 分钟...", is_group)

            # 启动异步任务查询视频状态
            threading.Thread(target=self._check_video_status, 
                           args=(request_id, channel_id, receiver, session_id, is_group)).start()

        except Exception as e:
            logger.error(f"[HunyuanVideo] 处理请求失败: {e}")
            self._send_text_message(e_context, f"处理失败: {str(e)}")

    def _submit_video_task(self, translated_prompt):
        """提交视频生成任务"""
        url = "https://api.siliconflow.cn/v1/video/submit"
        payload = {
            "model": "tencent/HunyuanVideo",
            "prompt": translated_prompt
        }
        headers = {
            "Authorization": f"Bearer {self.config_data['api_key']}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.request("POST", url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            return result.get('requestId')
        except Exception as e:
            logger.error(f"[HunyuanVideo] 提交任务失败: {e}")
            raise

    def _check_video_status(self, request_id, channel_id, receiver, session_id, is_group):
        """检查视频生成状态"""
        url = "https://api.siliconflow.cn/v1/video/status"
        headers = {
            "Authorization": f"Bearer {self.config_data['api_key']}",
            "Content-Type": "application/json"
        }
        payload = {"requestId": request_id}

        max_retries = 60  # 最多尝试60次，约10分钟
        retry_interval = 20  # 每20秒检查一次
        last_position = -1

        for attempt in range(max_retries):
            try:
                response = requests.request("POST", url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                current_status = result.get('status')
                current_position = result.get('position', 0)
                
                # 如果位置发生变化，通知用户
                if current_position != last_position:
                    progress_msg = f"视频生成进行中... 当前队列位置: {current_position}"
                    self._send_result_message(channel_id, receiver, session_id, progress_msg, is_group)
                    last_position = current_position

                if current_status in ['Success', 'Succeed']:  # 支持两种成功状态
                    videos = result.get('results', {}).get('videos', [])
                    if videos:
                        # 下载并发送视频
                        for i, video_info in enumerate(videos):
                            video_url = video_info.get('url')
                            if video_url:
                                self.download_and_send_video(video_url, channel_id, receiver, session_id, is_group)
                        return
                    else:
                        self._send_result_message(channel_id, receiver, session_id, "视频生成完成，但未获取到视频链接", is_group)
                        return
                elif current_status == 'Failed':
                    reason = result.get('reason', '未知原因')
                    self._send_result_message(channel_id, receiver, session_id, f"视频生成失败: {reason}", is_group)
                    return
                elif current_status == 'InProgress':
                    logger.debug(f"[HunyuanVideo] 任务 {request_id} 正在处理中... (位置: {current_position})")
                else:
                    logger.debug(f"[HunyuanVideo] 当前状态: {current_status}")

            except Exception as e:
                logger.error(f"[HunyuanVideo] 检查状态失败: {e}")
            
            time.sleep(retry_interval)

        self._send_result_message(channel_id, receiver, session_id, "视频生成超时，请稍后重试", is_group)

    def download_and_send_video(self, video_url, channel_id, receiver, session_id, is_group):
        """下载并发送视频"""
        try:
            # 创建存储目录（如果不存在）
            storage_path = self.config_data.get('storage_path', './')
            if not os.path.exists(storage_path):
                os.makedirs(storage_path)

            # 下载视频
            video_data = requests.get(video_url).content
            timestamp = int(time.time())
            video_filename = f"video_{timestamp}.mp4"
            video_path = os.path.join(storage_path, video_filename)
            
            with open(video_path, 'wb') as handler:
                handler.write(video_data)
            logger.info(f"[HunyuanVideo] 视频已保存到: {video_path}")

            # 创建发送上下文
            context = Context()
            context.type = ContextType.VIDEO
            context.content = video_path
            context.kwargs = {
                'isgroup': is_group,
                'receiver': receiver,
                'session_id': session_id,
                'channel_id': channel_id
            }

            # 创建视频回复
            reply = Reply()
            reply.type = ReplyType.VIDEO
            reply.content = video_path
            context['reply'] = reply

            # 发送视频
            wechat_channel = WechatChannel()
            wechat_channel.send(reply, context)

            # 发送成功提示
            self._send_result_message(channel_id, receiver, session_id, "视频已发送，请查收！", is_group)

        except Exception as e:
            logger.error(f"[HunyuanVideo] 下载或发送视频失败: {e}")
            self._send_result_message(channel_id, receiver, session_id, "视频下载或发送失败，请稍后重试。", is_group)

    def _send_result_message(self, channel_id, receiver, session_id, message, is_group=False):
        """发送结果消息"""
        context = Context()
        context.type = ContextType.TEXT
        context.content = message
        context.kwargs = {
            'isgroup': is_group,
            'receiver': receiver,
            'session_id': session_id,
            'channel_id': channel_id
        }

        reply = Reply()
        reply.type = ReplyType.TEXT
        reply.content = message
        context['reply'] = reply

        try:
            # 使用 WechatChannel 发送消息
            wechat_channel = WechatChannel()
            wechat_channel.send(reply, context)
        except Exception as e:
            logger.error(f"[HunyuanVideo] 发送消息失败: {e}")

    def _send_text_message(self, e_context, message):
        """发送文本消息到聊天窗口"""
        reply = Reply()
        reply.type = ReplyType.TEXT
        reply.content = message
        e_context['reply'] = reply
        e_context.action = EventAction.BREAK_PASS

    def get_help_text(self, **kwargs):
        """获取插件帮助信息"""
        help_text = "混元视频生成插件使用指南：\n"
        help_text += f"1. 使用 {self.command_prefix} 作为命令前缀\n"
        help_text += "2. 在前缀后输入想要生成的视频描述，描述要具体且清晰，包含场景、动作、氛围等细节\n"
        help_text += "3. 视频生成可能需要一些时间，请耐心等待视频生成完成\n"
        help_text += "4. 示例：\n"
        help_text += "   混元视频 一只可爱的猫咪在草地上奔跑\n"
        return help_text
