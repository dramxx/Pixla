import pytest
import tempfile
import os
from app.db import Database
from app.models import GenerationStatus


@pytest.fixture
def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        db = Database(db_path)
        yield db
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


class TestPaletteCRUD:
    def test_create_palette(self, db):
        palette = db.create_palette("Test Palette", ["#FF0000", "#00FF00"])

        assert palette.id >= 1
        assert palette.name == "Test Palette"
        assert palette.colors == ["#FF0000", "#00FF00"]

    def test_list_palettes(self, db):
        db.create_palette("Palette 1", ["#FF0000"])
        db.create_palette("Palette 2", ["#00FF00"])

        palettes = db.list_palettes()

        assert len(palettes) >= 2
        assert any(p.name == "Palette 1" for p in palettes)
        assert any(p.name == "Palette 2" for p in palettes)

    def test_get_palette(self, db):
        created = db.create_palette("My Palette", ["#FF0000"])
        retrieved = db.get_palette(created.id)

        assert retrieved is not None
        assert retrieved.name == "My Palette"
        assert retrieved.colors == ["#FF0000"]

    def test_get_palette_not_found(self, db):
        result = db.get_palette(9999)
        assert result is None

    def test_update_palette(self, db):
        created = db.create_palette("Original", ["#FF0000"])
        updated = db.update_palette(created.id, "Updated", ["#00FF00", "#0000FF"])

        assert updated.name == "Updated"
        assert updated.colors == ["#00FF00", "#0000FF"]

    def test_delete_palette(self, db):
        created = db.create_palette("To Delete", ["#FF0000"])
        result = db.delete_palette(created.id)

        assert result is True
        assert db.get_palette(created.id) is None

    def test_delete_palette_not_found(self, db):
        result = db.delete_palette(9999)
        assert result is False


class TestGenerationCRUD:
    def test_create_generation(self, db):
        gen = db.create_generation(
            prompt="a red apple",
            colors=["#FF0000", "#00FF00"],
            size=16,
            sprite_type="block",
        )

        assert gen.id == 1
        assert gen.prompt == "a red apple"
        assert gen.colors == ["#FF0000", "#00FF00"]
        assert gen.size == 16
        assert gen.sprite_type == "block"
        assert gen.status == GenerationStatus.PENDING

    def test_create_generation_with_optionals(self, db):
        gen = db.create_generation(
            prompt="test",
            colors=["#FF0000"],
            size=8,
            sprite_type="icon",
            system_prompt="custom prompt",
            model="llama3",
        )

        assert gen.system_prompt == "custom prompt"
        assert gen.model == "llama3"

    def test_get_generation(self, db):
        created = db.create_generation("test", ["#FF0000"], 16, "block")
        retrieved = db.get_generation(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_generation_not_found(self, db):
        result = db.get_generation(9999)
        assert result is None

    def test_list_generations(self, db):
        db.create_generation("test 1", ["#FF0000"], 16, "block")
        db.create_generation("test 2", ["#00FF00"], 16, "block")

        generations = db.list_generations(limit=10, offset=0)

        assert len(generations) >= 2

    def test_list_generations_pagination(self, db):
        for i in range(5):
            db.create_generation(f"test {i}", ["#FF0000"], 16, "block")

        page1 = db.list_generations(limit=2, offset=0)
        page2 = db.list_generations(limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].prompt != page2[0].prompt

    def test_update_generation_status(self, db):
        gen = db.create_generation("test", ["#FF0000"], 16, "block")
        db.update_generation_status(gen.id, GenerationStatus.GENERATING)

        updated = db.get_generation(gen.id)
        assert updated.status == GenerationStatus.GENERATING

    def test_update_generation_status_with_error(self, db):
        gen = db.create_generation("test", ["#FF0000"], 16, "block")
        db.update_generation_status(gen.id, GenerationStatus.ERROR, "Something went wrong")

        updated = db.get_generation(gen.id)
        assert updated.status == GenerationStatus.ERROR
        assert updated.error_message == "Something went wrong"

    def test_update_generation_pixels(self, db):
        gen = db.create_generation("test", ["#FF0000", "#00FF00"], 4, "block")
        pixel_data = [[0, 1, 0, 1], [1, 0, 1, 0], [0, 1, 0, 1], [1, 0, 1, 0]]

        db.update_generation_pixels(gen.id, pixel_data, 10)

        updated = db.get_generation(gen.id)
        assert updated.pixel_data == pixel_data
        assert updated.iterations == 10

    def test_update_generation_image(self, db):
        gen = db.create_generation("test", ["#FF0000"], 16, "block")
        db.update_generation_image(gen.id, "/path/to/image.png")

        updated = db.get_generation(gen.id)
        assert updated.image_path == "/path/to/image.png"

    def test_update_generation_reference(self, db):
        gen = db.create_generation("test", ["#FF0000"], 16, "block")
        db.update_generation_reference(gen.id, "/path/to/reference.png")

        updated = db.get_generation(gen.id)
        assert updated.reference_path == "/path/to/reference.png"


class TestGenerationLogs:
    def test_add_log(self, db):
        gen = db.create_generation("test", ["#FF0000"], 16, "block")
        db.add_log(gen.id, "thinking", "Analyzing prompt")

        logs = db.get_logs(gen.id)

        assert len(logs) == 1
        assert logs[0]["step"] == "thinking"
        assert logs[0]["message"] == "Analyzing prompt"

    def test_add_multiple_logs(self, db):
        gen = db.create_generation("test", ["#FF0000"], 16, "block")
        db.add_log(gen.id, "tool_call", "draw_pixel(x=0, y=0, color=0)")
        db.add_log(gen.id, "tool_result", "Set (0,0) to 0")
        db.add_log(gen.id, "error", "Something failed")

        logs = db.get_logs(gen.id)

        assert len(logs) == 3

    def test_get_logs_empty(self, db):
        gen = db.create_generation("test", ["#FF0000"], 16, "block")
        logs = db.get_logs(gen.id)

        assert logs == []

    def test_get_logs_for_nonexistent_generation(self, db):
        logs = db.get_logs(9999)
        assert logs == []


class TestDefaultPalette:
    def test_default_palette_created(self, db):
        palettes = db.list_palettes()

        assert len(palettes) >= 1
        assert any(p.name == "Default" for p in palettes)

    def test_default_palette_has_colors(self, db):
        default = next(p for p in db.list_palettes() if p.name == "Default")

        assert len(default.colors) > 0
        assert all(c.startswith("#") for c in default.colors)
