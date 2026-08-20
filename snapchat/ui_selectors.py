"""
Snapchat UI Element Selectors and Multi-Strategy Locator Definitions.
"""

from typing import List, Dict, Any


class SnapchatSelectors:
    """Multi-fallback selector definitions for Snapchat UI automation."""

    # Camera View Selectors
    CAMERA_SHUTTER = [
        {"resourceId": "com.snapchat.android:id/camera_capture_button"},
        {"description": "Take Photo"},
        {"description": "Camera"},
        {"xpath": "//android.widget.ImageButton[contains(@content-desc, 'Camera')]"},
        {"xpath": "//android.view.View[contains(@resource-id, 'capture')]"},
    ]

    FLASH_TOGGLE = [
        {"resourceId": "com.snapchat.android:id/camera_flash_button"},
        {"description": "Flash"},
    ]

    # Post Capture Selectors
    NEXT_BUTTON = [
        {"resourceId": "com.snapchat.android:id/send_btn"},
        {"resourceId": "com.snapchat.android:id/send_to_button"},
        {"description": "Send To"},
        {"text": "Next"},
        {"xpath": "//*[@text='Next' or @text='Send To']"},
    ]

    # Recipient Selection Selectors
    SEARCH_INPUT = [
        {"resourceId": "com.snapchat.android:id/search_edit_text"},
        {"resourceId": "com.snapchat.android:id/query_text"},
        {"text": "Search"},
        {"xpath": "//android.widget.EditText"},
    ]

    FINAL_SEND_BUTTON = [
        {"resourceId": "com.snapchat.android:id/send_to_bottom_panel_button"},
        {"resourceId": "com.snapchat.android:id/send_to_send_button"},
        {"description": "Send"},
        {"xpath": "//android.widget.ImageView[contains(@content-desc, 'Send')]"},
    ]

    # Navigation Tabs
    CAMERA_TAB = [
        {"resourceId": "com.snapchat.android:id/camera_tab"},
        {"description": "Camera"},
    ]

    CHAT_TAB = [
        {"resourceId": "com.snapchat.android:id/chat_tab"},
        {"description": "Chat"},
    ]
