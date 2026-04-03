import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.routes.generations import (
    CreateGenerationRequest,
    SpriteType,
    ChatRequest,
    PixelUpdate,
    UpdatePixelsRequest,
    TilesetRequest,
)


class TestCreateGenerationRequest:
    def test_valid_request(self):
        req = CreateGenerationRequest(
            prompt="a red apple",
            colors=["#FF0000", "#00FF00"],
            size=16,
            sprite_type=SpriteType.BLOCK,
        )

        assert req.prompt == "a red apple"
        assert req.colors == ["#FF0000", "#00FF00"]
        assert req.size == 16
        assert req.sprite_type == SpriteType.BLOCK

    def test_valid_icon_sprite_type(self):
        req = CreateGenerationRequest(
            prompt="sword",
            colors=["#CCCCCC"],
            sprite_type=SpriteType.ICON,
        )

        assert req.sprite_type == SpriteType.ICON

    def test_valid_entity_sprite_type(self):
        req = CreateGenerationRequest(
            prompt="hero",
            colors=["#FF0000"],
            sprite_type=SpriteType.ENTITY,
        )

        assert req.sprite_type == SpriteType.ENTITY

    def test_valid_autotile_sprite_type(self):
        req = CreateGenerationRequest(
            prompt="wall",
            colors=["#8B4513"],
            sprite_type=SpriteType.AUTOTILE,
        )

        assert req.sprite_type == SpriteType.AUTOTILE

    def test_invalid_color_format(self):
        with pytest.raises(ValidationError) as exc_info:
            CreateGenerationRequest(
                prompt="test",
                colors=["invalid"],
            )

        assert "Invalid color format" in str(exc_info.value)

    def test_invalid_color_value(self):
        with pytest.raises(ValidationError) as exc_info:
            CreateGenerationRequest(
                prompt="test",
                colors=["#QQQQQQ"],
            )

        assert "Invalid color" in str(exc_info.value)

    def test_size_too_small(self):
        with pytest.raises(ValidationError) as exc_info:
            CreateGenerationRequest(
                prompt="test",
                colors=["#FF0000"],
                size=2,
            )

        assert "size" in str(exc_info.value)

    def test_size_too_large(self):
        with pytest.raises(ValidationError) as exc_info:
            CreateGenerationRequest(
                prompt="test",
                colors=["#FF0000"],
                size=200,
            )

        assert "size" in str(exc_info.value)

    def test_size_valid_boundaries(self):
        req = CreateGenerationRequest(prompt="test", colors=["#FF0000"], size=4)
        assert req.size == 4

        req = CreateGenerationRequest(prompt="test", colors=["#FF0000"], size=128)
        assert req.size == 128

    def test_color_without_hash(self):
        with pytest.raises(ValidationError):
            CreateGenerationRequest(
                prompt="test",
                colors=["FF0000"],
            )

    def test_color_too_short(self):
        with pytest.raises(ValidationError):
            CreateGenerationRequest(
                prompt="test",
                colors=["#FF000"],
            )

    def test_color_too_long(self):
        with pytest.raises(ValidationError):
            CreateGenerationRequest(
                prompt="test",
                colors=["#FF00000"],
            )

    def test_default_values(self):
        req = CreateGenerationRequest(
            prompt="test",
            colors=["#FF0000"],
        )

        assert req.size == 16
        assert req.sprite_type == SpriteType.BLOCK
        assert req.reference_only == False
        assert req.use_agent == True


class TestChatRequest:
    def test_valid_message(self):
        req = ChatRequest(message="Make it bigger")

        assert req.message == "Make it bigger"

    def test_empty_message_allowed(self):
        req = ChatRequest(message="")

        assert req.message == ""


class TestPixelUpdate:
    def test_valid_update(self):
        update = PixelUpdate(x=5, y=10, color=3)

        assert update.x == 5
        assert update.y == 10
        assert update.color == 3

    def test_negative_color_allowed(self):
        update = PixelUpdate(x=0, y=0, color=-1)

        assert update.color == -1


class TestUpdatePixelsRequest:
    def test_valid_updates(self):
        req = UpdatePixelsRequest(
            updates=[
                PixelUpdate(x=0, y=0, color=1),
                PixelUpdate(x=1, y=1, color=2),
            ]
        )

        assert len(req.updates) == 2

    def test_empty_updates_allowed(self):
        req = UpdatePixelsRequest(updates=[])

        assert req.updates == []


class TestTilesetRequest:
    def test_valid_name(self):
        req = TilesetRequest(name="my-tileset")

        assert req.name == "my-tileset"


class TestSpriteTypeEnum:
    def test_block_value(self):
        assert SpriteType.BLOCK.value == "block"

    def test_icon_value(self):
        assert SpriteType.ICON.value == "icon"

    def test_entity_value(self):
        assert SpriteType.ENTITY.value == "entity"

    def test_autotile_value(self):
        assert SpriteType.AUTOTILE.value == "autotile"

    def test_from_string(self):
        assert SpriteType("block") == SpriteType.BLOCK
        assert SpriteType("icon") == SpriteType.ICON
