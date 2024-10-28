import base64
import io
import os

import pyautogui
import streamlit as st
from anthropic import Anthropic, AnthropicBedrock
from anthropic.types.beta import (
    BetaImageBlockParam,
    BetaMessage,
    BetaMessageParam,
    BetaTextBlock,
    BetaTextBlockParam,
    BetaToolUseBlock,
)
from PIL import Image

# client = AnthropicBedrock(aws_region="us-west-2", aws_profile="dev", max_retries=0)
client = Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)


def image_to_base64(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def action_screenshot(coordinate=None, text=None) -> BetaImageBlockParam:

    screenshot = pyautogui.screenshot(region=(0, 0, 1024, 768), allScreens=True)

    with st.chat_message("user"):
        with st.expander(label="Screenshot", expanded=False):
            st.image(screenshot)

    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": image_to_base64(screenshot),
        },
    }


def action_mouse_move(coordinate: list = None, text=None) -> BetaTextBlockParam:

    pyautogui.moveTo(coordinate[0], coordinate[1])

    return {"type": "text", "text": "移動しました。"}


def action_double_click(coordinate: list = None, text=None) -> BetaTextBlockParam:
    pyautogui.doubleClick()
    return {"type": "text", "text": "ダブルクリックしました。"}


def action_left_click(coordinate: list = None, text=None) -> BetaTextBlockParam:
    pyautogui.leftClick()
    return {"type": "text", "text": "左クリックしました。"}


def action_type(coordinate: list = None, text=None) -> BetaTextBlockParam:
    pyautogui.typewrite(text)
    return {"type": "text", "text": "入力しました。"}


def action_key(coordinate: list = None, text=None) -> BetaTextBlockParam:
    pyautogui.press(text)
    return {"type": "text", "text": "入力しました。"}


def create(messages: list[BetaMessageParam]) -> BetaMessage:

    return client.beta.messages.create(
        model="claude-3-5-sonnet-20241022",
        # model="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        max_tokens=1024,
        tools=[
            {
                "type": "computer_20241022",
                "name": "computer",
                "display_width_px": 1024,
                "display_height_px": 768,
                "display_number": 1,
            },
            {"type": "text_editor_20241022", "name": "str_replace_editor"},
            {"type": "bash_20241022", "name": "bash"},
        ],
        messages=messages,
        betas=["computer-use-2024-10-22"],
    )


st.title("I am 'Computer'")

if "message" not in st.session_state:
    st.session_state.message = []

messages: list[BetaMessageParam] = st.session_state.message


tools = {
    "screenshot": action_screenshot,
    "key": action_key,
    "type": action_type,
    "mouse_move": action_mouse_move,
    "left_click": action_left_click,
    "double_click": action_double_click,
    # "cursor_position": "", # TODO
    # "left_click_drag": "", # TODO
    # "right_click": "", # TODO
    # "middle_click": "", # TODO
}


if prompt := st.chat_input():

    user_message: BetaMessageParam = {
        "role": "user",
        "content": [{"type": "text", "text": prompt}],
    }

    with st.chat_message("user"):
        st.write(prompt)

    response = create(messages=messages + [user_message])

    assistant_message: BetaMessageParam = {
        "role": response.role,
        "content": response.content,
    }

    messages.append(user_message)
    messages.append(assistant_message)

    for c in response.content:
        if isinstance(c, BetaTextBlock):
            with st.chat_message(response.role):
                st.write(c.text)
        if isinstance(c, BetaToolUseBlock):

            with st.chat_message(response.role):
                st.write(c.input)

    while response.stop_reason == "tool_use":

        for c in response.content:
            if isinstance(c, BetaToolUseBlock):

                action = c.input["action"]
                coordinate = c.input["coordinate"] if "coordinate" in c.input else None
                text = c.input["text"] if "text" in c.input else None

                tool_result_message: BetaMessageParam = {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": c.id,
                            "content": [tools[action](coordinate, text)],
                        }
                    ],
                }

                with st.chat_message("user"):
                    with st.expander(label="Tool Result Message", expanded=False):
                        st.json(tool_result_message)

                response = create(messages=messages + [tool_result_message])

                assistant_message: BetaMessageParam = {
                    "role": response.role,
                    "content": response.content,
                }

                messages.append(tool_result_message)
                messages.append(assistant_message)

                for c in response.content:
                    if isinstance(c, BetaTextBlock):
                        with st.chat_message(response.role):
                            st.write(c.text)
                    if isinstance(c, BetaToolUseBlock):

                        with st.chat_message(response.role):
                            st.write(c.input)
