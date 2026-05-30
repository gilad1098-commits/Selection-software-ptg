import json
import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_TABLE_NAME: str = "rfqrecords"
    AZURE_SERVICE_BUS_CONNECTION: str = ""

    # Webhook
    WEBHOOK_SECRET: str = ""

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # Microsoft Graph
    USER_EMAIL: str = "procurement@company.com"
    RFQ_FOLDER_ID: str = ""

    # Slack
    SLACK_BOT_TOKEN: str = ""
    SLACK_SIGNING_SECRET: str = ""
    SLACK_WEBHOOK_URL: str = ""  # The URL Slack will POST button clicks to

    # Priority ERP
    PRIORITY_BASE_URL: str = ""
    PRIORITY_USER: str = ""
    PRIORITY_PASSWORD: str = ""

    # SharePoint
    SHAREPOINT_BASE_URL: str = ""

    # Engineer mappings (JSON strings)
    ENGINEER_EMAIL_MAP: str = '{"Denis": "denis@company.com", "Dmitri": "dmitri@company.com"}'
    ENGINEER_SLACK_MAP: str = '{"Denis": "U012AB345", "Dmitri": "U067CD890"}'

    @property
    def engineer_email_map(self) -> dict[str, str]:
        return json.loads(self.ENGINEER_EMAIL_MAP)

    @property
    def engineer_slack_map(self) -> dict[str, str]:
        return json.loads(self.ENGINEER_SLACK_MAP)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
