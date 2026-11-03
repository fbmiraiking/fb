import json
import logging
from datetime import date
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.ai.types import VisionAnalysisResult
from app.models.product import StandardProductRelationType
from app.models.requirement import RequirementType
from app.models.standard import StandardStatus
from app.vision import service as vision_service
from tests.factories import (
    make_category,
    make_product_relation,
    make_relation,
    make_requirement,
    make_standard,
)

SECRET = "sk-vision-match-secret-456"

PAYLOAD = {
    "product": {
        "name": "婴儿塑料奶瓶",
        "categoryGuess": "婴儿奶瓶",
        "confidence": 0.95,
    },
    "materials": ["PP", "硅胶"],
    "usages": ["婴儿喂养"],
    "visibleText": [
        "GB 1000-2018",
        "GB 8888-2099",
        "生产日期 2024-05-01",
    ],
    "visibleStandardNumbers": ["GB 1000-2018", "GB 8888-2099"],
    "productionDate": "2024-05-01",
    "manufacturer": "示例公司",
}


class FakeProvider:
    def __init__(self, text: str) -> None:
        self.text = text
        self.image: bytes | None = None
        self.config = None

    async def analyze_image(self, image: bytes, config):
        self.image = image
        self.config = config
        return VisionAnalysisResult(
            text=self.text,
            provider=config.provider,
            model=config.model,
        )


def png_bytes() -> bytes:
    image = Image.new("RGB", (640, 480), (220, 230, 240))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def form_data() -> dict[str, str]:
    return {
        "provider": "openai",
        "apiBaseUrl": "https://api.example.test/v1",
        "apiKey": SECRET,
        "model": "gpt-test",
    }


def _seed(client_db) -> None:
    category = make_category("奶瓶", aliases=("婴儿奶瓶",))
    old = make_standard(
        standard_no="GB 1000-2018",
        standard_name="旧版塑料奶瓶标准",
        status=StandardStatus.REPLACED,
        publish_date=date(2018, 1, 1),
        effective_date=date(2018, 7, 1),
        expiry_date=date(2024, 4, 30),
        standard_year=2018,
    )
    current = make_standard(
        standard_no="GB 1000-2024",
        standard_name="现行塑料奶瓶标准",
        status=StandardStatus.ACTIVE,
        publish_date=date(2024, 1, 1),
        effective_date=date(2024, 5, 1),
        standard_year=2024,
    )

    client_db.add_all([category, old, current])
    client_db.commit()
    client_db.add_all(
        [
            make_relation(current.id, old.id),
            make_product_relation(
                current.id,
                category.id,
                StandardProductRelationType.DIRECT_APPLICABLE,
            ),
        ]
    )
    client_db.commit()

    client_db.add_all(
        [
            make_requirement(
                old.id,
                "4.1",
                RequirementType.LABEL,
                "包装上应标注执行标准号。",
            ),
            make_requirement(
                old.id,
                "4.2",
                RequirementType.LABEL,
                "包装上应标注生产厂家名称。",
            ),
            make_requirement(
                old.id,
                "4.3",
                RequirementType.VISUAL,
                "产品外观应清洁、无破损。",
            ),
            make_requirement(
                old.id,
                "5.1",
                RequirementType.LAB_TEST,
                "材料迁移量应符合限量要求。",
            ),
            make_requirement(
                old.id,
                "5.2",
                RequirementType.DOCUMENT,
                "应提供符合性声明或检测报告。",
            ),
        ]
    )
    client_db.commit()


def test_vision_analyze_and_match_returns_db_standards(
    client: TestClient,
    db_session,
    monkeypatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _seed(db_session)
    fake = FakeProvider(text=json.dumps(PAYLOAD, ensure_ascii=False))
    monkeypatch.setattr(
        vision_service,
        "get_vision_provider",
        lambda provider: fake,
    )
    caplog.set_level(logging.DEBUG)

    response = client.post(
        "/api/v1/vision/analyze-and-match",
        data=form_data(),
        files={"image": ("label.png", png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    body = response.json()

    assert set(body) >= {
        "imageAnalysis",
        "detectedStandards",
        "relatedStandards",
        "imageStored",
    }
    assert body["imageStored"] is False
    assert body["imageAnalysis"]["product"]["name"] == "婴儿塑料奶瓶"
    assert body["unmatchedVisibleStandardNumbers"] == ["GB 8888-2099"]

    assert len(body["detectedStandards"]) == 1
    detected = body["detectedStandards"][0]
    required = {
        "standardNo",
        "standardName",
        "status",
        "publishDate",
        "effectiveDate",
        "expiryDate",
        "relationType",
        "isHistorical",
    }
    assert required <= set(detected)
    assert detected["standardNo"] == "GB 1000-2018"
    assert detected["standardName"] == "旧版塑料奶瓶标准"
    assert detected["status"] == "REPLACED"
    assert detected["statusLabel"] == "旧标准"
    assert detected["publishDate"] == "2018-01-01"
    assert detected["effectiveDate"] == "2018-07-01"
    assert detected["expiryDate"] == "2024-04-30"
    assert detected["relationType"] == "DETECTED"
    assert detected["isHistorical"] is True
    assert detected["replacedBy"][0]["standardNo"] == "GB 1000-2024"
    assert detected["latestCurrent"][0]["standardNo"] == "GB 1000-2024"
    assert "旧标准" in detected["notice"]
    assert "2018-07-01" in detected["notice"]

    related = body["relatedStandards"]
    assert set(related) == {"current", "upcoming", "historical", "other"}
    assert [item["standardNo"] for item in related["current"]] == [
        "GB 1000-2024"
    ]
    assert related["upcoming"] == []
    assert related["historical"] == []
    assert related["other"] == []
    for item in related["current"]:
        assert required <= set(item)
        assert item["relationType"] == "DIRECT_APPLICABLE"
        assert item["isHistorical"] is False

    verification = body["standardVerification"]
    assert len(verification) == 1
    group = verification[0]
    assert group["standardNo"] == "GB 1000-2018"
    assert group["statusLabel"] == "旧标准"
    assert group["replacementStandards"][0]["standardNo"] == "GB 1000-2024"
    assert [item["chapter"] for item in group["requirements"]] == [
        "4.1",
        "4.2",
        "4.3",
        "5.1",
        "5.2",
    ]
    assert [item["status"] for item in group["requirements"]] == [
        "OBSERVED",
        "OBSERVED",
        "PARTIAL",
        "NOT_POSSIBLE",
        "NEEDS_DOCUMENT",
    ]
    assert group["observedCount"] == 2
    assert group["partialCount"] == 1
    assert group["externalCheckCount"] == 2
    assert group["requirements"][0]["imageCheckable"] is True
    assert group["requirements"][3]["imageCheckable"] is False
    assert group["requirements"][3]["statusLabel"] == "无法通过图片判断"
    assert group["requirements"][4]["statusLabel"] == "需要证书或文档"
    assert (
        body["verificationNotice"]
        == "图片分析只能辅助核对可见信息，不能替代实验检测、检测报告或合规认证。"
    )

    serialized = response.text
    assert "GB 8888-2099" not in {
        item["standardNo"]
        for item in body["detectedStandards"]
        + related["current"]
        + related["upcoming"]
        + related["historical"]
        + related["other"]
    }
    assert SECRET not in serialized
    assert SECRET not in caplog.text

    assert fake.image is not None
