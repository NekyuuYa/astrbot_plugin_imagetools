from astrbot.api.all import *
from PIL import Image
import io
import re

@register("imagetools", "Nekyuu", "图像处理工具箱", "0.1.0")
class ImageTools(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config

    @filter.command("image", alias=["图像处理"])
    async def image_handler(self, event: AstrMessageEvent):
        '''图像处理工具箱。用法：/image <功能> [参数] (并附带图片)
        功能：缩放(resize)、灰度(grayscale)、对称(symmetry)'''
        
        msg = event.message_str.strip()
        if not msg:
            yield event.plain_result("请输入具体功能。用法：/image <功能> [参数]\n可用功能：缩放、灰度、对称")
            return
            
        parts = re.split(r'\s+', msg)
        action = parts[0].lower()
        args = parts[1:]

        # 获取图片
        images = event.get_images()
        if not images:
            yield event.plain_result("请附带一张图片。")
            return
            
        image_url = images[0].url
        async with self.context.http_client.get(image_url) as resp:
            if resp.status != 200:
                yield event.plain_result("图片下载失败。")
                return
            img_data = await resp.read()
        
        try:
            img = Image.open(io.BytesIO(img_data))
            
            # 路由分发
            if action in ["resize", "缩放"]:
                yield from self._handle_resize(event, img, args)
            elif action in ["grayscale", "灰度"]:
                yield from self._handle_grayscale(event, img)
            elif action in ["symmetry", "对称"]:
                yield from self._handle_symmetry(event, img, args)
            else:
                yield event.plain_result(f"未知功能 '{action}'。可用功能：缩放、灰度、对称")
        except Exception as e:
            yield event.plain_result(f"处理失败: {str(e)}")

    def _handle_resize(self, event, img, args):
        try:
            if len(args) < 2:
                yield event.plain_result("格式错误。用法：/image 缩放 宽度 高度")
                return
            width = int(args[0])
            height = int(args[1])
            res = img.resize((width, height))
            yield from self._send_image(event, res)
        except ValueError:
            yield event.plain_result("宽度和高度必须是数字。示例：/image 缩放 800 600")

    def _handle_grayscale(self, event, img):
        res = img.convert('L')
        yield from self._send_image(event, res)

    def _handle_symmetry(self, event, img, args):
        direction = "左"
        ratio = 0.5
        if len(args) >= 1: direction = args[0]
        if len(args) >= 2:
            try:
                ratio = float(args[1])
                if not (0 <= ratio <= 1): ratio = 0.5
            except ValueError: pass

        w, h = img.size
        if direction in ["左", "left"]:
            axis = int(w * ratio)
            part = img.crop((0, 0, axis, h))
            mirror = part.transpose(Image.FLIP_LEFT_RIGHT)
            res = Image.new(img.mode, (axis * 2, h))
            res.paste(part, (0, 0))
            res.paste(mirror, (axis, 0))
        elif direction in ["右", "right"]:
            axis = int(w * ratio)
            part = img.crop((axis, 0, w, h))
            mirror = part.transpose(Image.FLIP_LEFT_RIGHT)
            part_w = w - axis
            res = Image.new(img.mode, (part_w * 2, h))
            res.paste(mirror, (0, 0))
            res.paste(part, (part_w, 0))
        elif direction in ["上", "top"]:
            axis = int(h * ratio)
            part = img.crop((0, 0, w, axis))
            mirror = part.transpose(Image.FLIP_TOP_BOTTOM)
            res = Image.new(img.mode, (w, axis * 2))
            res.paste(part, (0, 0))
            res.paste(mirror, (0, axis))
        elif direction in ["下", "bottom"]:
            axis = int(h * ratio)
            part = img.crop((0, axis, w, h))
            mirror = part.transpose(Image.FLIP_TOP_BOTTOM)
            part_h = h - axis
            res = Image.new(img.mode, (w, part_h * 2))
            res.paste(mirror, (0, 0))
            res.paste(part, (0, part_h))
        else:
            yield event.plain_result(f"不支持的方向 '{direction}'。")
            return
        yield from self._send_image(event, res)

    def _send_image(self, event, img):
        output = io.BytesIO()
        img.save(output, format='PNG')
        yield event.image_result(output.getvalue())
