from langchain_core.prompts import ChatPromptTemplate

# 使用 LangChain 的 ChatPromptTemplate
STORYBOARD_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的动画分镜师,擅长将场景转换为详细的分镜脚本。"),
    ("human", """将以下场景转换为分镜脚本。

场景信息:
{scene_info}

角色信息:
{characters_info}

请为每个场景设计:
1. 镜头类型 (shot_type):
   - close_up: 特写镜头
   - medium_shot: 中景镜头
   - full_shot: 全景镜头
   - wide_shot: 远景镜头
   - extreme_close_up: 大特写

2. 镜头角度 (camera_angle):
   - eye_level: 平视
   - high_angle: 俯视
   - low_angle: 仰视
   - overhead: 顶视
   - dutch_angle: 斜角

3. 镜头运动 (camera_movement):
   - static: 静止
   - pan: 摇移
   - tilt: 俯仰
   - dolly: 推拉
   - tracking: 跟随

4. 时长 (duration):
   - 基于对话长度和动作数量计算
   - 对话: 约3字/秒
   - 动作: 每个动作约1.5秒
   - 最小3秒,最大10秒

5. 图像生成prompt (image_prompt):
   - 详细的视觉描述,包含环境、角色、光线、氛围
   - 使用anime style风格
   - 包含具体的构图要素

6. 构图 (composition):
   - rule_of_thirds: 三分法
   - centered: 居中构图
   - symmetrical: 对称构图
   - leading_lines: 引导线构图

7. 光线 (lighting):
   - natural: 自然光
   - soft: 柔光
   - dramatic: 戏剧性光线
   - backlight: 背光
   - side_light: 侧光

8. 转场效果 (transition):
   - cut: 切换
   - fade: 淡入淡出
   - dissolve: 溶解
   - wipe: 划像
   - none: 无转场

9. 情绪氛围 (mood):
   - 描述场景的情绪和氛围

请以JSON格式输出,严格遵循以下schema:
{{
    "scenes": [
        {{
            "scene_id": 场景编号(数字),
            "duration": 时长(浮点数),
            "shot_type": "镜头类型",
            "camera_angle": "镜头角度",
            "camera_movement": "镜头运动",
            "transition": "转场效果",
            "image_prompt": "详细的图像生成描述",
            "composition": "构图原则",
            "lighting": "光线设计",
            "mood": "情绪氛围"
        }}
    ]
}}

注意事项:
1. image_prompt必须详细且具体,包含所有视觉元素
2. 考虑场景连贯性,转场要自然
3. 时长计算要符合实际对话和动作需求
4. 确保JSON格式正确,可以被解析
5. 每个场景的scene_id必须与输入的scene_id对应""")
])
